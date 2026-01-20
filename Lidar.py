"""
RPLidar A2M8 Server for Raspberry Pi 5
Reads from RPLidar using PySerial and broadcasts data to connected clients
"""
import socket
import threading
import json
import time
import serial
import struct

class RPLidarA2:
    """Direct interface to RPLidar A2M8 using PySerial"""

    # Command constants
    SYNC_BYTE = 0xA5
    GET_INFO = 0x50
    GET_HEALTH = 0x52
    STOP = 0x25
    RESET = 0x40
    SCAN = 0x20
    FORCE_SCAN = 0x21

    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect(self):
        """Connect to the RPLidar"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            time.sleep(0.1)
            print(f"Connected to RPLidar on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from RPLidar"""
        if self.serial and self.serial.is_open:
            self.stop()
            self.serial.close()

    def send_command(self, cmd, payload=None):
        """Send command to RPLidar"""
        if not self.serial or not self.serial.is_open:
            return False

        # Build command packet
        packet = bytes([self.SYNC_BYTE, cmd])

        if payload:
            packet += bytes(payload)

        self.serial.write(packet)
        return True

    def stop(self):
        """Stop scanning"""
        self.send_command(self.STOP)
        time.sleep(0.1)
        self.serial.reset_input_buffer()

    def reset(self):
        """Reset the device"""
        self.send_command(self.RESET)
        time.sleep(2)

    def start_scan(self):
        """Start scanning"""
        self.serial.reset_input_buffer()
        self.send_command(self.SCAN)
        time.sleep(0.1)

        # Read descriptor
        descriptor = self.serial.read(7)
        if len(descriptor) < 7:
            return False

        return True

    def read_scan_data(self):
        """Read one scan point - A2M8 uses 5-byte packets"""
        try:
            # Read 5 bytes per measurement
            raw = self.serial.read(5)
            if len(raw) < 5:
                return None

            # Parse A2M8 format
            # Byte 0: [S|!S|C|Quality[5:4]]
            # Byte 1: Quality[3:0]<<4 | Angle[12:8]
            # Byte 2: Angle[7:0]
            # Byte 3: Distance[7:0]
            # Byte 4: Distance[15:8]

            # Check start bit (bit 0) and inverse start bit (bit 1)
            start_flag = ((raw[0] & 0x01) == 1) and ((raw[0] & 0x02) == 0)

            # Check bit (bit 2)
            check_bit = (raw[0] & 0x04) >> 2

            # Quality (6 bits total)
            quality = ((raw[0] & 0xFC) >> 2)

            # Angle (13 bits, divide by 64 for degrees)
            angle_raw = ((raw[1] & 0x0F) << 8) | raw[2]
            angle = angle_raw / 64.0

            # Distance (16 bits, divide by 4 for mm)
            distance_raw = raw[3] | (raw[4] << 8)
            distance = distance_raw / 4.0

            return {
                'start': start_flag,
                'quality': quality,
                'angle': angle,
                'distance': distance,
                'check': check_bit
            }

        except Exception as e:
            print(f"Parse error: {e}")
            return None


class RPLidarServer:
    def __init__(self, lidar_port='/dev/ttyUSB0', host='10.33.253.244', port=50007):
        self.lidar_port = lidar_port
        self.host = host
        self.port = port
        self.clients = []
        self.server_socket = None
        self.lidar = None
        self.scanning = False

    def handle_client(self, client_socket, address):
        """Handle individual client connections"""
        print(f"New connection from {address}")
        self.clients.append(client_socket)

        try:
            while True:
                # Receive commands from client
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                print(f"Received from {address}: {data}")

                try:
                    message = json.loads(data)
                    response = self.process_command(message)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    client_socket.send(b'{"error": "Invalid JSON"}')

        except Exception as e:
            print(f"Error with {address}: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print(f"Connection closed: {address}")

    def process_command(self, message):
        """Process commands from clients"""
        command = message.get('command', '')

        if command == 'start_scan':
            if not self.scanning:
                self.start_lidar_scan()
                return {"status": "success", "message": "Scan started"}
            return {"status": "info", "message": "Already scanning"}

        elif command == 'stop_scan':
            if self.scanning:
                self.stop_lidar_scan()
                return {"status": "success", "message": "Scan stopped"}
            return {"status": "info", "message": "Not scanning"}

        elif command == 'status':
            return {
                "status": "success",
                "scanning": self.scanning,
                "connected": self.lidar is not None,
                "clients": len(self.clients)
            }

        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    def start_lidar_scan(self):
        """Start scanning with RPLidar"""
        if not self.lidar:
            return

        self.scanning = True
        scan_thread = threading.Thread(target=self.scan_loop)
        scan_thread.daemon = True
        scan_thread.start()
        print("LIDAR scanning started")

    def stop_lidar_scan(self):
        """Stop scanning"""
        self.scanning = False
        if self.lidar:
            self.lidar.stop()
        print("LIDAR scanning stopped")

    def scan_loop(self):
        """Continuously read and broadcast LIDAR data"""
        try:
            # Start scanning
            if not self.lidar.start_scan():
                print("Failed to start scan")
                self.scanning = False
                return

            scan_data = []

            while self.scanning:
                point = self.lidar.read_scan_data()

                if point:
                    scan_data.append({
                        "quality": point['quality'],
                        "angle": round(point['angle'], 2),
                        "distance": round(point['distance'] / 1000, 3)  # mm to meters
                    })

                    # When we complete a full rotation (start flag)
                    if point['start'] and len(scan_data) > 10:
                        # Broadcast complete scan
                        message = {
                            "type": "lidar_scan",
                            "timestamp": time.time(),
                            "points": scan_data,
                            "num_points": len(scan_data)
                        }
                        self.broadcast(message)
                        scan_data = []  # Start new scan

        except Exception as e:
            print(f"Scan error: {e}")
            self.scanning = False
        finally:
            if self.lidar:
                self.lidar.stop()

    def broadcast(self, message):
        """Send message to all connected clients"""
        data = json.dumps(message).encode('utf-8')
        disconnected = []

        for client in self.clients:
            try:
                client.send(data)
            except:
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            if client in self.clients:
                self.clients.remove(client)

    def start(self):
        """Start the server and connect to RPLidar"""
        # Connect to RPLidar
        try:
            print(f"Connecting to RPLidar on {self.lidar_port}...")
            self.lidar = RPLidarA2(self.lidar_port)

            if not self.lidar.connect():
                print("Failed to connect to RPLidar")
                print("Make sure:")
                print("  1. RPLidar is connected via USB")
                print("  2. You have permissions: sudo chmod 666 /dev/ttyUSB0")
                print("  3. pyserial is installed: pip3 install pyserial")
                return

            print("RPLidar connected successfully!")

        except Exception as e:
            print(f"Failed to connect to RPLidar: {e}")
            return

        # Start network server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        print(f"Server listening on {self.host}:{self.port}")

        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean shutdown"""
        self.scanning = False

        if self.lidar:
            try:
                self.lidar.disconnect()
            except:
                pass

        if self.server_socket:
            self.server_socket.close()

        print("Server shut down")

if __name__ == "__main__":
    server = RPLidarServer(
        lidar_port='/dev/ttyUSB0',  # May be /dev/ttyUSB1, check with: ls /dev/ttyUSB*
        host='10.33.253.244',
        port=50007
    )
    server.start()