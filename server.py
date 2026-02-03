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
        print("\nServer interrupted", file=sys.stderr)
    finally:
        client_socket.close()
        server_socket.close()
        print("Server closed", file=sys.stderr)


if __name__ == "__main__":
    run_server()