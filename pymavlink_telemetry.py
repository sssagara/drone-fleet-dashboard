#!/usr/bin/env python3

from pymavlink import mavutil
import threading
import time
import json
import socket

class MavlinkTelemetry:
    def __init__(self, connection_string, drone_id, server):
        """
        Initialize MAVLink connection
        
        Args:
            connection_string: MAVLink connection (e.g., 'udpin:0.0.0.0:14540')
            drone_id: Drone ID number (1, 2, 3, etc.)
            server: Reference to TelemetryServer for data updates
        """
        self.drone_id = drone_id
        self.connection_string = connection_string
        self.server = server
        
        # Connect to vehicle
        print(f"Drone {drone_id}: Connecting to {connection_string}")
        self.master = mavutil.mavlink_connection(connection_string)
        
        # Wait for heartbeat
        print(f"Drone {drone_id}: Waiting for heartbeat...")
        self.master.wait_heartbeat()
        print(f"Drone {drone_id}: Heartbeat received (system {self.master.target_system} component {self.master.target_component})")
        
        # Store latest data
        self.battery_voltage = 0.0
        self.flight_mode = "UNKNOWN"
        self.local_position = [0.0, 0.0, 0.0]
        self.armed = False
        
        # Request data streams
        self.request_data_streams()
        
        # Start telemetry thread
        self.running = True
        self.telemetry_thread = threading.Thread(target=self.telemetry_loop)
        self.telemetry_thread.daemon = True
        self.telemetry_thread.start()
        
        print(f"Drone {drone_id}: Telemetry system initialized")
    
    def request_data_streams(self):
        """Request MAVLink data streams"""
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            10,  # 10 Hz
            1    # Start
        )
    
    def telemetry_loop(self):
        """Main telemetry processing loop"""
        while self.running:
            try:
                msg = self.master.recv_match(blocking=True, timeout=1.0)
                
                if msg is None:
                    continue
                
                msg_type = msg.get_type()
                
                # Process battery data
                if msg_type == 'SYS_STATUS':
                    self.battery_voltage = msg.voltage_battery / 1000.0  # Convert mV to V
                    self.update_server_data()
                
                # Process flight mode
                elif msg_type == 'HEARTBEAT':
                    mode = mavutil.mode_string_v10(msg)
                    self.flight_mode = mode
                    # Extract armed status from base_mode
                    self.armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                    self.update_server_data()
                
                # Process local position
                elif msg_type == 'LOCAL_POSITION_NED':
                    # Convert NED to ENU for consistency
                    self.local_position = [msg.x, msg.y, -msg.z]
                    self.update_server_data()
                    
            except Exception as e:
                print(f"Drone {self.drone_id}: Telemetry error - {e}")
    
    def update_server_data(self):
        """Update server with latest telemetry data"""
        data = {
            'battery_voltage': self.battery_voltage,
            'flight_mode': self.flight_mode,
            'position': self.local_position,
            'armed': self.armed
        }
        # Debug output every 2 seconds
        if not hasattr(self, '_last_debug') or time.time() - self._last_debug > 2:
            print(f"Drone {self.drone_id} telemetry: Voltage={self.battery_voltage:.2f}V, Mode={self.flight_mode}, Pos={self.local_position}, Armed={self.armed}")
            self._last_debug = time.time()
        self.server.update_drone_data(self.drone_id, data)
        print(f"DEBUG: Drone {self.drone_id} - type: {type(self.drone_id)}, value: {repr(self.drone_id)}")
        
    
    def arm(self):
        """Arm the vehicle"""
        print(f"Drone {self.drone_id}: Arming...")
        self.master.arducopter_arm()
        self.master.motors_armed_wait()
        print(f"Drone {self.drone_id}: Armed")
    
    def disarm(self):
        """Disarm the vehicle"""
        print(f"Drone {self.drone_id}: Disarming...")
        self.master.arducopter_disarm()
        self.master.motors_disarmed_wait()
        print(f"Drone {self.drone_id}: Disarmed")
    
    def takeoff(self, altitude=10.0):
        """
        Takeoff to specified altitude
        
        Args:
            altitude: Target altitude in meters
        """
        print(f"Drone {self.drone_id}: Preparing for takeoff to {altitude}m")
        
        # Set mode to GUIDED first (required for PX4)
        print(f"Drone {self.drone_id}: Setting mode to GUIDED")
        self.set_mode('GUIDED')
        
        time.sleep(1)
        
        # Arm the vehicle
        print(f"Drone {self.drone_id}: Arming...")
        self.master.arducopter_arm()
        
        time.sleep(2)
        
        # Wait for armed confirmation
        print(f"Drone {self.drone_id}: Waiting for armed status...")
        self.master.motors_armed_wait()
        print(f"Drone {self.drone_id}: Armed confirmed")
        
        time.sleep(1)
        
        # Send takeoff command
        print(f"Drone {self.drone_id}: Sending takeoff command")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,  # confirmation
            0, 0, 0, 0,  # params 1-4
            0, 0,  # latitude, longitude (not used for local)
            altitude  # altitude
        )
        
        # Wait for command acknowledgment
        ack = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3)
        if ack and ack.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
            if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                print(f"Drone {self.drone_id}: Takeoff command accepted")
            else:
                print(f"Drone {self.drone_id}: Takeoff command rejected: {ack.result}")
        
        print(f"Drone {self.drone_id}: Takeoff sequence complete")
    
    def land(self):
        """Land the vehicle"""
        print(f"Drone {self.drone_id}: Landing...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,  # confirmation
            0, 0, 0, 0,  # params 1-4
            0, 0, 0  # latitude, longitude, altitude
        )
        
        print(f"Drone {self.drone_id}: Land command sent")
    
    def emergency_stop(self):
        """Emergency flight termination"""
        print(f"Drone {self.drone_id}: EMERGENCY FLIGHT TERMINATION!")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_DO_FLIGHTTERMINATION,
            0,  # confirmation
            1,  # terminate (1 = terminate, 0 = restore)
            0, 0, 0, 0, 0, 0
        )
        
        print(f"Drone {self.drone_id}: Flight termination command sent")
    
    def set_mode(self, mode):
        """
        Set flight mode
        
        Args:
            mode: Flight mode string (e.g., 'GUIDED', 'LAND', 'RTL')
        """
        # Get mode ID
        if mode not in self.master.mode_mapping():
            print(f"Drone {self.drone_id}: Unknown mode {mode}")
            return
        
        mode_id = self.master.mode_mapping()[mode]
        
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        
        print(f"Drone {self.drone_id}: Set mode to {mode}")
    
    def shutdown(self):
        """Shutdown telemetry system"""
        print(f"Drone {self.drone_id}: Shutting down telemetry")
        self.running = False
        if self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=2.0)


class TelemetryServer:
    """TCP server to communicate telemetry data to dashboard"""
    
    def __init__(self, host='127.0.0.1', port=5555):
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
        
        print(f"Telemetry server listening on {self.host}:{self.port}")
        
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
                print(f"Error sending to client: {e}")
                self.clients.remove(client)
    
    def send_to_client(self, client):
        """Send data to a specific client"""
        message = json.dumps({
            'type': 'telemetry',
            'data': self.drone_data
        }) + '\n'
        try:
            client.sendall(message.encode())
            # Debug: print data being sent
            if self.drone_data:
                print(f"Sent telemetry to client: {len(self.drone_data)} drones")
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
                        print(f"Command processing error: {e}")
                        self.clients.remove(client)
            time.sleep(0.01)
    
    def handle_command(self, command):
        """Handle command from dashboard"""
        cmd_type = command.get('type')
        drone_id = command.get('drone_id')
        
        print(f"Received command: {command}")
        
        if cmd_type == 'launch':
            # Launch all drones
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
        print("Shutting down telemetry server")
        self.running = False
        for client in self.clients:
            client.close()
        self.server_socket.close()


class FleetTelemetryManager:
    """Manage telemetry for multiple drones"""
    
    def __init__(self):
        print("Starting Fleet Telemetry Manager")
        
        # Start telemetry server
        self.server = TelemetryServer()
        
        # Configuration: drone_id -> connection_string
        self.drone_configs = {
            1: 'udpin:0.0.0.0:14540',
            2: 'udpin:0.0.0.0:14541',
        }
        
        # Initialize all drones
        for drone_id, connection_string in self.drone_configs.items():
            try:
                drone = MavlinkTelemetry(connection_string, drone_id, self.server)
                self.server.add_drone(drone_id, drone)
            except Exception as e:
                print(f"Failed to initialize Drone {drone_id}: {e}")
        
        print("Fleet Telemetry Manager initialized")
    
    def run(self):
        """Run the telemetry manager"""
        print("Telemetry manager running. Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all drones"""
        self.server.shutdown()


if __name__ == '__main__':
    try:
        manager = FleetTelemetryManager()
        manager.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()