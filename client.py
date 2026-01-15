import socket
import threading
import json
import time
from collections import deque


class LidarClient:
    def __init__(self, server_host, server_port=50007):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.data_buffer = deque(maxlen=1000)  # Keep last 1000 readings
        self.data_callback = None

    def connect(self):
        """Connect to the LIDAR server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            print(f"Connected to LIDAR server at {self.server_host}:{self.server_port}")

            # Start listening thread
            listen_thread = threading.Thread(target=self.listen_for_data)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def listen_for_data(self):
        """Continuously listen for LIDAR data from server"""
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    print("Server disconnected")
                    self.connected = False
                    break

                buffer += data

                # Handle multiple JSON objects in buffer
                while True:
                    try:
                        # Try to parse JSON
                        message, idx = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[idx:].lstrip()

                        # Process the LIDAR data
                        self.process_lidar_data(message)

                    except json.JSONDecodeError:
                        # Incomplete JSON, wait for more data
                        break

            except Exception as e:
                print(f"Error receiving data: {e}")
                self.connected = False
                break

    def process_lidar_data(self, data):
        """Process incoming LIDAR data in real-time"""
        # Add to buffer for history
        self.data_buffer.append(data)

        # If a callback is registered, call it
        if self.data_callback:
            self.data_callback(data)
        else:
            # Default processing
            print(f"LIDAR Data: {data}")

    def register_callback(self, callback_function):
        """Register a function to process each data point as it arrives"""
        self.data_callback = callback_function

    def get_latest_data(self):
        """Get the most recent LIDAR reading"""
        if self.data_buffer:
            return self.data_buffer[-1]
        return None

    def get_data_history(self, n=100):
        """Get last n readings"""
        return list(self.data_buffer)[-n:]

    def send_command(self, command):
        """Send a command to the LIDAR server"""
        if not self.connected:
            print("Not connected to server")
            return False

        try:
            data = json.dumps(command).encode('utf-8')
            self.socket.send(data)
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        if self.socket:
            self.socket.close()
        print("Disconnected from LIDAR server")


# Example usage with real-time processing
def process_lidar_point(data):
    """Your custom processing function"""
    # Extract LIDAR data
    if 'distance' in data and 'angle' in data:
        distance = data['distance']
        angle = data['angle']

        # Do real-time processing here
        print(f"Processing: Distance={distance}m, Angle={angle}°")

        # Example: detect obstacles
        if distance < 1.0:  # Less than 1 meter
            print(f"OBSTACLE DETECTED at {angle}°!")

        # You can update visualization, send to robot controller, etc.


if __name__ == "__main__":
    # Connect to LIDAR (Raspberry Pi)
    client = LidarClient(server_host='10.33.253.244', server_port=50007)

    if client.connect():
        # Register your processing function
        client.register_callback(process_lidar_point)

        # Send a command to start scanning
        client.send_command({"command": "start_scan", "rate": 10})

        # Keep running
        try:
            while client.connected:
                time.sleep(0.1)

                # You can also pull data manually
                latest = client.get_latest_data()
                # Do something with latest data

        except KeyboardInterrupt:
            print("\nShutting down client...")
            client.disconnect()