import socket
import sys

# Configuration
SERVER_IP = '10.33.239.139'  # Replace with Pi 5's IP address
SERVER_PORT = 5555
BUFFER_SIZE = 4096


def run_client():
    """
    Simple socket client that receives data and prints to stdout.
    Usage: python3 lidar_client.py | python3 your_processing_program.py
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"Connecting to {SERVER_IP}:{SERVER_PORT}...", file=sys.stderr)
        client_socket.connect((SERVER_IP, SERVER_PORT))
        print("Connected to lidar server!", file=sys.stderr)

        while True:
            # Receive data
            data = client_socket.recv(BUFFER_SIZE)

            if not data:
                print("Connection closed by server", file=sys.stderr)
                break

            # Write to stdout (can be piped to another program)
            sys.stdout.write(data.decode())
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nShutting down client...", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        client_socket.close()
        print("Disconnected", file=sys.stderr)


if __name__ == "__main__":
    run_client()