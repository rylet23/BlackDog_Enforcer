# #This is the LIDAR
# import socket
# import threading
# import json
#
# class server:
#     def __init__(self, host='10.33.239.139', port=50007):
#         self.host = host
#         self.port = port
#         self.clients = []
#         self.server_socket = None
#
#     def handle_client(self, client_socket, address):
#         """Handle Individual Client Connections"""
#         print(f"New Connection From {address}")
#         self.clients.append(client_socket)
#         try:
#             while True:
#                 #Receive Data from Client
#                 data = client_socket.recv(1024).decode('utf-8')
#                 if not data:
#                     break
#
#                 print(f"Received from {address}: {data}")
#
#                 #Parse JSON Data
#                 try:
#                     message = json.loads(data)
#                     #process the message and create the response
#                     response = self.process_message(message)
#
#                     #send response back
#                     client_socket.send(json.dumps(response).encode('utf-8'))
#                 except json.JSONDecodeError:
#                     client_socket.send(b'{"error": "Invalid JSON"}')
#
#         except Exception as e:
#             print(f"Error with {address}: {e}")
#         finally:
#             self.clients.remove(client_socket)
#             client_socket.close()
#             print(f"Connection closed: {address}")
#
#     def process_message(self, message):
#         """Process received message and generate response"""
#         # Add your custom logic here
#         return {
#             "status": "received",
#             "echo": message,
#             "response": "Message processed successfully"
#         }
#
#     def broadcast(self, message):
#         """Send message to all connected clients"""
#         data = json.dumps(message).encode('utf-8')
#         for client in self.clients:
#             try:
#                 client.send(data)
#             except:
#                 self.clients.remove(client)
#
#     def start(self):
#         """Start the server"""
#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         self.server_socket.bind((self.host, self.port))
#         self.server_socket.listen(5)
#
#         print(f"Server listening on {self.host}:{self.port}")
#
#         try:
#             while True:
#                 client_socket, address = self.server_socket.accept()
#                 client_thread = threading.Thread(
#                     target=self.handle_client,
#                     args=(client_socket, address)
#                 )
#                 client_thread.daemon = True
#                 client_thread.start()
#         except KeyboardInterrupt:
#             print("\nShutting down server...")
#         finally:
#             self.server_socket.close()
#
# if __name__ == "__main__":
#     srv = server(host='10.33.253.244', port=50007)
#     srv.start()

import socket
import sys

# Configuration
SERVER_HOST = '0.0.0.0'  # Listen on all interfaces
SERVER_PORT = 5555
BUFFER_SIZE = 4096


def run_server():
    """
    Simple socket server that forwards stdin to connected client.
    Usage: ./your_lidar_program | python3 lidar_server.py
    """
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(1)

    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}", file=sys.stderr)
    print("Waiting for client connection...", file=sys.stderr)

    client_socket, client_address = server_socket.accept()
    print(f"Client connected from {client_address}", file=sys.stderr)

    try:
        # Read from stdin and send to client
        for line in sys.stdin:
            try:
                client_socket.sendall(line.encode())
            except:
                print("Client disconnected", file=sys.stderr)
                break

    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
    finally:
        client_socket.close()
        server_socket.close()
        print("Server closed", file=sys.stderr)


if __name__ == "__main__":
    run_server()