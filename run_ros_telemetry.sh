#!/bin/bash
# Helper script to run the ROS telemetry intermediary

echo "=========================================="
echo "  ROS Telemetry Script for Fleet Dashboard"
echo "=========================================="
echo ""
echo "This script connects to MAVROS topics and"
echo "forwards telemetry to the dashboard GUI"
echo ""
echo "Expected MAVROS namespaces:"
echo "  - /uav0/mavros/*"
echo "  - /uav1/mavros/*"
echo "  - /uav2/mavros/*"
echo ""
echo "Dashboard will connect to: localhost:5556"
echo ""
echo "=========================================="
echo ""

# Check if ROS master is running
if ! rostopic list &>/dev/null; then
    echo "ERROR: Cannot connect to ROS master!"
    echo "Please ensure ROS master is running and ROS_MASTER_URI is set correctly"
    exit 1
fi

echo "✓ ROS master detected"
echo ""

# Check for MAVROS topics
echo "Checking for MAVROS topics..."
if rostopic list | grep -q "/uav0/mavros"; then
    echo "✓ Found uav0 MAVROS topics"
else
    echo "⚠ Warning: No uav0 MAVROS topics found"
fi

if rostopic list | grep -q "/uav1/mavros"; then
    echo "✓ Found uav1 MAVROS topics"
else
    echo "⚠ Warning: No uav1 MAVROS topics found"
fi

if rostopic list | grep -q "/uav2/mavros"; then
    echo "✓ Found uav2 MAVROS topics"
else
    echo "⚠ Warning: No uav2 MAVROS topics found"
fi

echo ""
echo "Starting ROS telemetry script..."
echo "Press Ctrl+C to stop"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Run the telemetry script
python3 "$SCRIPT_DIR/ros_telemetry.py"
