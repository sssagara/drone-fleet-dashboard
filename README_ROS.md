# Drone Fleet Dashboard - ROS Version

This directory contains the ROS/MAVROS version of the Drone Fleet Dashboard system. It works alongside the PyMAVLink version without interfering.

## Architecture

```
PX4 SITL (uav0, uav1, uav2) 
    ↓
MAVROS (separate container with namespaced topics)
    ↓
ROS Telemetry Script (ros_telemetry.py)
    ↓ (TCP Socket - Port 5556)
Fleet Dashboard GUI (drone_fleet_dashboard_ros.py)
```

## Files

### ROS-Specific Files
- `ros_telemetry.py` - ROS telemetry intermediary script that subscribes to MAVROS topics
- `drone_fleet_dashboard_ros.py` - ROS version of the dashboard GUI
- `drone_fleet_dashboard_ros.launch` - Launch file for the ROS dashboard
- `docker-compose-ros.yaml` - Docker compose configuration for ROS version

### Shared Files (Used by Both Versions)
- `Dockerfile` - Base ROS Noetic image with rqt
- `CMakeLists.txt` - Catkin build configuration
- `package.xml` - ROS package manifest
- `plugin.xml` - RQt plugin registration (now includes both versions)

### PyMAVLink Version Files (Unchanged)
- `pymavlink_telemetry.py` - PyMAVLink telemetry script
- `drone_fleet_dashboard.py` - Original PyMAVLink dashboard
- `drone_fleet_dashboard.launch` - Launch file for PyMAVLink version
- `docker-compose.yaml` - Docker compose for PyMAVLink version

## ROS Topics

The ROS version subscribes to the following MAVROS topics for each drone (namespaced by uav0, uav1, uav2, etc.):

- `/{namespace}/mavros/local_position/pose` (geometry_msgs/PoseStamped) - Local position
- `/{namespace}/mavros/state` (mavros_msgs/State) - Flight mode and armed status
- `/{namespace}/mavros/battery` (sensor_msgs/BatteryState) - Battery voltage

## Setup and Usage

### Prerequisites
1. MAVROS container running with multiple drone namespaces (uav0, uav1, uav2)
2. PX4 SITL instances running and connected to MAVROS
3. ROS master running on host (or shared via /tmp/ros)

### Running the ROS Version

#### Option 1: Using docker-compose (Recommended)
```bash
# Build and start the ROS dashboard
docker-compose -f docker-compose-ros.yaml up

# Or in detached mode
docker-compose -f docker-compose-ros.yaml up -d
```

#### Option 2: Manual Launch

1. Start the container in bash mode:
```bash
docker-compose -f docker-compose-ros.yaml run --rm drone_fleet_dashboard_ros bash
```

2. Inside the container, build the workspace:
```bash
cd /root/catkin_ws
source devel/setup.bash
catkin_make
source devel/setup.bash
```

3. Launch the ROS telemetry script (in one terminal):
```bash
python3 /root/catkin_ws/src/ros_telemetry.py
```

4. Launch the dashboard (in another terminal/exec):
```bash
docker exec -it drone_fleet_dashboard_ros bash
cd /root/catkin_ws
source devel/setup.bash
roslaunch drone_fleet_dashboard drone_fleet_dashboard_ros.launch
```

### Debugging the ROS Telemetry Script

To run just the telemetry script for debugging:

```bash
# Start container with bash
docker exec -it drone_fleet_dashboard_ros bash

# Run the telemetry script
cd /root/catkin_ws/src
python3 ros_telemetry.py
```

You should see output like:
```
Starting Fleet ROS Telemetry Manager
ROS Telemetry server listening on 127.0.0.1:5556
Drone 1: ROS Telemetry client initialized for namespace 'uav0'
Drone 2: ROS Telemetry client initialized for namespace 'uav1'
Drone 3: ROS Telemetry client initialized for namespace 'uav2'
```

## Configuration

### Drone Namespaces
Edit `ros_telemetry.py` to configure drone namespaces:

```python
self.drone_configs = {
    1: 'uav0',  # Drone 1 → uav0 namespace
    2: 'uav1',  # Drone 2 → uav1 namespace
    3: 'uav2',  # Drone 3 → uav2 namespace
    # Add more as needed
}
```

### Communication Port
- ROS version uses port **5556** (different from PyMAVLink's 5555)
- Change in both `ros_telemetry.py` and `drone_fleet_dashboard_ros.py` if needed

## Running Both Versions Simultaneously

You can run both PyMAVLink and ROS versions at the same time:

```bash
# Terminal 1: PyMAVLink version
docker-compose -f docker-compose.yaml up

# Terminal 2: ROS version
docker-compose -f docker-compose-ros.yaml up
```

They use different ports (5555 vs 5556) and different dashboard classes, so they won't interfere.

## Troubleshooting

### Dashboard shows all drones offline
- Check if MAVROS is running: `rostopic list | grep mavros`
- Verify MAVROS topics are publishing: `rostopic echo /uav0/mavros/state`
- Check if telemetry script is running and connected
- Verify ROS_MASTER_URI is set correctly

### ROS telemetry script can't connect to topics
- Ensure MAVROS container is running with correct namespaces
- Check network_mode: host in docker-compose
- Verify ROS master is accessible: `rostopic list`

### No battery data
- Some SITL configurations don't publish battery data
- Check if battery topic exists: `rostopic echo /uav0/mavros/battery`

### Connection timeout
- MAVROS services may take time to initialize
- The script has 5-second timeouts - increase if needed in `ros_telemetry.py`

## Development Notes

### Adding New Commands
To add new commands:

1. Add button in `drone_fleet_dashboard_ros.py`
2. Add command handler in `TelemetryServer.handle_command()` in `ros_telemetry.py`
3. Implement the actual command in `ROSTelemetryClient` class

### Testing Individual Components

Test ROS topics directly:
```bash
# Check if topics exist
rostopic list | grep uav0

# Monitor position
rostopic echo /uav0/mavros/local_position/pose

# Monitor state
rostopic echo /uav0/mavros/state

# Monitor battery
rostopic echo /uav0/mavros/battery
```

## Differences from PyMAVLink Version

| Feature | PyMAVLink Version | ROS Version |
|---------|------------------|-------------|
| Communication | Direct MAVLink | ROS Topics via MAVROS |
| Port | 5555 | 5556 |
| Drone Connection | UDP ports | ROS namespaces |
| Flight Control | MAVLink commands | MAVROS services |
| Advantages | Direct hardware control | ROS ecosystem integration |

## Next Steps

1. **Formation Control**: Implement multi-drone formation logic
2. **Mission Planning**: Add waypoint mission support via MAVROS
3. **Advanced Telemetry**: Add velocity, attitude, GPS data
4. **Recording**: Integrate with rosbag for mission recording
5. **Simulation Integration**: Connect to Gazebo/SITL swarm simulations

## References

- Control Manager Example: https://github.com/Eightfingers/ros1_ws/blob/master/src/zmq_comms/scripts/control_manager.py
- MAVROS Documentation: http://wiki.ros.org/mavros
- PX4 SITL Multi-Vehicle: https://docs.px4.io/main/en/simulation/
