FROM ros:noetic-ros-core

# Set up environment
ENV DEBIAN_FRONTEND=noninteractive
ENV CATKIN_WS=/root/catkin_ws

# Install minimal dependencies for rqt and GUI
RUN apt-get update && apt-get install -y \
    python3-catkin-tools \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    python3-pip \
    git \
    wget \
    libgl1-mesa-glx \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libsm6 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install rqt and required GUI packages
RUN apt-get update && apt-get install -y \
    ros-noetic-rqt \
    ros-noetic-rqt-gui \
    ros-noetic-rqt-gui-py \
    ros-noetic-rqt-py-common \
    && rm -rf /var/lib/apt/lists/*

# Install MAVROS packages for ROS version
RUN apt-get update && apt-get install -y \
    ros-noetic-mavros-msgs \
    ros-noetic-geometry-msgs \
    ros-noetic-sensor-msgs \
    ros-noetic-std-msgs \
    && rm -rf /var/lib/apt/lists/*

# Install pymavlink for PyMAVLink version
RUN pip3 install pymavlink

# Create and initialize catkin workspace
RUN mkdir -p $CATKIN_WS/src
WORKDIR $CATKIN_WS

# Initialize catkin workspace
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && catkin_make"

# Set up environment variables
RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc && \
    echo "source $CATKIN_WS/devel/setup.bash" >> /root/.bashrc

# Copy the package (optional - can be mounted as volume instead)
# COPY src/ $CATKIN_WS/src/

# Build the workspace on first run
WORKDIR $CATKIN_WS

# Use bash as default shell
CMD ["/bin/bash"]
