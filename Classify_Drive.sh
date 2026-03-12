#!/bin/bash
# Animal Enforcer - ZED Camera + Car Controller Integration
# Runs live animal classification and drives car when animals detected

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CNN_MODEL_DIR="$HOME/BlackDog_Enforcer/CNN_Model"
CONFIDENCE_THRESHOLD=0.90  # 90% confidence required
INFERENCE_INTERVAL=0.3     # Check every 0.3 seconds

echo -e "${GREEN}=== BlackDog Animal Enforcer ===${NC}"
echo -e "Confidence Threshold: ${YELLOW}${CONFIDENCE_THRESHOLD}${NC}"
echo -e "Inference Interval: ${YELLOW}${INFERENCE_INTERVAL}s${NC}"
echo ""

# Check if model exists
if [ ! -f "$CNN_MODEL_DIR/animal_classifier.pth" ]; then
    echo -e "${RED}ERROR: Model file not found!${NC}"
    echo "Expected: $CNN_MODEL_DIR/animal_classifier.pth"
    echo "Please train the model first using cnn-determine.py"
    exit 1
fi

# Check if camera is available
if [ ! -e "/dev/video0" ]; then
    echo -e "${RED}ERROR: Camera not found at /dev/video0${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Model found${NC}"
echo -e "${GREEN}✓ Camera found${NC}"
echo ""

echo -e "${GREEN}Starting system...${NC}"
echo "Press Ctrl+C to stop"
echo ""

# Run the pipeline: Classifier → Car Controller
cd "$CNN_MODEL_DIR"
python3 live_animal_classifier2.py \
    --mode console \
    --confidence-threshold $CONFIDENCE_THRESHOLD \
    --interval $INFERENCE_INTERVAL | \
python3 ../Car_Controller.py