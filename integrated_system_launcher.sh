#!/bin/bash
# Master script to run the entire integrated system
# Run this on the ROBOT (not the server)

set -e  # Exit on any error

SCRIPTS_PATH="$HOME/BlackDog_Enforcer"
SERVER_IP="${1:-10.33.168.158}"  # Pass as argument or use default

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  BlackDog Integrated System Launcher  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Server IP: $SERVER_IP"
echo "  Scripts Path: $SCRIPTS_PATH"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if [ ! -f "$SCRIPTS_PATH/room_baseline.json" ]; then
    echo -e "${RED}✗ Baseline map not found!${NC}"
    echo -e "${YELLOW}Run mapping first: ./run_integrated_system.sh --map${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Baseline map found${NC}"
fi

if [ ! -f "$SCRIPTS_PATH/Car_Controller.py" ]; then
    echo -e "${RED}✗ Car_Controller.py not found!${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Car_Controller found${NC}"
fi

if [ ! -f "$SCRIPTS_PATH/obstruction_handler.py" ]; then
    echo -e "${RED}obstruction_handler.py not found!${NC}"
    echo -e "${YELLOW}Make sure you created obstruction_handler.py${NC}"
    exit 1
else
    echo -e "${GREEN}obstruction_handler found${NC}"
fi

echo ""
echo -e "${GREEN}All prerequisites met!${NC}"
echo ""

# Handle mapping mode
if [ "$1" == "--map" ]; then
    echo -e "${YELLOW}=== MAPPING MODE ===${NC}"
    echo "Creating baseline map from LIDAR data..."
    echo "This will take ~1-2 minutes. Please keep environment still."
    echo ""
    
    cd "$SCRIPTS_PATH"
    python3 client.py --ip "$SERVER_IP" | python3 Lidar_Mapper.py -n 100
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Baseline map created successfully!${NC}"
        echo "You can now run: ./run_integrated_system.sh"
    else
        echo -e "${RED}✗ Mapping failed${NC}"
        exit 1
    fi
    exit 0
fi

# Handle help
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: ./run_integrated_system.sh [OPTIONS] [SERVER_IP]"
    echo ""
    echo "OPTIONS:"
    echo "  --map              Create/update baseline map"
    echo "  --help             Show this help message"
    echo ""
    echo "ARGUMENTS:"
    echo "  SERVER_IP          IP of Pi 5 server (default: 10.33.134.54)"
    echo ""
    echo "EXAMPLES:"
    echo "  ./run_integrated_system.sh                    # Run with default IP"
    echo "  ./run_integrated_system.sh 192.168.1.100     # Run with custom IP"
    echo "  ./run_integrated_system.sh --map              # Create baseline"
    exit 0
fi

echo -e "${YELLOW}Starting integrated system...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the integrated pipeline:
# Client (connects to server) | Monitor (detects + integrates with car control)
cd "$SCRIPTS_PATH"

python3 client.py --ip "$SERVER_IP" | python3 Lidar_Monitor.py
