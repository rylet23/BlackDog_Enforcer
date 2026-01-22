# # test_motor.py
# import serial
# import time
#
# port = '/dev/ttyUSB0'
# baudrate = 115200
#
# ser = serial.Serial(port, baudrate, timeout=1)
# print(f"Connected to {port}")
#
# # Send motor start command with PWM
# # For A2M8, we need to send a specific motor control command
# print("Sending motor start command...")
#
# # Stop first
# ser.write(bytes([0xA5, 0x25]))  # STOP
# time.sleep(0.5)
# ser.reset_input_buffer()
#
# # Reset device
# print("Resetting device...")
# ser.write(bytes([0xA5, 0x40]))  # RESET
# time.sleep(2)
#
# # Set motor PWM (A2M8 specific - send PWM value)
# # Format: [0xA5, 0xF0, 0x02, PWM_LSB, PWM_MSB, Checksum]
# # Default PWM: 660 (0x0294)
# print("Setting motor PWM...")
# pwm_value = 660
# pwm_lsb = pwm_value & 0xFF
# pwm_msb = (pwm_value >> 8) & 0xFF
# checksum = (0xA5 + 0xF0 + 0x02 + pwm_lsb + pwm_msb) & 0xFF
#
# motor_cmd = bytes([0xA5, 0xF0, 0x02, pwm_lsb, pwm_msb, checksum])
# ser.write(motor_cmd)
# time.sleep(1)
#
# print("Motor should be spinning now - do you hear/see it?")
# input("Press Enter to continue...")
#
# # Start scan
# print("Starting scan...")
# ser.write(bytes([0xA5, 0x20]))  # SCAN
# time.sleep(0.5)
#
# # Read descriptor
# descriptor = ser.read(7)
# print(f"Descriptor: {descriptor.hex() if descriptor else 'None'}")
#
# # Read data
# print("\nReading data points...")
# for i in range(30):
#     raw = ser.read(5)
#     if len(raw) == 5:
#         start_flag = ((raw[0] & 0x01) == 1) and ((raw[0] & 0x02) == 0)
#         angle_raw = ((raw[1] & 0x0F) << 8) | raw[2]
#         angle = angle_raw / 64.0
#         distance_raw = raw[3] | (raw[4] << 8)
#         distance = distance_raw / 4.0
#
#         if start_flag:
#             print("--- NEW SCAN ---")
#         if distance > 0:
#             print(f"{angle:.1f}° = {distance:.1f}mm")
#
# # Stop motor
# print("\nStopping motor...")
# ser.write(bytes([0xA5, 0x25]))  # STOP
# time.sleep(0.5)
#
# # Set PWM to 0 to stop motor
# motor_cmd = bytes([0xA5, 0xF0, 0x02, 0x00, 0x00, 0x97])
# ser.write(motor_cmd)
#
# ser.close()
# print("Done!")

from pyrplidar import PyRPlidar
import time
LIDAR_ANGLE_MIN = 0
LIDAR_ANGLE_MAX = 360
LIDAR_DISTANCE_THRESHOLD_HIGH = 300
LIDAR_DISTANCE_THRESHOLD_LOW = 100

def simple_scan():
    lidar = PyRPlidar()
    lidar.connect(port="/dev/ttyUSB0", baudrate = 256000, timeout = 3)
    lidar.set_motor_pwm(500)
    time.sleep(2)

    scan_generator = lidar.force_scan()
    try:
        for scan in scan_generator:
            angle = scan.angle
            distance = scan.distance
            #if LIDAR_ANGLE_MIN <= angle < LIDAR_ANGLE_MAX and LIDAR_DISTANCE_THRESHOLD_LOW <= distance <= LIDAR_DISTANCE_THRESHOLD_HIGH:
            print(f"Angle: {angle}, Distance: {distance}")

    except KeyboardInterrupt:
            print("Scan Interrupted. Stopping LIDAR...")
    finally:
        lidar.stop()
        lidar.set_motor_pwm(0)
        lidar.disconnect()

if __name__ == "__main__":
    simple_scan()

