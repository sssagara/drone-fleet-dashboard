#!/usr/bin/env python3

import rospy
from rqt_gui_py.plugin import Plugin
from python_qt_binding import loadUi
from python_qt_binding.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QLineEdit, QGridLayout
from python_qt_binding.QtCore import Qt, QTimer
from python_qt_binding.QtGui import QFont, QPalette, QColor
from std_msgs.msg import Float32, String
from geometry_msgs.msg import PoseStamped
import subprocess
import os

class DroneFleetDashboard(Plugin):
    def __init__(self, context):
        super(DroneFleetDashboard, self).__init__(context)
        self.setObjectName('DroneFleetDashboard')
        
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
        
        # Create drone panels
        self.drones = []
        for i in range(5):
            drone_panel = self.create_drone_panel(i + 1)
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
        
        # Create 6 global control buttons
        button_configs = [
            ("LAUNCH", "#004400", "#00ff00", self.global_command_1),
            ("ABORT", "#660000", "#ff0000", self.global_command_2),
            ("FORMATION", "#000066", "#0088ff", self.global_command_3),
            ("LAND ALL", "#664400", "#ffaa00", self.global_command_4),
            ("CALIBRATE", "#440066", "#aa00ff", self.global_command_5),
            ("SYSTEM CHECK", "#333333", "#888888", self.global_command_6)
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
        
        # Timer for updating UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)
    
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
        ip_input.setPlaceholderText("192.168.1.X")
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
        cmd1_btn.clicked.connect(lambda: self.run_command1(drone_id, ip_input.text()))
        
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
        cmd2_btn.clicked.connect(lambda: self.run_command2(drone_id, ip_input.text()))
        
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
            'connected': False,
            'battery_sub': None,
            'mode_sub': None,
            'pose_sub': None,
            'ip_address': None
        }
        
        return drone_data
    
    def connect_drone(self, drone_id, ip_address):
        """Connect to a drone with given IP address"""
        if not ip_address:
            rospy.logwarn(f"UNIT {drone_id}: NO IP ADDRESS PROVIDED")
            return
        
        drone = self.drones[drone_id - 1]
        
        # Disconnect previous subscribers
        if drone['battery_sub']:
            drone['battery_sub'].unregister()
        if drone['mode_sub']:
            drone['mode_sub'].unregister()
        if drone['pose_sub']:
            drone['pose_sub'].unregister()
        
        drone['ip_address'] = ip_address
        
        # Create ROS subscribers
        try:
            drone['battery_sub'] = rospy.Subscriber(
                f'/drone_{drone_id}/battery_voltage',
                Float32,
                lambda msg, d=drone: self.battery_callback(msg, d)
            )
            
            drone['mode_sub'] = rospy.Subscriber(
                f'/drone_{drone_id}/flight_mode',
                String,
                lambda msg, d=drone: self.mode_callback(msg, d)
            )
            
            drone['pose_sub'] = rospy.Subscriber(
                f'/drone_{drone_id}/local_position/pose',
                PoseStamped,
                lambda msg, d=drone: self.pose_callback(msg, d)
            )
            
            drone['connected'] = True
            drone['status_value'].setText("ONLINE")
            drone['status_value'].setStyleSheet("QLabel { color: #00ff00; font-weight: bold; font-size: 14px; }")
            rospy.loginfo(f"UNIT {drone_id}: CONNECTION ESTABLISHED - {ip_address}")
            
        except Exception as e:
            rospy.logerr(f"UNIT {drone_id}: CONNECTION FAILED - {str(e)}")
            drone['status_value'].setText("ERROR")
            drone['status_value'].setStyleSheet("QLabel { color: #ffaa00; font-weight: bold; font-size: 14px; }")
    
    def battery_callback(self, msg, drone):
        """Update battery voltage"""
        voltage = msg.data
        drone['battery_value'].setText(f"{voltage:.2f} V")
        
        if voltage > 11.5:
            color = "#00ff00"
        elif voltage > 10.5:
            color = "#ffaa00"
        else:
            color = "#ff0000"
        
        drone['battery_value'].setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; font-size: 14px; }}")
    
    def mode_callback(self, msg, drone):
        """Update flight mode"""
        mode = msg.data
        drone['mode_value'].setText(mode)
        
        if mode in ["ARMED", "AUTO", "MISSION"]:
            color = "#0088ff"
        elif mode in ["MANUAL", "LOITER"]:
            color = "#00ff88"
        elif mode in ["EMERGENCY", "ABORT"]:
            color = "#ff0000"
        else:
            color = "#888888"
        
        drone['mode_value'].setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; font-size: 14px; }}")
    
    def pose_callback(self, msg, drone):
        """Update position"""
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        drone['pos_value'].setText(f"X: {x:.2f} / Y: {y:.2f} / Z: {z:.2f}")
        drone['pos_value'].setStyleSheet("QLabel { color: #00ff88; font-weight: bold; font-size: 13px; }")
    
    def run_command1(self, drone_id, ip_address):
        """Emergency Stop"""
        if not ip_address:
            rospy.logwarn(f"UNIT {drone_id}: NO IP ADDRESS CONFIGURED")
            return
        
        command = f"rostopic pub -1 /drone_{drone_id}/emergency std_msgs/Bool 'data: true'"
        
        try:
            rospy.loginfo(f"UNIT {drone_id}: EMERGENCY STOP ACTIVATED")
            subprocess.Popen(command, shell=True)
        except Exception as e:
            rospy.logerr(f"UNIT {drone_id}: COMMAND FAILED - {str(e)}")
    
    def run_command2(self, drone_id, ip_address):
        """Return to Base"""
        if not ip_address:
            rospy.logwarn(f"UNIT {drone_id}: NO IP ADDRESS CONFIGURED")
            return
        
        command = f"rostopic pub -1 /drone_{drone_id}/return_to_home std_msgs/Bool 'data: true'"
        
        try:
            rospy.loginfo(f"UNIT {drone_id}: RETURN TO BASE COMMAND SENT")
            subprocess.Popen(command, shell=True)
        except Exception as e:
            rospy.logerr(f"UNIT {drone_id}: COMMAND FAILED - {str(e)}")
    
    # Global fleet control commands
    def global_command_1(self):
        """LAUNCH"""
        rospy.loginfo("FLEET COMMAND: LAUNCH SEQUENCE INITIATED")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                command = f"rostopic pub -1 /drone_{drone['id']}/start_mission std_msgs/Bool 'data: true'"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: LAUNCH COMMAND SENT")
    
    def global_command_2(self):
        """ABORT"""
        rospy.loginfo("FLEET COMMAND: ABORT MISSION")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                command = f"rostopic pub -1 /drone_{drone['id']}/abort_mission std_msgs/Bool 'data: true'"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: ABORT COMMAND SENT")
    
    def global_command_3(self):
        """FORMATION"""
        rospy.loginfo("FLEET COMMAND: FORMATION MODE ACTIVATED")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                command = f"rostopic pub -1 /drone_{drone['id']}/formation_mode std_msgs/Bool 'data: true'"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: FORMATION MODE ENGAGED")
    
    def global_command_4(self):
        """LAND ALL"""
        rospy.loginfo("FLEET COMMAND: LAND ALL UNITS")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                command = f"rostopic pub -1 /drone_{drone['id']}/land std_msgs/Bool 'data: true'"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: LANDING COMMAND SENT")
    
    def global_command_5(self):
        """CALIBRATE"""
        rospy.loginfo("FLEET COMMAND: CALIBRATION SEQUENCE")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                # SSH command to run script on drone
                command = f"ssh ubuntu@{drone['ip_address']} 'bash /home/ubuntu/scripts/calibrate.sh' &"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: CALIBRATION STARTED")
    
    def global_command_6(self):
        """SYSTEM CHECK"""
        rospy.loginfo("FLEET COMMAND: SYSTEM CHECK INITIATED")
        for drone in self.drones:
            if drone['connected'] and drone['ip_address']:
                # SSH command to run script on drone
                command = f"ssh ubuntu@{drone['ip_address']} 'bash /home/ubuntu/scripts/system_check.sh' &"
                subprocess.Popen(command, shell=True)
                rospy.loginfo(f"UNIT {drone['id']}: SYSTEM CHECK IN PROGRESS")
    
    def update_ui(self):
        """Periodic UI update"""
        pass
    
    def shutdown_plugin(self):
        """Cleanup"""
        self.update_timer.stop()
        for drone in self.drones:
            if drone['battery_sub']:
                drone['battery_sub'].unregister()
            if drone['mode_sub']:
                drone['mode_sub'].unregister()
            if drone['pose_sub']:
                drone['pose_sub'].unregister()
    
    def save_settings(self, plugin_settings, instance_settings):
        """Save settings"""
        for i, drone in enumerate(self.drones):
            ip = drone['ip_input'].text()
            if ip:
                instance_settings.set_value(f'drone_{i+1}_ip', ip)
    
    def restore_settings(self, plugin_settings, instance_settings):
        """Restore settings"""
        for i, drone in enumerate(self.drones):
            ip = instance_settings.value(f'drone_{i+1}_ip', '')
            if ip:
                drone['ip_input'].setText(ip)