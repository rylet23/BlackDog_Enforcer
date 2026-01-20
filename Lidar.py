"""
RPLidar A2M8 Server for Raspberry Pi 5
Reads from RPLidar and broadcasts data to connected clients
"""
import socket
import threading
import json
import time
from rplidar import RPLidar


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

        elif command == 'get_info':
            return self.get_lidar_info()

        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    def get_lidar_info(self):
        """Get RPLidar device information"""
        if self.lidar:
            try:
                info = self.lidar.get_info()
                health = self.lidar.get_health()
                return {
                    "status": "success",
                    "info": info,
                    "health": health,
                    "scanning": self.scanning
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "Lidar not connected"}

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
            self.lidar.stop_motor()
        print("LIDAR scanning stopped")

    def scan_loop(self):
        """Continuously read and broadcast LIDAR data"""
        try:
            # Start the motor and scanning
            self.lidar.start_motor()
            time.sleep(2)  # Give motor time to spin up

            for scan in self.lidar.iter_scans():
                if not self.scanning:
                    break

                # Process each scan (360 degree sweep)
                scan_data = []
                for point in scan:
                    quality, angle, distance = point
                    scan_data.append({
                        "quality": quality,
                        "angle": round(angle, 2),
                        "distance": round(distance / 1000, 3)  # Convert mm to meters
                    })

                # Broadcast scan to all clients
                message = {
                    "type": "lidar_scan",
                    "timestamp": time.time(),
                    "points": scan_data,
                    "num_points": len(scan_data)
                }
                self.broadcast(message)

        except Exception as e:
            print(f"Scan error: {e}")
            self.scanning = False
        finally:
            if self.lidar:
                self.lidar.stop()
                self.lidar.stop_motor()

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
            self.lidar = RPLidar(self.lidar_port)

            # Get device info
            info = self.lidar.get_info()
            print(f"RPLidar connected: {info}")

            health = self.lidar.get_health()
            print(f"RPLidar health: {health}")

        except Exception as e:
            print(f"Failed to connect to RPLidar: {e}")
            print("Make sure:")
            print("  1. RPLidar is connected via USB")
            print("  2. You have permissions: sudo chmod 666 /dev/ttyUSB0")
            print("  3. rplidar library is installed: pip install rplidar")
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
                self.lidar.stop()
                self.lidar.stop_motor()
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