# Architecture Comparison: PyMAVLink vs ROS Version

## PyMAVLink Version Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PX4 SITL (Host Computer)                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  Drone 1 │   │  Drone 2 │   │  Drone 3 │   │  Drone 4 │    │
│  │  :14540  │   │  :14541  │   │  :14542  │   │  :14543  │    │
│  └─────┬────┘   └─────┬────┘   └─────┬────┘   └─────┬────┘    │
└────────┼──────────────┼──────────────┼──────────────┼──────────┘
         │              │              │              │
         │ UDP MAVLink  │ UDP MAVLink  │ UDP MAVLink  │ UDP MAVLink
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│           pymavlink_telemetry.py (Host/Container)               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MavlinkTelemetry (per drone)                            │  │
│  │  - Direct MAVLink connection                             │  │
│  │  - Parses HEARTBEAT, SYS_STATUS, LOCAL_POSITION_NED      │  │
│  │  - Sends commands via MAVLink                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ TCP Socket (localhost:5555)       │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           TelemetryServer                                │  │
│  │           - JSON telemetry broadcast                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ TCP Connection
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          Docker Container: drone_fleet_dashboard                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     drone_fleet_dashboard.py (RQt Plugin)                │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  TelemetryClient                                  │   │  │
│  │  │  - Connects to port 5555                          │   │  │
│  │  │  - Receives JSON telemetry                        │   │  │
│  │  │  - Sends JSON commands                            │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  GUI (6 Drone Panels)                            │   │  │
│  │  │  - IP Address Input                              │   │  │
│  │  │  - Battery / Mode / Position Display             │   │  │
│  │  │  - Command Buttons                               │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## ROS Version Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PX4 SITL (Host Computer)                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│  │  Drone 1 │   │  Drone 2 │   │  Drone 3 │                    │
│  │  :14540  │   │  :14541  │   │  :14542  │                    │
│  └─────┬────┘   └─────┬────┘   └─────┬────┘                    │
└────────┼──────────────┼──────────────┼──────────────────────────┘
         │              │              │
         │ UDP MAVLink  │ UDP MAVLink  │ UDP MAVLink
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│              MAVROS Container (Separate)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ uav0/mavros  │  │ uav1/mavros  │  │ uav2/mavros  │         │
│  │ - state      │  │ - state      │  │ - state      │         │
│  │ - battery    │  │ - battery    │  │ - battery    │         │
│  │ - local_pos  │  │ - local_pos  │  │ - local_pos  │         │
│  │ - services   │  │ - services   │  │ - services   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ ROS Topics       │ ROS Topics       │ ROS Topics
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│             ros_telemetry.py (Host/Container)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ROSTelemetryClient (per drone)                          │  │
│  │  - Subscribes to /uav{N}/mavros/local_position/pose      │  │
│  │  - Subscribes to /uav{N}/mavros/state                    │  │
│  │  - Subscribes to /uav{N}/mavros/battery                  │  │
│  │  - Uses MAVROS services for commands                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ TCP Socket (localhost:5556)       │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           TelemetryServer                                │  │
│  │           - JSON telemetry broadcast                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ TCP Connection
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│        Docker Container: drone_fleet_dashboard_ros               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     drone_fleet_dashboard_ros.py (RQt Plugin)            │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  TelemetryClient                                  │   │  │
│  │  │  - Connects to port 5556                          │   │  │
│  │  │  - Receives JSON telemetry                        │   │  │
│  │  │  - Sends JSON commands                            │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  ┌──────────────────────────────────────────────────┐   │  │
│  │  │  GUI (6 Drone Panels)                            │   │  │
│  │  │  - ROS Namespace Display                         │   │  │
│  │  │  - Battery / Mode / Position Display             │   │  │
│  │  │  - Command Buttons                               │   │  │
│  │  └──────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Differences Summary

### Communication Layer
| PyMAVLink | ROS |
|-----------|-----|
| Direct UDP MAVLink | ROS Topics via MAVROS |
| Port-based (14540, 14541...) | Namespace-based (uav0, uav1...) |
| No middleware | MAVROS middleware required |

### Data Acquisition
| PyMAVLink | ROS |
|-----------|-----|
| HEARTBEAT message | /mavros/state topic |
| SYS_STATUS message | /mavros/battery topic |
| LOCAL_POSITION_NED | /mavros/local_position/pose |
| Direct parsing | Message callbacks |

### Command Execution
| PyMAVLink | ROS |
|-----------|-----|
| MAV_CMD_* via MAVLink | MAVROS service calls |
| Direct command_long_send() | CommandBool, SetMode services |
| Custom mode numbers | Named modes (strings) |

### Ports
| PyMAVLink | ROS |
|-----------|-----|
| Telemetry: 5555 | Telemetry: 5556 |
| PX4: 14540-14545 | MAVROS handles PX4 |

### Container Names
| PyMAVLink | ROS |
|-----------|-----|
| drone_fleet_dashboard | drone_fleet_dashboard_ros |

### GUI Labels
| PyMAVLink | ROS |
|-----------|-----|
| "IP ADDR: 192.168.x.x" | "ROS NS: uav0" |

## Running Both Versions Simultaneously

Both versions use:
- ✅ Same Dockerfile (ROS Noetic base)
- ✅ Same RQt framework
- ✅ Different ports (no conflicts)
- ✅ Different container names
- ✅ Different plugin classes

```bash
# Terminal 1: PyMAVLink version
docker-compose up

# Terminal 2: ROS version  
docker-compose -f docker-compose-ros.yaml up
```

## Integration Points

### With PyMAVLink Version
- Independent operation
- Can monitor same drones via different protocols
- Useful for protocol comparison

### With External ROS Nodes
- Compatible with rosbag recording
- Can integrate with rviz for visualization
- Can coordinate with motion planning nodes
- Can use ROS parameter server for configuration

## Future Enhancements

### PyMAVLink Version
- Direct hardware integration
- Custom MAVLink commands
- Low-latency control

### ROS Version
- Integration with ROS navigation stack
- Formation control via ROS actions
- Mission planning with move_base
- Integration with sensor fusion nodes
- rosbag recording and playback
