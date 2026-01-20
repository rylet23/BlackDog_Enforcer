# test_pyserial.py
import serial
import time
import struct

port = '/dev/ttyUSB0'
baudrate = 115200

# Connect
ser = serial.Serial(port, baudrate, timeout=1)
print(f"Connected to {port}")

# Stop any existing scan
ser.write(bytes([0xA5, 0x25]))  # STOP command
time.sleep(0.5)
ser.reset_input_buffer()

# Start scan
ser.write(bytes([0xA5, 0x20]))  # SCAN command
time.sleep(0.5)

# Read descriptor (7 bytes)
descriptor = ser.read(7)
print(f"Descriptor: {descriptor.hex()}")

# Read some data points
print("\nReading scan data:")
for i in range(20):
    raw = ser.read(5)
    if len(raw) == 5:
        # Parse
        start_flag = ((raw[0] & 0x01) == 1) and ((raw[0] & 0x02) == 0)
        angle_raw = ((raw[1] & 0x0F) << 8) | raw[2]
        angle = angle_raw / 64.0
        distance_raw = raw[3] | (raw[4] << 8)
        distance = distance_raw / 4.0

        if start_flag:
            print("--- NEW SCAN ---")
        print(f"Point {i}: {angle:.1f}° = {distance:.1f}mm")

# Stop
ser.write(bytes([0xA5, 0x25]))
ser.close()
print("\nDone!")