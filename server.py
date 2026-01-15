#This is the LIDAR
import socket
import threading
import json

#HOST = '155.31.68.208' #Blackdog2

class server:
    def __init__(self, host= '155.31.68.208', port= 50007):
        self.host = host
        self.port = port
        self.clients = []
        self.serversocket = None

    def handle_client(self, client_socket, address):
        """Handle Individual Client Connections"""
        print(f"New Connection From {address}")
        self.clients.append(client_socket)
        try:
            while True:
                #Recieve Data from Client
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                print(f"Recieved from {address}: {data}")

                #Parse JSON Data
                try:
                    message = json.loads(data)
                    #process the message and create the response
                    response = self.process_message(message)

                    #send response back
                    client_socket.send(json.dumps(response).encode('utf-8'))
                except json.JSONDecodeError:
                    client_socket.send("Invalid JSON".encode('utf-8'))

        except Exception as e:
            print(f"Error with {address}: {e}")
        finally:
            self.clients.remove(client_socket)
            client_socket.close()
            print(f"Connection closed: {address}")

        def broadcast(self, message):
            """Send message to all connected clients"""
            data = json.dumps(message).encode('utf-8')
            for client in self.clients:
                try:
                    client.send(data)
                except:
                    self.clients.remove(client)

        def start(self):
            """Start the server"""
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
                self.server_socket.close()

    if __name__ == "__main__":
        server = server(host='0.0.0.0', port=5000)
        server.start()




