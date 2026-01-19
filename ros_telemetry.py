#!/usr/bin/env python3

import rospy
import threading
import time
import json
import socket
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from sensor_msgs.msg import BatteryState
from mavros_msgs.srv import CommandBool, CommandBoolRequest, SetMode, SetModeRequest
from std_msgs.msg import String


class ROSTelemetryClient:
    """ROS client to receive telemetry from MAVROS for a single drone"""
    
    def __init__(self, drone_id, namespace, server):
        """
        Initialize ROS telemetry client
        
        Args:
            drone_id: Drone ID number (1, 2, 3, etc.)
            namespace: ROS namespace for this drone (e.g., 'uav0', 'uav1', 'uav2')
            server: Reference to TelemetryServer for data updates
        """
        self.drone_id = drone_id
        self.namespace = namespace
        self.server = server
        
        # Store latest data
        self.battery_voltage = 0.0
        self.flight_mode = "UNKNOWN"
        self.local_position = [0.0, 0.0, 0.0]
        self.armed = False
        self.connected = False
        
        # ROS subscribers
        self.pose_sub = None
        self.state_sub = None
        self.battery_sub = None
        
        # ROS service clients
        self.arming_client = None
        self.set_mode_client = None
        
        # Note: ROS node should be initialized by the parent FleetROSTelemetryManager
        # not by individual drone clients
        
        self.initialize_subscribers()
        self.initialize_services()
        
        print(f"Drone {drone_id}: ROS Telemetry client initialized for namespace '{namespace}'")
    
    def initialize_subscribers(self):
        """Initialize ROS subscribers for telemetry data"""
        try:
            # Subscribe to local position
            pose_topic = f"/{self.namespace}/mavros/local_position/pose"
            self.pose_sub = rospy.Subscriber(
                pose_topic,
                PoseStamped,
                self.pose_callback
            )
            
            # Subscribe to state (flight mode and armed status)
            state_topic = f"/{self.namespace}/mavros/state"
            self.state_sub = rospy.Subscriber(
                state_topic,
                State,
                self.state_callback
            )
            
            # Subscribe to battery
            battery_topic = f"/{self.namespace}/mavros/battery"
            self.battery_sub = rospy.Subscriber(
                battery_topic,
                BatteryState,
                self.battery_callback
            )
            
            print(f"Drone {self.drone_id}: Subscribed to topics in namespace '{self.namespace}'")
            self.connected = True
            
        except Exception as e:
            print(f"Drone {self.drone_id}: Error initializing subscribers: {e}")
            self.connected = False
    
    def initialize_services(self):
        """Initialize ROS service clients for commands"""
        try:
            # Arming service
            arming_service = f"/{self.namespace}/mavros/cmd/arming"
            rospy.wait_for_service(arming_service, timeout=5.0)
            self.arming_client = rospy.ServiceProxy(arming_service, CommandBool)
            
            # Set mode service
            set_mode_service = f"/{self.namespace}/mavros/set_mode"
            rospy.wait_for_service(set_mode_service, timeout=5.0)
            self.set_mode_client = rospy.ServiceProxy(set_mode_service, SetMode)
            
            print(f"Drone {self.drone_id}: Services initialized")
            
        except rospy.ROSException as e:
            print(f"Drone {self.drone_id}: Warning - Services not available: {e}")
    
    def pose_callback(self, msg):
        """Callback for local position updates"""
        # Extract position (NED to ENU conversion if needed)
        self.local_position = [
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z
        ]
        self.update_server_data()
    
    def state_callback(self, msg):
        """Callback for state updates (mode and armed status)"""
        self.flight_mode = msg.mode
        self.armed = msg.armed
        self.connected = msg.connected
        # print(f"Drone {self.drone_id}: State - Mode: {self.flight_mode}, Armed: {self.armed}, Connected: {self.connected}")
        self.update_server_data()
    
    def battery_callback(self, msg):
        """Callback for battery updates"""
        self.battery_voltage = msg.voltage
        self.update_server_data()
    
    def update_server_data(self):
        """Update server with latest telemetry data"""
        data = {
            'battery_voltage': self.battery_voltage,
            'flight_mode': self.flight_mode,
            'position': self.local_position,
            'armed': self.armed,
            'connected': self.connected
        }
        self.server.update_drone_data(self.drone_id, data)
    
    def arm(self):
        """Arm the vehicle"""
        if self.arming_client is None:
            print(f"Drone {self.drone_id}: Arming service not available")
            return
        
        try:
            print(f"Drone {self.drone_id}: Arming...")
            req = CommandBoolRequest()
            req.value = True
            response = self.arming_client(req)
            if response.success:
                print(f"Drone {self.drone_id}: Armed successfully")
            else:
                print(f"Drone {self.drone_id}: Arming failed")
        except rospy.ServiceException as e:
            print(f"Drone {self.drone_id}: Arming service call failed: {e}")
    
    def disarm(self):
        """Disarm the vehicle"""
        if self.arming_client is None:
            print(f"Drone {self.drone_id}: Arming service not available")
            return
        
        try:
            print(f"Drone {self.drone_id}: Disarming...")
            req = CommandBoolRequest()
            req.value = False
            response = self.arming_client(req)
            if response.success:
                print(f"Drone {self.drone_id}: Disarmed successfully")
            else:
                print(f"Drone {self.drone_id}: Disarming failed")
        except rospy.ServiceException as e:
            print(f"Drone {self.drone_id}: Disarming service call failed: {e}")
    
    def set_mode(self, mode):
        """
        Set flight mode
        
        Args:
            mode: Flight mode string (e.g., 'OFFBOARD', 'AUTO.LAND', 'AUTO.RTL')
        """
        if self.set_mode_client is None:
            print(f"Drone {self.drone_id}: Set mode service not available")
            return
        
        try:
            print(f"Drone {self.drone_id}: Setting mode to {mode}...")
            req = SetModeRequest()
            req.custom_mode = mode
            response = self.set_mode_client(req)
            if response.mode_sent:
                print(f"Drone {self.drone_id}: Mode set to {mode}")
            else:
                print(f"Drone {self.drone_id}: Failed to set mode to {mode}")
        except rospy.ServiceException as e:
            print(f"Drone {self.drone_id}: Set mode service call failed: {e}")
    
    def takeoff(self, altitude=5.0):
        """
        Takeoff sequence
        
        Args:
            altitude: Target altitude in meters
        """
        print(f"Drone {self.drone_id}: Initiating takeoff to {altitude}m")
        
        # For ROS/MAVROS, takeoff is typically done by:
        # 1. Set mode to OFFBOARD or GUIDED
        # 2. Arm
        # 3. Send position setpoints (handled by external controller)
        
        self.set_mode('OFFBOARD')
        time.sleep(1)
        self.arm()
        
        print(f"Drone {self.drone_id}: Takeoff sequence initiated")
    
    def land(self):
        """Land the vehicle"""
        print(f"Drone {self.drone_id}: Landing...")
        self.set_mode('AUTO.LAND')
    
    def rtl(self):
        """Return to launch"""
        print(f"Drone {self.drone_id}: Return to launch...")
        self.set_mode('AUTO.RTL')
    
    def emergency_stop(self):
        """Emergency stop - disarm immediately"""
        print(f"Drone {self.drone_id}: EMERGENCY STOP!")
        self.disarm()
    
    def reboot(self):
        """Reboot the flight controller"""
        from mavros_msgs.srv import CommandLong, CommandLongRequest
        
        print(f"Drone {self.drone_id}: Rebooting flight controller...")
        
        try:
            # Wait for command service
            command_service = f"/{self.namespace}/mavros/cmd/command"
            rospy.wait_for_service(command_service, timeout=5.0)
            command_client = rospy.ServiceProxy(command_service, CommandLong)
            
            # Prepare reboot command (MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN = 246)
            req = CommandLongRequest()
            req.command = 246  # MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN
            req.param1 = 1.0   # Autopilot reboot
            req.param2 = 0.0
            req.param3 = 0.0
            req.param4 = 0.0
            req.param5 = 0.0
            req.param6 = 0.0
            req.param7 = 0.0
            
            response = command_client(req)
            if response.success:
                print(f"Drone {self.drone_id}: Reboot command sent successfully")
            else:
                print(f"Drone {self.drone_id}: Reboot command failed: {response.result}")
                
        except rospy.ServiceException as e:
            print(f"Drone {self.drone_id}: Reboot service call failed: {e}")
        except rospy.ROSException as e:
            print(f"Drone {self.drone_id}: Reboot service timeout: {e}")
    
    def shutdown(self):
        """Shutdown telemetry client"""
        print(f"Drone {self.drone_id}: Shutting down ROS telemetry client")
        if self.pose_sub:
            self.pose_sub.unregister()
        if self.state_sub:
            self.state_sub.unregister()
        if self.battery_sub:
            self.battery_sub.unregister()


class TelemetryServer:
    """TCP server to communicate telemetry data to dashboard"""
    
    def __init__(self, host='127.0.0.1', port=5556):
        self.host = host
        self.port = port
        self.drone_data = {}
        self.drones = {}
        self.clients = []
        self.running = True
        
        # Create socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        
        print(f"ROS Telemetry server listening on {self.host}:{self.port}")
        
        # Start server thread
        self.server_thread = threading.Thread(target=self.accept_connections)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Start command processing thread
        self.command_thread = threading.Thread(target=self.process_commands)
        self.command_thread.daemon = True
        self.command_thread.start()
    
    def accept_connections(self):
        """Accept client connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"Client connected from {address}")
                self.clients.append(client_socket)
                
                # Send current data to new client
                self.send_to_client(client_socket)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Accept connection error: {e}")
    
    def update_drone_data(self, drone_id, data):
        """Update drone telemetry data"""
        self.drone_data[drone_id] = data
        # Broadcast to all clients
        self.broadcast_data()
    
    def broadcast_data(self):
        """Broadcast telemetry data to all clients"""
        for client in self.clients[:]:
            try:
                self.send_to_client(client)
            except Exception as e:
                self.clients.remove(client)
    
    def send_to_client(self, client):
        """Send data to a specific client"""
        message = json.dumps({
            'type': 'telemetry',
            'data': self.drone_data
        }) + '\n'
        try:
            client.sendall(message.encode())
            # Debug: Print first time data is sent
            if not hasattr(self, '_first_send_done'):
                print(f"Sending telemetry data: {self.drone_data}")
                self._first_send_done = True
        except BrokenPipeError:
            raise  # Let caller handle cleanup
    
    def process_commands(self):
        """Process commands from clients"""
        while self.running:
            for client in self.clients[:]:
                try:
                    client.setblocking(0)
                    data = client.recv(4096)
                    if data:
                        command = json.loads(data.decode().strip())
                        self.handle_command(command)
                except BlockingIOError:
                    pass
                except Exception as e:
                    if self.running:
                        self.clients.remove(client)
            time.sleep(0.01)
    
    def handle_command(self, command):
        """Handle command from dashboard"""
        cmd_type = command.get('type')
        drone_id = command.get('drone_id')
        
        print(f"Received command: {command}")
        
        if cmd_type == 'launch':
            # Launch all drones (takeoff)
            for drone in self.drones.values():
                threading.Thread(target=drone.takeoff, args=(10.0,)).start()
        
        elif cmd_type == 'land_all':
            # Land all drones
            for drone in self.drones.values():
                threading.Thread(target=drone.land).start()
        
        elif cmd_type == 'emergency':
            # Emergency stop all drones
            for drone in self.drones.values():
                threading.Thread(target=drone.emergency_stop).start()
        
        elif cmd_type == 'reboot':
            # Reboot all flight controllers
            print("Reboot command received - rebooting all drones")
            for drone in self.drones.values():
                threading.Thread(target=drone.reboot).start()
        
        elif cmd_type == 'formation':
            # Formation command for all drones
            print("Formation command received - placeholder for future implementation")
        
        elif cmd_type == 'drone_emergency' and drone_id in self.drones:
            # Individual drone emergency
            threading.Thread(target=self.drones[drone_id].emergency_stop).start()
        
        elif cmd_type == 'drone_land' and drone_id in self.drones:
            # Individual drone land
            threading.Thread(target=self.drones[drone_id].land).start()
    
    def add_drone(self, drone_id, drone):
        """Add drone instance"""
        self.drones[drone_id] = drone
    
    def shutdown(self):
        """Shutdown server"""
        print("Shutting down ROS telemetry server")
        self.running = False
        for client in self.clients:
            client.close()
        self.server_socket.close()


class FleetROSTelemetryManager:
    """Manage ROS telemetry for multiple drones"""
    
    def __init__(self):
        print("Starting Fleet ROS Telemetry Manager")
        
        # Initialize ROS node once for the entire telemetry system
        try:
            rospy.init_node('fleet_telemetry_manager', anonymous=False, disable_signals=True)
            print("ROS node initialized: fleet_telemetry_manager")
        except rospy.exceptions.ROSException as e:
            print(f"ROS node initialization error: {e}")
        
        # Start telemetry server (different port than pymavlink version)
        self.server = TelemetryServer(host='127.0.0.1', port=5556)
        
        # Configuration: drone_id -> ROS namespace
        # Supports up to 6 drones
        self.drone_configs = {
            1: 'uav0',
            2: 'uav1',
            3: 'uav2',
            # Uncomment as more drones are added:
            # 4: 'uav3',
            # 5: 'uav4',
            # 6: 'uav5',
        }
        
        # Initialize all drones
        for drone_id, namespace in self.drone_configs.items():
            try:
                drone = ROSTelemetryClient(drone_id, namespace, self.server)
                self.server.add_drone(drone_id, drone)
            except Exception as e:
                print(f"Failed to initialize Drone {drone_id}: {e}")
        
        print("Fleet ROS Telemetry Manager initialized")
    
    def run(self):
        """Run the telemetry manager"""
        print("ROS Telemetry manager running. Press Ctrl+C to exit.")
        try:
            rospy.spin()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all drones"""
        self.server.shutdown()
        for drone in self.server.drones.values():
            drone.shutdown()


if __name__ == '__main__':
    try:
        manager = FleetROSTelemetryManager()
        manager.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
