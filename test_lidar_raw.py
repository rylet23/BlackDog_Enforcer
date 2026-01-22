import serial
import time
import struct

LIDAR_ANGLE_MIN = 0
LIDAR_ANGLE_MAX = 360
LIDAR_DISTANCE_THRESHOLD_HIGH = 300
LIDAR_DISTANCE_THRESHOLD_LOW = 100

# RPLidar A2M8 Protocol Commands
RPLIDAR_CMD_STOP = b'\xA5\x25'
RPLIDAR_CMD_RESET = b'\xA5\x40'
RPLIDAR_CMD_SCAN = b'\xA5\x20'
RPLIDAR_CMD_FORCE_SCAN = b'\xA5\x21'
RPLIDAR_CMD_GET_INFO = b'\xA5\x50'
RPLIDAR_CMD_GET_HEALTH = b'\xA5\x52'


# Motor control for A2M8
def set_motor_pwm(ser, pwm_value):
    """Set motor PWM (0-1023, default 660)"""
    pwm_lsb = pwm_value & 0xFF
    pwm_msb = (pwm_value >> 8) & 0xFF
    checksum = (0xA5 + 0xF0 + 0x02 + pwm_lsb + pwm_msb) & 0xFF
    cmd = bytes([0xA5, 0xF0, 0x02, pwm_lsb, pwm_msb, checksum])
    ser.write(cmd)
    print(f"Motor PWM set to {pwm_value}")


def parse_scan_data(raw_bytes):
    """Parse A2M8 scan data packet (5 bytes per measurement)"""
    if len(raw_bytes) < 5:
        return None

    # Check start flag
    start_flag = (raw_bytes[0] & 0x01) == 1 and (raw_bytes[0] & 0x02) == 0

    # Parse angle (14 bits)
    angle_q6 = ((raw_bytes[1] >> 1) << 8) | raw_bytes[2]
    angle = angle_q6 / 64.0

    # Parse distance (16 bits)
    distance_q2 = raw_bytes[3] | (raw_bytes[4] << 8)
    distance = distance_q2 / 4.0

    # Quality from first byte
    quality = raw_bytes[0] >> 2

    return {
        'start_flag': start_flag,
        'angle': angle,
        'distance': distance,
        'quality': quality
    }


def simple_scan():
    port = '/dev/ttyUSB0'  # Adjust for your system
    baudrate = 115200  # Try 115200 first, then 256000 if needed

    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port} at {baudrate} baud")
        time.sleep(0.5)

        # Stop any existing operation
        print("Stopping any existing scans...")
        ser.write(RPLIDAR_CMD_STOP)
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Reset device
        print("Resetting device...")
        ser.write(RPLIDAR_CMD_RESET)
        time.sleep(2)
        ser.reset_input_buffer()

        # Start motor
        print("Starting motor...")
        set_motor_pwm(ser, 660)
        time.sleep(2)

        # Start scan
        print("Starting scan...")
        ser.write(RPLIDAR_CMD_SCAN)
        time.sleep(0.5)

        # Read and discard descriptor (7 bytes)
        descriptor = ser.read(7)
        print(f"Descriptor received: {descriptor.hex() if descriptor else 'None'}")

        # Read scan data
        print("\nReading scan data...")
        scan_count = 0
        valid_count = 0

        while scan_count < 360:  # One full rotation
            raw = ser.read(5)

            if len(raw) == 5:
                data = parse_scan_data(raw)

                if data:
                    if data['start_flag']:
                        print(f"\n--- NEW SCAN (total valid points: {valid_count}) ---")
                        valid_count = 0

                    angle = data['angle']
                    distance = data['distance']
                    quality = data['quality']

                    if (LIDAR_ANGLE_MIN <= angle < LIDAR_ANGLE_MAX and
                            LIDAR_DISTANCE_THRESHOLD_LOW <= distance <= LIDAR_DISTANCE_THRESHOLD_HIGH):
                        print(f"Quality: {quality:3d}, Angle: {angle:6.2f}°, Distance: {distance:7.2f}mm")
                        valid_count += 1

                    scan_count += 1

        print(f"\nScan complete! Processed {scan_count} measurements")

    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop scan and motor
        print("\nStopping...")
        try:
            ser.write(RPLIDAR_CMD_STOP)
            time.sleep(0.5)
            set_motor_pwm(ser, 0)
            time.sleep(0.5)
            ser.close()
            print("Disconnected")
        except:
            pass


if __name__ == "__main__":
    simple_scan()