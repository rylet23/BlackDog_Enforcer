#This is the Robot
import socket

HOST = '10.33.237.62' #Blackdog1
PORT = 50007 #update later to best option

import socket
import threading
import json
import time


class BidirectionalClient:
    def __init__(self, server_host, server_port=50007):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False

    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            print(f"Connected to server at {self.server_host}:{self.server_port}")

            # Start listening thread
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def listen_for_messages(self):
        """Continuously listen for messages from server"""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    print("Server disconnected")
                    self.connected = False
                    break

                try:
                    message = json.loads(data)
                    self.handle_message(message)
                except json.JSONDecodeError:
                    print(f"Received invalid JSON: {data}")

            except Exception as e:
                print(f"Error receiving message: {e}")
                self.connected = False
                break

    def handle_message(self, message):
        """Handle incoming messages from server"""
        print(f"Received from server: {message}")
        # Add your custom message handling logic here

    def send_message(self, message):
        """Send a message to the server"""
        if not self.connected:
            print("Not connected to server")
            return False

        try:
            data = json.dumps(message).encode('utf-8')
            self.socket.send(data)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        if self.socket:
            self.socket.close()
        print("Disconnected from server")


# Example usage
if __name__ == "__main__":
    # Replace with your Raspberry Pi's IP address
    client = BidirectionalClient(server_host='10.33.237.62', server_port=50007)

    if client.connect():
        # Send some example messages
        client.send_message({"type": "greeting", "data": "Hello from client!"})
        time.sleep(1)

        client.send_message({"type": "sensor_data", "temperature": 25.5, "humidity": 60})
        time.sleep(1)

        # Keep running to receive messages
        try:
            while client.connected:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down client...")
            client.disconnect()



