#!/bin/bash
# Configuration
SCRIPTS_PATH="$HOME/BlackDog_Enforcer"
MAPPER_SCRIPT="$SCRIPTS_PATH/Lidar_Mapper.py"
MONITOR_SCRIPT="$SCRIPTS_PATH/Lidar_Monitor.py"
CLIENT_SCRIPT="$SCRIPTS_PATH/client.py"

# IMPORTANT: Your Pi 5 Server IP
SERVER_IP="10.33.134.54"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' 

# 1. Check for Mapping Mode
if [ "$1" == "map" ]; then
    echo -e "${YELLOW}=== MODE: MAPPING ENVIRONMENT ===${NC}"
    # We pass the SERVER_IP to the client.py as an argument
    python3 "$CLIENT_SCRIPT" --ip "$SERVER_IP" | python3 "$MAPPER_SCRIPT"
    exit 0
fi

# 2. Check for Monitoring Mode
echo -e "${GREEN}=== MODE: MONITORING & ENFORCING ===${NC}"
echo -e "${YELLOW}LiDAR will detect obstructions and trigger:${NC}"
echo -e "  1. Steering car to face object"
echo -e "  2. Running CNN classification"
echo -e "  3. Executing avoidance if confirmed"
echo ""

# Check if baseline exists before starting
if [ ! -f "room_baseline.json" ]; then
    echo -e "${RED}Error: room_baseline.json not found!${NC}"
    echo -e "${YELLOW}Please run: ./ProcessAndClient.sh map${NC}"
    exit 1
fi

# Pipe the client data (with IP) into the monitor
python3 "$CLIENT_SCRIPT" --ip "$SERVER_IP" | python3 "$MONITOR_SCRIPT"
