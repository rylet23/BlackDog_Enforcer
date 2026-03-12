# BlackDog Enforcer

**Senior Design Project - Embry-Riddle Aeronautical University**  
An autonomous wildlife deterrence system for airport runway safety

## Project Overview

The BlackDog Enforcer is our senior capstone project: an autonomous RC vehicle that uses LiDAR and computer vision to detect and deter wildlife from airport runways. The system aims to improve safety for passengers, pilots, and ground crews while protecting wildlife through non-lethal deterrence methods.

### Team Members
- **Ryle Traub** - [@rylet23](https://github.com/rylet23)
- **Cole Turner** - [@Cturner-24](https://github.com/Cturner-24)
- **Robert Chaney** - [@ChaneyErau](https://github.com/chaneyerau)
- **Colin Becker**

**Faculty Advisor:** Dr. Towhidnejad  
**Project Duration:** Fall 2025 - Spring 2026

## Problem Statement

Wildlife-aircraft collisions pose serious safety risks at airports worldwide, threatening passengers, pilots, and ground crew while also causing significant damage to aircraft. Traditional wildlife management requires constant human monitoring and poses risks to personnel. Our solution provides an autonomous, 24/7 deterrence system that:

- Reduces wildlife presence on active runways
- Improves safety for all airport personnel and passengers
- Operates continuously without human intervention
- Uses non-lethal methods to protect wildlife

## System Architecture

The BlackDog Enforcer uses a distributed dual-Raspberry Pi architecture:

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│     Raspberry Pi 5          │         │     Raspberry Pi 4          │
│   (Lidar Processing)        │  TCP    │   (Vehicle Control)         │
│                             │ Socket  │                             │
│  ┌──────────────────────┐   │ ───────>│  ┌──────────────────────┐   │
│  │  RPLidar A2M8        │   │         │  │  Motor Control       │   │
│  │  Object Detection    │   │         │  │  Navigation          │   │
│  │  Location Tracking   │   │         │  │  Deterrent Trigger   │   │
│  └──────────────────────┘   │         │  └──────────────────────┘   │
└─────────────────────────────┘         └─────────────────────────────┘
```

### Key Components

**Hardware:**
- 2x Raspberry Pi (Pi 5 for lidar, Pi 4 for vehicle control)
- RPLidar A2M8 sensor for 360° environmental mapping
- ZED 2i stereo camera for object classification
- Traxxas RC car platform with brushed motor system
- 27W battery packs for Raspberry Pis
- Traxxas NiMH battery for vehicle propulsion

**Software:**
- Custom Python pipeline for data processing
- RPLidar SDK (C++) for sensor interface
- Real-time TCP socket communication
- Modular architecture for easy testing and development

## Project Goals

### Primary Objectives
1. Autonomous detection of objects on simulated runway environments
2. Real-time lidar data streaming between Raspberry Pis
3. Target identification and tracking system
4. Autonomous navigation to target location
5. Non-lethal deterrence mechanism activation
6. Integration with ZED camera for object classification

### Testing Phases
**Phase 1 (Current):** System integration and lidar communication
**Phase 2:** Testing at ERAU Eagle Landing with squirrels/raccoons
**Phase 3:** Field testing at Daytona Beach International Airport (pending approval)

## Installation & Setup

### Prerequisites
- Raspberry Pi OS (64-bit) on both Pis
- Python 3.11+
- RPLidar SDK compiled for ARM architecture

### RPLidar SDK Setup (Pi 5 Only)

```bash
# Clone and build the SDK
cd ~/
git clone https://github.com/Slamtec/rplidar_sdk.git
cd rplidar_sdk
make

# Verify build
ls output/Linux/Release/ultra_simple
```

### Network Configuration

**On Pi 5 (Lidar Server):**
```bash
# Find your IP address
hostname -I
# Note this IP for the client configuration
```

**On Pi 4 (Vehicle Controller):**
```bash
# Edit the client script with Pi 5's IP
nano ~/BlackDog_Enforcer/lidar_client.py
# Update: SERVER_IP = 'YOUR_PI5_IP_HERE'
```

## Quick Start

### Starting the System

**Terminal 1 - Pi 5 (Lidar Server):**
```bash
cd ~/BlackDog_Enforcer
./start_lidar_server.sh
```

**Terminal 2 - Pi 4 (Vehicle Client):**
```bash
cd ~/BlackDog_Enforcer
./start_car_client.sh
```

### Stopping the System
Press `Ctrl+C` on either Pi. The lidar motor will automatically stop.

## Project Structure

```
BlackDog_Enforcer/
├── start_lidar_server.sh          # Launch script for Pi 5 server
├── start_car_client.sh             # Launch script for Pi 4 client
├── lidar_server.py                 # TCP server for streaming lidar data
├── lidar_client.py                 # TCP client for receiving data
├── Lidar_Data_Processor.py         # Target detection and tracking
├── car_controller.py               # Vehicle control logic (WIP)
├── rplidar_sdk/                    # Submodule: RPLidar C++ SDK
└── README.md                       # This file
```

## How It Works

### Data Pipeline

**Pi 5 (Lidar Processing):**
```
RPLidar Sensor → ultra_simple (C++) → lidar_server.py → Network
```

**Pi 4 (Vehicle Control):**
```
Network → lidar_client.py → Lidar_Data_Processor.py → car_controller.py → Motors
```

### Detection Algorithm

1. **360° Scan:** RPLidar captures complete environmental scan
2. **Data Streaming:** Raw scan data transmitted via TCP socket
3. **Target Processing:** System identifies closest valid object
4. **Decision Making:** Determines if intervention is needed
5. **Navigation:** Vehicle moves toward target (in development)
6. **Deterrence:** Activates audio deterrent when in range (planned)

## Configuration

### Lidar Settings
Edit `start_lidar_server.sh`:
```bash
LIDAR_PORT="/dev/ttyUSB0"    # Serial port
BAUDRATE="115200"             # A2M8 default
```

### Detection Thresholds
Edit `Lidar_Data_Processor.py`:
```python
MIN_DISTANCE = 100      # Minimum detection (mm)
MAX_DISTANCE = 3000     # Maximum detection (mm)
MIN_QUALITY = 10        # Minimum scan quality
```

### Vehicle Control
Edit `car_controller.py`:
```python
STOP_DISTANCE = 200           # Stop distance (mm)
FORWARD_ANGLE_RANGE = 30      # Forward cone (degrees)
```

## Development Status

### Completed 
- [x] Dual-Pi network communication
- [x] RPLidar integration and data streaming
- [x] Real-time target detection pipeline
- [x] Modular software architecture
- [x] Emergency shutdown handling
- [x] ZED camera classification
- [x] Motor control integration
- [x] CNN-based animal classification

### In Progress 
- [ ] Autonomous navigation algorithm
- [ ] Audio deterrent system
- [ ] Field testing procedures

### Planned 
- [ ] Multi-target tracking
- [ ] Event logging system
- [ ] Battery monitoring
- [ ] FAA compliance testing

## Testing

### Individual Component Tests

**Test Lidar Connection:**
```bash
cd ~/rplidar_sdk
./output/Linux/Release/ultra_simple --channel --serial /dev/ttyUSB0 115200
```

**Test Data Processor:**
```bash
cat sample_data.txt | python3 Lidar_Data_Processor.py
```

**Test Vehicle Controller:**
```bash
echo '{"status":"target_found","angle":45,"distance":500}' | python3 car_controller.py
```

## Troubleshooting

### Lidar Not Detected
```bash
# Check USB connection
ls /dev/ttyUSB*

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Network Connection Issues
- Verify both Pis are on same network
- Check Pi 5 IP is correct in `lidar_client.py`
- Test connection: `ping <PI5_IP>`
- Check firewall: `sudo ufw allow 5555`

### Motor Keeps Spinning
The system includes automatic motor shutdown on disconnect. If it fails:
```bash
# Manually stop
killall ultra_simple
```

## Documentation

- **[System Requirements Specification](docs/BlackDog_SRS_v2.pdf)** - Detailed requirements
- **[GitHub Wiki](https://github.com/rylet23/BlackDog_Enforcer/wiki)** - Setup guides and tutorials
- **[Meeting Notes](docs/meetings/)** - Team meeting summaries

## Contributing

This is an academic project, but we welcome feedback and suggestions!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

## Academic Integrity

This project is submitted as part of our senior capstone requirement at Embry-Riddle Aeronautical University. Please respect academic integrity policies if referencing this work.

## License

This project is developed for educational purposes as part of the ERAU Senior Design program.

## Acknowledgments

- **Dr. Towhidnejad** - Faculty advisor and project sponsor
- **Casey Elder** - Teaching assistant
- **SLAMTEC** - RPLidar SDK and documentation
- **Stereolabs** - ZED camera support
- **ERAU Facilities** - Testing location access

## Contact

For questions about this project, please contact the team through GitHub issues or reach out to:
- Project Lead: [@rylet23](https://github.com/rylet23)
- Software Lead: [@Cturner-24](https://github.com/Cturner-24)
- Hardware Lead: Colin Becker []
- Project Manager: Robert Chaney []

---

**Project Status:** Active Development (Spring 2026)  
**Last Updated:** February 2026
