from pyrplidar import PyRPlidar
import time

LIDAR_ANGLE_MIN = 0
LIDAR_ANGLE_MAX = 360
LIDAR_DISTANCE_THRESHOLD_HIGH = 300
LIDAR_DISTANCE_THRESHOLD_LOW = 100


def simple_scan():
    lidar = PyRPlidar()

    try:
        lidar.connect(port="/dev/ttyUSB0", baudrate=256000, timeout=3)
        # Linux:"dev/ttyUSB0"
        # MacOS: "/dev/cu.usbserial-0001"
        # Windows: "COM5"
        print("Successfully connected to LIDAR")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    try:
        # Stop any existing scan first
        print("Stopping any existing operations...")
        try:
            lidar.stop()
        except:
            pass
        time.sleep(0.5)

        # Reset the device
        print("Resetting device...")
        try:
            lidar.reset()
        except:
            pass
        time.sleep(2)

        # Start motor
        print("Starting motor...")
        lidar.set_motor_pwm(660)
        time.sleep(3)

        print("Starting scan...")
        scan_generator = lidar.start_scan_express(2)

        scan_count = 0
        for count, scan in enumerate(scan_generator):
            try:
                print(f"Raw scan data: {scan}, type: {type(scan)}")

                if isinstance(scan, (list, tuple)) and len(scan) >= 3:
                    quality, angle, distance = scan[0], scan[1], scan[2]
                    print(f"Angle: {angle:.2f}°, Distance: {distance:.2f}mm, Quality: {quality}")
                elif hasattr(scan, 'angle'):
                    print(f"Angle: {scan.angle:.2f}°, Distance: {scan.distance:.2f}mm")
                else:
                    print(f"Unknown scan format: {scan}")

                if count > 20:
                    break

            except Exception as e:
                print(f"Error: {e}, scan={scan}")
                import traceback
                traceback.print_exc()
                continue

    except KeyboardInterrupt:
        print("\nScan Interrupted. Stopping LIDAR...")
    except Exception as e:
        print(f"Error during scanning: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            lidar.stop()
            lidar.set_motor_pwm(0)
            time.sleep(0.5)
            lidar.disconnect()
            print("LIDAR stopped and disconnected")
        except Exception as e:
            print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    simple_scan()
