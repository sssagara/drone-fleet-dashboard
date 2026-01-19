# Drone Fleet Dashboard - Quick Start Guide

## Overview

This project provides two versions of a drone fleet monitoring and control dashboard:

1. **PyMAVLink Version** - Direct MAVLink communication with PX4 autopilots
2. **ROS Version** - ROS/MAVROS topic-based communication (NEW)

Both versions can run simultaneously without interfering with each other.

## Quick Start

### PyMAVLink Version (Original)
```bash
# Terminal 1: Start telemetry script
docker exec -it drone_fleet_dashboard bash
python3 /root/catkin_ws/src/pymavlink_telemetry.py

# Terminal 2: Launch dashboard
docker-compose up
```

### ROS Version (New)
```bash
# Make sure MAVROS is running first!

# Terminal 1: Start ROS telemetry script
docker exec -it drone_fleet_dashboard_ros bash
./run_ros_telemetry.sh

# Terminal 2: Launch dashboard
docker-compose -f docker-compose-ros.yaml up
```

## File Structure

```
drone-fleet-dashboard/
├── pymavlink_telemetry.py              # PyMAVLink telemetry script
├── ros_telemetry.py                    # ROS telemetry script (NEW)
├── run_ros_telemetry.sh               # Helper script for ROS version (NEW)
├── docker-compose.yaml                # PyMAVLink version docker config
├── docker-compose-ros.yaml            # ROS version docker config (NEW)
├── Dockerfile                         # Shared ROS Noetic base image
├── README.md                          # This file
├── README_ROS.md                      # Detailed ROS version documentation (NEW)
└── src/
    └── drone_fleet_dashboard/
        ├── launch/
        │   ├── drone_fleet_dashboard.launch       # PyMAVLink launch
        │   └── drone_fleet_dashboard_ros.launch   # ROS launch (NEW)
        ├── src/drone_fleet_dashboard/
        │   ├── drone_fleet_dashboard.py           # PyMAVLink GUI
        │   └── drone_fleet_dashboard_ros.py       # ROS GUI (NEW)
        ├── plugin.xml                 # RQt plugin registration (both versions)
        ├── package.xml               # ROS package manifest
        └── CMakeLists.txt            # Catkin build config
```

## Version Comparison

| Feature | PyMAVLink Version | ROS Version |
|---------|------------------|-------------|
| **Communication** | Direct UDP MAVLink | ROS Topics via MAVROS |
| **Port** | 5555 | 5556 |
| **Connection** | IP:Port (UDP) | ROS Namespaces |
| **Dependencies** | pymavlink | MAVROS, ROS Noetic |
| **Advantages** | Direct hardware access | ROS ecosystem integration |
| **Use Case** | Direct PX4 connection | Multi-drone ROS systems |

## Which Version Should I Use?

### Use PyMAVLink Version When:
- Working with PX4 SITL directly
- Need low-latency direct MAVLink communication
- Simpler setup without ROS infrastructure
- Single-drone or simple multi-drone scenarios

### Use ROS Version When:
- Already using ROS/MAVROS for drone control
- Want to integrate with ROS ecosystem (rosbag, rviz, etc.)
- Working with namespaced multi-drone systems
- Need to coordinate with other ROS nodes

## Prerequisites

### PyMAVLink Version
- Docker and docker-compose
- PX4 SITL instances running on UDP ports (14540, 14541, etc.)
- X11 display for GUI

### ROS Version
- Docker and docker-compose
- ROS Noetic with MAVROS running
- MAVROS connected to PX4 SITL with namespaces (uav0, uav1, uav2)
- X11 display for GUI
- ROS master running and accessible

## Installation

1. Clone the repository:
```bash
cd /path/to/your/workspace
git clone <repository-url>
cd drone-fleet-dashboard
```

2. Allow X11 connections:
```bash
xhost +local:docker
```

3. Build the Docker image:
```bash
docker-compose build
```

## Detailed Usage

### PyMAVLink Version

See original documentation in the repository.

### ROS Version

See [README_ROS.md](README_ROS.md) for comprehensive documentation including:
- Architecture overview
- ROS topic details
- Configuration options
- Troubleshooting guide
- Development notes

## Running Both Versions Simultaneously

You can run both versions at the same time for comparison or different use cases:

```bash
# Terminal 1: PyMAVLink version
docker-compose up

# Terminal 2: ROS version
docker-compose -f docker-compose-ros.yaml up
```

They use different:
- Ports (5555 vs 5556)
- Container names
- Dashboard classes
- Telemetry scripts

## Development

### Building After Changes

```bash
# Rebuild the catkin workspace
docker exec -it drone_fleet_dashboard_ros bash
cd /root/catkin_ws
catkin_make
source devel/setup.bash
```

### Testing Individual Components

#### Test ROS Topics
```bash
# List all MAVROS topics
rostopic list | grep mavros

# Monitor specific topics
rostopic echo /uav0/mavros/local_position/pose
rostopic echo /uav0/mavros/state
rostopic echo /uav0/mavros/battery
```

#### Test Telemetry Connection
```bash
# Run telemetry script in foreground
docker exec -it drone_fleet_dashboard_ros bash
python3 /root/catkin_ws/src/ros_telemetry.py
```

## Troubleshooting

### Common Issues

1. **"Connection refused" when starting dashboard**
   - Make sure telemetry script is running first
   - Check port numbers match (5555 for PyMAVLink, 5556 for ROS)

2. **"Cannot connect to X server"**
   - Run `xhost +local:docker`
   - Check DISPLAY environment variable

3. **"No ROS master" (ROS version)**
   - Ensure ROS master is running: `roscore`
   - Check ROS_MASTER_URI: `echo $ROS_MASTER_URI`

4. **Drones show as OFFLINE**
   - **PyMAVLink**: Check PX4 SITL is running and UDP ports are correct
   - **ROS**: Check MAVROS is running and topics are being published

### Getting Help

For ROS-specific issues, see [README_ROS.md](README_ROS.md) troubleshooting section.

## Contributing

When adding features:
1. Maintain separation between PyMAVLink and ROS versions
2. Use appropriate file naming (e.g., `*_ros.py` for ROS versions)
3. Update both README files if applicable
4. Test both versions to ensure no conflicts

## License

[Add your license here]

## Acknowledgments

- ROS control manager reference: https://github.com/Eightfingers/ros1_ws
- PX4 Autopilot project
- MAVROS project
