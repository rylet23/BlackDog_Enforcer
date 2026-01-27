#!/bin/bash
# Start Lidar Server on Pi 5
# Automatically stops motor when client disconnects or Ctrl+C

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

# Store PIDs for cleanup
LIDAR_PID=""
SERVER_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping processes..."

    # Kill server first
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi

    # Send interrupt to ultra_simple so it stops motor properly
    if [ ! -z "$LIDAR_PID" ]; then
        echo "Stopping lidar motor..."
        kill -INT $LIDAR_PID 2>/dev/null
        sleep 1
        # Force kill if still running
        kill -9 $LIDAR_PID 2>/dev/null
    fi

    echo -e "${GREEN}Lidar stopped${NC}"
    exit 0
}

# Trap signals
trap cleanup INT TERM EXIT

echo -e "${GREEN}=== Starting Lidar Server ===${NC}"

# Check if ultra_simple exists
if [ ! -f "$ULTRA_SIMPLE" ]; then
    echo -e "${RED}Error: ultra_simple not found at $ULTRA_SIMPLE${NC}"
    exit 1
fi

# Check if server script exists
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo -e "${RED}Error: server.py not found at $SERVER_SCRIPT${NC}"
    exit 1
fi

# Check if device exists
if [ ! -e "$LIDAR_PORT" ]; then
    echo -e "${RED}Error: Lidar device not found at $LIDAR_PORT${NC}"
    exit 1
fi

echo "Lidar device: $LIDAR_PORT"
echo "Baudrate: $BAUDRATE"
echo "Server listening on port 5555"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Create a named pipe (FIFO) for communication
PIPE="/tmp/lidar_pipe_$$"
mkfifo "$PIPE"

# Cleanup pipe on exit
trap "rm -f $PIPE; cleanup" EXIT INT TERM

# Start ultra_simple writing to pipe in background
"$ULTRA_SIMPLE" --channel --serial "$LIDAR_PORT" "$BAUDRATE" > "$PIPE" &
LIDAR_PID=$!

# Start server reading from pipe in background
python3 "$SERVER_SCRIPT" < "$PIPE" &
SERVER_PID=$!

# Wait for server to exit (client disconnect, Ctrl+C, etc.)
wait $SERVER_PID

# Server exited - trigger cleanup which will stop ultra_simple
echo "Server process ended"
cleanup