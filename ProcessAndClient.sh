#!/bin/bash
# Start Car Client on Pi 4
# This script receives lidar data and controls the RC car

# Configuration
SCRIPTS_PATH="$/PycharmProjects/BlackDog_Enforcer"
CLIENT_SCRIPT="$SCRIPTS_PATH/client.py"
PROCESSOR_SCRIPT="$SCRIPTS_PATH/Lidar_Data_Processor.py"
CONTROLLER_SCRIPT="$SCRIPTS_PATH/car_controller.py"
SERVER_IP="10.33.239.139"  # Pi 5's IP address

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Car Client ===${NC}"

# Check if scripts exist
for script in "$CLIENT_SCRIPT" "$PROCESSOR_SCRIPT" "$CONTROLLER_SCRIPT"; do
    if [ ! -f "$script" ]; then
        echo -e "${RED}Error: Script not found: $script${NC}"
        exit 1
    fi
done

# Check server IP is set
if [ "$SERVER_IP" == "10.33.239.139" ]; then
    echo -e "${YELLOW}Warning: Using default server IP: $SERVER_IP${NC}"
    echo -e "${YELLOW}Edit this script to set your Pi 5's IP address${NC}"
    echo ""
fi

echo "Connecting to lidar server at: $SERVER_IP:5555"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Update the client script with correct IP (inline sed)
sed -i "s/SERVER_IP = .*/SERVER_IP = '$SERVER_IP'/" "$CLIENT_SCRIPT"

# Run the pipeline
python3 "$CLIENT_SCRIPT" | python3 "$PROCESSOR_SCRIPT" #| python3 "$CONTROLLER_SCRIPT" can add later when it works

echo -e "${GREEN}Client stopped${NC}"