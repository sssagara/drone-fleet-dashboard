#!/usr/bin/env python3

from rqt_gui_py.plugin import Plugin
from python_qt_binding.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QGridLayout
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
                                    print(f"Received telemetry for {len(self.telemetry_data)} drones: {list(self.telemetry_data.keys())}")
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}, data: {msg[:100]}")
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
                print(f"Telemetry client error: {e}")
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
        warning = QLabel('⚠ SYSTEM ACTIVE - MONITORING MODE ⚠')
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
        
        # Create drone panels (only 2 for now)
        self.drones = []
        for i in range(1, 3):  # Only drone 1 and 2
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
        
        # Create 3 active global control buttons
        button_configs = [
            ("LAUNCH", "#004400", "#00ff00", self.global_command_launch),
            ("LAND ALL", "#664400", "#ffaa00", self.global_command_land_all),
            ("EMERGENCY STOP", "#660000", "#ff0000", self.global_command_emergency),
        ]
        
        for label, bg_color, border_color, callback in button_configs:
            btn = QPushButton(label)
            btn.setMinimumHeight(50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {bg_color}, stop:1 {bg_color}dd);
                    border: 2px solid {border_color};
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    font-family: 'Courier New';
                    letter-spacing: 1px;
                    text-align: left;
                    padding-left: 15px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {bg_color}ee, stop:1 {bg_color}ff);
                    border: 2px solid {border_color};
                }}
                QPushButton:pressed {{
                    background: {bg_color};
                }}
            """)
            btn.clicked.connect(callback)
            right_buttons_layout.addWidget(btn)
        
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
        
        # Top row - Connection info
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        
        port_label = QLabel(f"PORT: 1454{drone_id-1}")
        port_label.setStyleSheet("""
            QLabel {
                color: #ffff00;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Courier New';
            }
        """)
        
        top_row.addWidget(port_label)
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
        
        cmd2_btn = QPushButton("LAND")
        cmd2_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #664400, stop:1 #996600);
                border: 2px solid #ffaa00;
                color: white;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #885500, stop:1 #bb7700);
            }
            QPushButton:pressed {
                background: #443300;
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
            'status_value': status_value,
            'battery_value': battery_value,
            'mode_value': mode_value,
            'pos_value': pos_value,
        }
        
        return drone_data
    
    def update_ui_from_telemetry(self):
        """Update UI with telemetry data (called by Qt timer in main thread)"""
        telemetry_data = self.telemetry_client.get_telemetry_data()
        
        if not telemetry_data:
            # No data yet, mark as offline
            self.check_connection_status()
            return
        
        # Debug print (only occasionally)
        if not hasattr(self, '_update_count'):
            self._update_count = 0
        self._update_count += 1
        if self._update_count % 10 == 0:  # Print every 10 updates (1 second)
            print(f"UI Update: Processing telemetry for {len(telemetry_data)} drones: {list(telemetry_data.keys())}")
        
        for drone in self.drones:
            drone_id = drone['id']
            # JSON converts dict keys to strings, so we need to use string key
            drone_id_str = str(drone_id)
            
            if self._update_count <= 3:
                print(f"DEBUG: Looking for drone_id={drone_id_str} (original: {drone_id})")
            
            if drone_id_str in telemetry_data:
                data = telemetry_data[drone_id_str]
                
                # Debug print for first few updates
                if self._update_count <= 3:
                    print(f"  Drone {drone_id}: Voltage={data.get('battery_voltage', 0):.2f}V, Mode={data.get('flight_mode', 'N/A')}, Armed={data.get('armed', False)}")
                
                # Update status
                drone['status_value'].setText("ONLINE")
                drone['status_value'].setStyleSheet("QLabel { color: #00ff00; font-weight: bold; font-size: 14px; }")
                
                # Update battery
                voltage = data.get('battery_voltage', 0.0)
                drone['battery_value'].setText(f"{voltage:.2f} V")
                
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
                    if mode in ["GUIDED", "AUTO", "MISSION", "AUTO_MISSION", "AUTO_TAKEOFF"]:
                        color = "#0088ff"
                    elif mode in ["MANUAL", "STABILIZE", "LOITER", "STABILIZED", "POSCTL", "ALTCTL"]:
                        color = "#00ff88"
                    else:
                        color = "#ffaa00"
                else:
                    color = "#888888"
                
                drone['mode_value'].setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; font-size: 14px; }}")
                
                # Update position
                position = data.get('position', [0, 0, 0])
                drone['pos_value'].setText(f"X: {position[0]:.2f} / Y: {position[1]:.2f} / Z: {position[2]:.2f}")
                drone['pos_value'].setStyleSheet("QLabel { color: #00ff88; font-weight: bold; font-size: 13px; }")
            else:
                # Drone not in telemetry data - mark as offline
                if self._update_count <= 3:
                    print(f"  Drone {drone_id}: NOT IN TELEMETRY DATA (looking for key '{drone_id_str}')")
        
        # Check connection status periodically
        if self._update_count % 10 == 0:
            self.check_connection_status()
    
    def check_connection_status(self):
        """Check connection status periodically"""
        if not self.telemetry_client.connected:
            # Mark all drones as offline if server disconnected
            for drone in self.drones:
                drone['status_value'].setText("OFFLINE")
                drone['status_value'].setStyleSheet("QLabel { color: #ff0000; font-weight: bold; font-size: 14px; }")
    
    def drone_emergency_stop(self, drone_id):
        """Individual drone emergency stop"""
        print(f"UNIT {drone_id}: EMERGENCY STOP ACTIVATED")
        self.telemetry_client.send_command({
            'type': 'drone_emergency',
            'drone_id': drone_id
        })
    
    def drone_land(self, drone_id):
        """Individual drone land"""
        print(f"UNIT {drone_id}: LAND COMMAND SENT")
        self.telemetry_client.send_command({
            'type': 'drone_land',
            'drone_id': drone_id
        })
    
    # Global fleet control commands
    def global_command_launch(self):
        """LAUNCH - Takeoff all drones"""
        print("FLEET COMMAND: LAUNCH SEQUENCE INITIATED")
        self.telemetry_client.send_command({'type': 'launch'})
    
    def global_command_land_all(self):
        """LAND ALL"""
        print("FLEET COMMAND: LAND ALL UNITS")
        self.telemetry_client.send_command({'type': 'land_all'})
    
    def global_command_emergency(self):
        """EMERGENCY STOP ALL"""
        print("FLEET COMMAND: EMERGENCY STOP ALL UNITS")
        self.telemetry_client.send_command({'type': 'emergency'})
    
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