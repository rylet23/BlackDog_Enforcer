#!/bin/bash
# Start Lidar Server on Pi 5
# This script starts the RPLidar and streams data to clients

# Configuration
LIDAR_SDK_PATH="$HOME/rplidar_sdk"
ULTRA_SIMPLE="$LIDAR_SDK_PATH/output/Linux/Release/ultra_simple"
LIDAR_PORT="/dev/ttyUSB0"
BAUDRATE="115200"
SERVER_SCRIPT="$HOME/BlackDog_Enforcer/server.py"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Lidar Server ===${NC}"

# Check if ultra_simple exists
if [ ! -f "$ULTRA_SIMPLE" ]; then
    echo -e "${RED}Error: ultra_simple not found at $ULTRA_SIMPLE${NC}"
    echo "Please compile the RPLidar SDK first:"
    echo "  cd $LIDAR_SDK_PATH"
    echo "  make"
    exit 1
fi

# Check if server script exists
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo -e "${RED}Error: lidar_server.py not found at $SERVER_SCRIPT${NC}"
    exit 1
fi

# Check if device exists
if [ ! -e "$LIDAR_PORT" ]; then
    echo -e "${RED}Error: Lidar device not found at $LIDAR_PORT${NC}"
    echo "Available USB devices:"
    ls -l /dev/ttyUSB* 2>/dev/null || echo "No /dev/ttyUSB* devices found"
    exit 1
fi

echo "Lidar device: $LIDAR_PORT"
echo "Baudrate: $BAUDRATE"
echo "Server listening on port 5555"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run ultra_simple and pipe to server
"$ULTRA_SIMPLE" --channel --serial "$LIDAR_PORT" "$BAUDRATE" | python3 "$SERVER_SCRIPT"

echo -e "${GREEN}Server stopped${NC}"