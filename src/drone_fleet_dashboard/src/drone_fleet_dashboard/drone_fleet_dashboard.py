#!/usr/bin/env python3

from rqt_gui_py.plugin import Plugin
from python_qt_binding.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QGridLayout, QSlider, QMessageBox
from python_qt_binding.QtCore import Qt, QTimer
from python_qt_binding.QtGui import QFont, QPalette, QColor
import socket
import json
import threading

class TelemetryClient:
    """Client to receive telemetry from pymavlink script"""
    
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        self.connected = False
        self.telemetry_data = {}
        self.data_lock = threading.Lock()
        
        # Start connection thread
        self.thread = threading.Thread(target=self.connect_and_receive)
        self.thread.daemon = True
        self.thread.start()
    
    def connect_and_receive(self):
        """Connect to telemetry server and receive data"""
        while self.running:
            try:
                if not self.connected:
                    print(f"Connecting to telemetry server {self.host}:{self.port}...")
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                    self.connected = True
                    print("Connected to telemetry server")
                
                # Receive data
                data = self.socket.recv(4096)
                if data:
                    messages = data.decode().strip().split('\n')
                    for msg in messages:
                        if msg:
                            try:
                                message = json.loads(msg)
                                if message.get('type') == 'telemetry':
                                    with self.data_lock:
                                        self.telemetry_data = message.get('data', {})
                            except json.JSONDecodeError as e:
                                pass
                else:
                    # Connection closed
                    self.connected = False
                    self.socket.close()
                    
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError):
                self.connected = False
                if self.socket:
                    self.socket.close()
                import time
                time.sleep(2)  # Wait before reconnecting
            except Exception as e:
                self.connected = False
                if self.socket:
                    self.socket.close()
                import time
                time.sleep(2)
    
    def send_command(self, command):
        """Send command to telemetry server"""
        if self.connected and self.socket:
            try:
                message = json.dumps(command) + '\n'
                self.socket.sendall(message.encode())
                print(f"Command sent: {command}")
            except Exception as e:
                print(f"Error sending command: {e}")
                self.connected = False
    
    def get_telemetry_data(self):
        """Get current telemetry data (thread-safe)"""
        with self.data_lock:
            return self.telemetry_data.copy()
    
    def shutdown(self):
        """Shutdown client"""
        self.running = False
        self.connected = False
        if self.socket:
            self.socket.close()


class DroneFleetDashboard(Plugin):
    def __init__(self, context):
        super(DroneFleetDashboard, self).__init__(context)
        self.setObjectName('DroneFleetDashboard')
        
        # Create telemetry client
        self.telemetry_client = TelemetryClient()
        
        # Create main widget
        self._widget = QWidget()
        self._widget.setWindowTitle('◢ DRONE FLEET COMMAND SYSTEM - ZGMF SERIES ◤')
        
        # Set dark theme
        self.setup_theme()
        
        # Main layout - horizontal split
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left side - drone panels
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
        # Warning banner
        warning = QLabel('⚠ SYSTEM ACTIVE - INTERACTIVE DEMONSTRATION MODE ⚠')
        warning.setAlignment(Qt.AlignCenter)
        warning.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(100, 80, 0, 150),
                    stop:1 rgba(80, 60, 0, 200));
                border: 2px solid #ffaa00;
                border-left: 4px solid #ffaa00;
                color: #ffff00;
                padding: 12px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Courier New';
                letter-spacing: 1px;
            }
        """)
        left_layout.addWidget(warning)
        
        # Create drone panels (6 drones)
        self.drones = []
        for i in range(1, 7):
            drone_panel = self.create_drone_panel(i)
            self.drones.append(drone_panel)
            left_layout.addWidget(drone_panel['group'])
        
        # Right side - global control buttons
        right_layout = QVBoxLayout()
        right_group = QGroupBox("◢ FLEET CONTROL ◤")
        right_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 50, 30, 150),
                    stop:1 rgba(0, 30, 20, 200));
                border: 2px solid #00ff88;
                border-top: 4px solid #00ff88;
                padding: 15px;
                margin-top: 10px;
                font-size: 16px;
                font-weight: bold;
                color: #00ff88;
                font-family: 'Courier New';
                letter-spacing: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 20px;
            }
        """)
        
        right_buttons_layout = QVBoxLayout()
        right_buttons_layout.setSpacing(12)
        
        # Launch button
        launch_btn = QPushButton("LAUNCH ►")
        launch_btn.setMinimumHeight(50)
        launch_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #004400, stop:1 #004400dd);
                border: 2px solid #00ff00;
                color: white;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Courier New';
                letter-spacing: 1px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #004400ee, stop:1 #004400ff);
            }
        """)
        launch_btn.clicked.connect(self.global_command_launch)
        right_buttons_layout.addWidget(launch_btn)
        
        # Abort button
        abort_btn = QPushButton("ABORT ►")
        abort_btn.setMinimumHeight(50)
        abort_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #660000, stop:1 #660000dd);
                border: 2px solid #ff0000;
                color: white;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Courier New';
                letter-spacing: 1px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #880000, stop:1 #880000ff);
            }
        """)
        abort_btn.clicked.connect(self.global_command_abort)
        right_buttons_layout.addWidget(abort_btn)
        
        # Formation button
        formation_btn = QPushButton("FORMATION ►")
        formation_btn.setMinimumHeight(50)
        formation_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000066, stop:1 #000066dd);
                border: 2px solid #0088ff;
                color: white;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Courier New';
                letter-spacing: 1px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000088, stop:1 #000088ff);
            }
        """)
        formation_btn.clicked.connect(self.global_command_formation)
        right_buttons_layout.addWidget(formation_btn)
        
        # Land All button
        land_btn = QPushButton("LAND ALL ►")
        land_btn.setMinimumHeight(50)
        land_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #664400, stop:1 #664400dd);
                border: 2px solid #ffaa00;
                color: white;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Courier New';
                letter-spacing: 1px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #885500, stop:1 #885500ff);
            }
        """)
        land_btn.clicked.connect(self.global_command_land_all)
        right_buttons_layout.addWidget(land_btn)
        
        # Calibrate button (renamed to Reboot System)
        reboot_btn = QPushButton("REBOOT SYSTEM ►")
        reboot_btn.setMinimumHeight(50)
        reboot_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #440066, stop:1 #440066dd);
                border: 2px solid #aa00ff;
                color: white;
                font-weight: bold;
                font-size: 12px;
                font-family: 'Courier New';
                letter-spacing: 1px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #550088, stop:1 #550088ff);
            }
        """)
        reboot_btn.clicked.connect(self.global_command_reboot)
        right_buttons_layout.addWidget(reboot_btn)
        
        # Emergency Stop Slider
        emergency_container = QWidget()
        emergency_layout = QVBoxLayout(emergency_container)
        emergency_layout.setContentsMargins(0, 0, 0, 0)
        
        emergency_label = QLabel("EMERGENCY STOP")
        emergency_label.setStyleSheet("""
            QLabel {
                color: #ff0000;
                font-weight: bold;
                font-size: 11px;
                font-family: 'Courier New';
                text-align: center;
            }
        """)
        emergency_label.setAlignment(Qt.AlignCenter)
        
        self.emergency_slider = QSlider(Qt.Horizontal)
        self.emergency_slider.setMinimum(0)
        self.emergency_slider.setMaximum(100)
        self.emergency_slider.setValue(0)
        self.emergency_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 2px solid #ff0000;
                height: 10px;
                background: #330000;
            }
            QSlider::handle:horizontal {
                background: #ff0000;
                border: 2px solid #ff0000;
                width: 20px;
                margin: -5px 0;
            }
        """)
        self.emergency_slider.valueChanged.connect(self.emergency_slider_changed)
        
        emergency_instruction = QLabel("◄ Slide to activate")
        emergency_instruction.setStyleSheet("""
            QLabel {
                color: #ff6666;
                font-size: 10px;
                font-family: 'Courier New';
                text-align: center;
            }
        """)
        emergency_instruction.setAlignment(Qt.AlignCenter)
        
        emergency_layout.addWidget(emergency_label)
        emergency_layout.addWidget(self.emergency_slider)
        emergency_layout.addWidget(emergency_instruction)
        
        right_buttons_layout.addWidget(emergency_container)
        
        right_buttons_layout.addStretch()
        right_group.setLayout(right_buttons_layout)
        right_layout.addWidget(right_group)
        
        # Add both sides to main layout
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)
        
        self._widget.setLayout(main_layout)
        context.add_widget(self._widget)
        
        # Timer for updating UI from telemetry data
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui_from_telemetry)
        self.update_timer.start(100)  # Update every 100ms
    
    def setup_theme(self):
        """Setup dark Gundam-style theme"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(10, 10, 21))
        palette.setColor(QPalette.WindowText, QColor(0, 255, 136))
        palette.setColor(QPalette.Base, QColor(0, 0, 0))
        palette.setColor(QPalette.AlternateBase, QColor(20, 20, 40))
        palette.setColor(QPalette.Text, QColor(0, 255, 136))
        palette.setColor(QPalette.Button, QColor(0, 51, 51))
        palette.setColor(QPalette.ButtonText, QColor(0, 255, 255))
        self._widget.setPalette(palette)
        
        # Set stylesheet for main widget
        self._widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:1 #0f0f1e);
                color: #00ff88;
                font-family: 'Courier New';
            }
        """)
    
    def create_drone_panel(self, drone_id):
        """Create a panel for a single drone in Gundam style"""
        group = QGroupBox(f"◢ UNIT 0{drone_id} ◤")
        group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 30, 60, 100),
                    stop:1 rgba(0, 15, 30, 150));
                border: 2px solid #0088ff;
                border-left: 4px solid #00ff88;
                padding: 15px;
                margin-top: 10px;
                font-size: 16px;
                font-weight: bold;
                color: #00ffff;
                font-family: 'Courier New';
                letter-spacing: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        
        # Top row - IP and Connect
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        
        ip_label = QLabel("IP ADDR:")
        ip_label.setStyleSheet("""
            QLabel {
                color: #ffff00;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Courier New';
            }
        """)
        
        ip_input = QLineEdit()
        ip_input.setPlaceholderText(f"192.168.65.{100+drone_id}")
        ip_input.setMaximumWidth(150)
        ip_input.setStyleSheet("""
            QLineEdit {
                background: rgba(0, 0, 0, 200);
                border: 2px solid #0088ff;
                color: #00ff88;
                padding: 6px 10px;
                font-size: 13px;
                font-family: 'Courier New';
            }
            QLineEdit:focus {
                border: 2px solid #00ffff;
            }
        """)
        
        connect_btn = QPushButton("CONNECT")
        connect_btn.setMaximumWidth(100)
        connect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #003366, stop:1 #004488);
                border: 2px solid #0088ff;
                color: #00ffff;
                padding: 6px 15px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #004488, stop:1 #0055aa);
            }
            QPushButton:pressed {
                background: #002244;
            }
        """)
        connect_btn.clicked.connect(lambda: self.connect_drone(drone_id, ip_input.text()))
        
        top_row.addWidget(ip_label)
        top_row.addWidget(ip_input)
        top_row.addWidget(connect_btn)
        top_row.addStretch()
        
        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        info_grid.setHorizontalSpacing(20)
        
        label_style = """
            QLabel {
                color: #ffff00;
                font-size: 11px;
                font-weight: bold;
                font-family: 'Courier New';
                letter-spacing: 1px;
            }
        """
        
        value_style = """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                font-family: 'Courier New';
            }
        """
        
        # Status
        status_label = QLabel("STATUS:")
        status_label.setStyleSheet(label_style)
        status_value = QLabel("OFFLINE")
        status_value.setStyleSheet(value_style + "QLabel { color: #ff0000; }")
        info_grid.addWidget(status_label, 0, 0)
        info_grid.addWidget(status_value, 0, 1)
        
        # Battery
        battery_label = QLabel("BATTERY:")
        battery_label.setStyleSheet(label_style)
        battery_value = QLabel("-- V")
        battery_value.setStyleSheet(value_style + "QLabel { color: #666666; }")
        info_grid.addWidget(battery_label, 0, 2)
        info_grid.addWidget(battery_value, 0, 3)
        
        # Flight Mode
        mode_label = QLabel("MODE:")
        mode_label.setStyleSheet(label_style)
        mode_value = QLabel("--")
        mode_value.setStyleSheet(value_style + "QLabel { color: #666666; }")
        info_grid.addWidget(mode_label, 0, 4)
        info_grid.addWidget(mode_value, 0, 5)
        
        # Position row
        pos_container = QWidget()
        pos_container.setStyleSheet("""
            QWidget {
                background: rgba(0, 0, 0, 128);
                border-left: 3px solid #ffff00;
                padding: 8px;
            }
        """)
        pos_layout = QHBoxLayout(pos_container)
        pos_layout.setContentsMargins(10, 5, 10, 5)
        
        pos_label = QLabel("POSITION:")
        pos_label.setStyleSheet(label_style)
        pos_value = QLabel("X: -- / Y: -- / Z: --")
        pos_value.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Courier New';
            }
        """)
        
        pos_layout.addWidget(pos_label)
        pos_layout.addWidget(pos_value)
        pos_layout.addStretch()
        
        # Command buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cmd1_btn = QPushButton("EMERGENCY STOP")
        cmd1_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #660000, stop:1 #aa0000);
                border: 2px solid #ff0000;
                color: white;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #880000, stop:1 #cc0000);
            }
            QPushButton:pressed {
                background: #440000;
            }
        """)
        cmd1_btn.clicked.connect(lambda: self.drone_emergency_stop(drone_id))
        
        cmd2_btn = QPushButton("RETURN TO BASE")
        cmd2_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000066, stop:1 #0000aa);
                border: 2px solid #0088ff;
                color: white;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000088, stop:1 #0000cc);
            }
            QPushButton:pressed {
                background: #000044;
            }
        """)
        cmd2_btn.clicked.connect(lambda: self.drone_land(drone_id))
        
        buttons_layout.addWidget(cmd1_btn)
        buttons_layout.addWidget(cmd2_btn)
        
        # Assemble layout
        main_layout.addLayout(top_row)
        main_layout.addLayout(info_grid)
        main_layout.addWidget(pos_container)
        main_layout.addLayout(buttons_layout)
        
        group.setLayout(main_layout)
        
        # Store references
        drone_data = {
            'group': group,
            'id': drone_id,
            'ip_input': ip_input,
            'status_value': status_value,
            'battery_value': battery_value,
            'mode_value': mode_value,
            'pos_value': pos_value,
        }
        
        return drone_data
    
    def connect_drone(self, drone_id, ip_address):
        """Connect button clicked - just for display, actual connection is automatic"""
        if ip_address:
            print(f"UNIT {drone_id}: Manual connection to {ip_address} (telemetry is automatic via pymavlink)")
        else:
            print(f"UNIT {drone_id}: No IP address entered")
    
    def update_ui_from_telemetry(self):
        """Update UI with telemetry data (called by Qt timer in main thread)"""
        telemetry_data = self.telemetry_client.get_telemetry_data()
        
        if not telemetry_data:
            self.check_connection_status()
            return
        
        for drone in self.drones:
            drone_id = drone['id']
            drone_id_str = str(drone_id)
            
            if drone_id_str in telemetry_data:
                data = telemetry_data[drone_id_str]
                
                # Update status
                drone['status_value'].setText("ONLINE")
                drone['status_value'].setStyleSheet("QLabel { color: #00ff00; font-weight: bold; font-size: 14px; }")
                
                # Update battery
                voltage = data.get('battery_voltage', 0.0)
                drone['battery_value'].setText(f"{voltage:.1f} V")
                
                if voltage > 11.5:
                    color = "#00ff00"
                elif voltage > 10.5:
                    color = "#ffaa00"
                else:
                    color = "#ff0000"
                
                drone['battery_value'].setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; font-size: 14px; }}")
                
                # Update mode
                mode = data.get('flight_mode', 'UNKNOWN')
                armed = data.get('armed', False)
                
                if armed:
                    display_mode = f"{mode} (ARMED)"
                else:
                    display_mode = mode
                
                drone['mode_value'].setText(display_mode)
                
                if armed:
                    if mode in ["GUIDED", "AUTO", "MISSION", "AUTO_MISSION", "AUTO_TAKEOFF", "AUTO_LOITER"]:
                        color = "#0088ff"
                    elif mode in ["MANUAL", "STABILIZE", "LOITER", "STABILIZED", "POSCTL", "ALTCTL"]:
                        color = "#00ff88"
                    else:
                        color = "#ffaa00"
                else:
                    color = "#888888"
                
                drone['mode_value'].setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; font-size: 14px; }}")
                
                # Update position (3 decimal places)
                position = data.get('position', [0, 0, 0])
                drone['pos_value'].setText(f"X: {position[0]:.3f} / Y: {position[1]:.3f} / Z: {position[2]:.3f}")
                drone['pos_value'].setStyleSheet("QLabel { color: #00ff88; font-weight: bold; font-size: 13px; }")
    
    def check_connection_status(self):
        """Check connection status periodically"""
        if not self.telemetry_client.connected:
            for drone in self.drones:
                drone['status_value'].setText("OFFLINE")
                drone['status_value'].setStyleSheet("QLabel { color: #ff0000; font-weight: bold; font-size: 14px; }")
    
    def emergency_slider_changed(self, value):
        """Handle emergency slider movement"""
        if value >= 90:
            # Trigger emergency stop
            reply = QMessageBox.warning(
                self._widget,
                "EMERGENCY STOP",
                "CONFIRM EMERGENCY FLIGHT TERMINATION FOR ALL UNITS?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.global_command_emergency()
            
            # Reset slider
            self.emergency_slider.setValue(0)
        
    def drone_emergency_stop(self, drone_id):
        """Individual drone emergency stop"""
        print(f"UNIT {drone_id}: EMERGENCY STOP ACTIVATED")
        self.telemetry_client.send_command({
            'type': 'drone_emergency',
            'drone_id': drone_id
        })
    
    def drone_land(self, drone_id):
        """Individual drone land"""
        print(f"UNIT {drone_id}: RETURN TO BASE COMMAND SENT")
        self.telemetry_client.send_command({
            'type': 'drone_land',
            'drone_id': drone_id
        })
    
    # Global fleet control commands
    def global_command_launch(self):
        """LAUNCH - Takeoff all drones to 1m and hold"""
        print("FLEET COMMAND: LAUNCH SEQUENCE INITIATED")
        self.telemetry_client.send_command({'type': 'launch'})
    
    def global_command_abort(self):
        """ABORT - Stop and land all"""
        print("FLEET COMMAND: ABORT - LANDING ALL UNITS")
        self.telemetry_client.send_command({'type': 'land_all'})
    
    def global_command_land_all(self):
        """LAND ALL"""
        print("FLEET COMMAND: LAND ALL UNITS")
        self.telemetry_client.send_command({'type': 'land_all'})
    
    def global_command_emergency(self):
        """EMERGENCY STOP ALL"""
        print("FLEET COMMAND: EMERGENCY STOP ALL UNITS")
        self.telemetry_client.send_command({'type': 'emergency'})
    
    def global_command_reboot(self):
        """REBOOT SYSTEM - Reboot all flight controllers"""
        print("FLEET COMMAND: REBOOTING ALL FLIGHT CONTROLLERS")
        self.telemetry_client.send_command({'type': 'reboot'})
    
    def global_command_formation(self):
        """FORMATION - Placeholder for future"""
        print("FLEET COMMAND: FORMATION MODE (PLACEHOLDER)")
        self.telemetry_client.send_command({'type': 'formation'})
    
    def shutdown_plugin(self):
        """Cleanup"""
        self.update_timer.stop()
        self.telemetry_client.shutdown()
    
    def save_settings(self, plugin_settings, instance_settings):
        """Save settings"""
        pass
    
    def restore_settings(self, plugin_settings, instance_settings):
        """Restore settings"""
        pass