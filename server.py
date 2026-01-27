import socket
import sys
import signal
import os

# Configuration
SERVER_HOST = '0.0.0.0'  # Listen on all interfaces
SERVER_PORT = 5555
BUFFER_SIZE = 4096


def stop_ultra_simple():
    """Send interrupt to parent process (ultra_simple) to stop motor"""
    try:
        # Get parent process ID (ultra_simple)
        ppid = os.getppid()
        print(f"\nSending stop signal to ultra_simple (PID {ppid})...", file=sys.stderr)
        os.kill(ppid, signal.SIGINT)
    except Exception as e:
        print(f"Could not stop ultra_simple: {e}", file=sys.stderr)


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

    client_socket = None
    try:
        client_socket, client_address = server_socket.accept()
        print(f"Client connected from {client_address}", file=sys.stderr)

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
        if client_socket:
            client_socket.close()
        server_socket.close()
        print("Server closed", file=sys.stderr)
        # Stop the motor when server exits for any reason
        stop_ultra_simple()


if __name__ == "__main__":
    run_server()