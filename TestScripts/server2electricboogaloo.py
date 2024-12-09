import socket
import threading
import signal
import sys
import time

# Server settings
INADDR_ANY = socket.gethostbyname(socket.gethostname())
VIDEO_PORT = 8888
AUDIO_PORT = 9999
FORMAT = "utf-8"

# Video server socket
video_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server_socket.bind((INADDR_ANY, VIDEO_PORT))

# Audio server socket
audio_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
audio_server_socket.bind((INADDR_ANY, AUDIO_PORT))

# Flag to control the server loop
server_running = True

# Lists to track connected clients
video_clients = []
audio_clients = set()  # Use a set to track unique UDP clients


def handle_video(client_socket, cli_addr):
    """Handle video streaming for a single client."""
    print(f"[VIDEO CONNECTION] {cli_addr} connected.")
    while server_running:
        try:
            data = client_socket.recv(4096)
            if not data:
                print(f"[{cli_addr}] Video client disconnected.")
                break

            # Relay video data to other connected clients
            for c in video_clients:
                if c != client_socket:
                    try:
                        c.sendall(data)
                    except Exception as e:
                        print(f"Error sending video data to {c}: {e}")
                        video_clients.remove(c)
        except ConnectionError as e:
            print(f"[{cli_addr}] Video connection error: {e}")
            break
        except Exception as e:
            print(f"[{cli_addr}] Unexpected error: {e}")
            break

    # Cleanup
    client_socket.close()
    if client_socket in video_clients:
        video_clients.remove(client_socket)
    print(f"[VIDEO DISCONNECTED] {cli_addr} disconnected.")


def handle_audio():
    """Relay audio data between clients while ensuring connection remains alive."""
    print("[AUDIO SERVER STARTED]")
    while server_running:
        try:
            # Receive audio data from any client
            audio_data, client_address = audio_server_socket.recvfrom(4096)

            # Handle empty packets
            if not audio_data:
                print(f"[WARNING] Empty audio packet received from {client_address}")
                continue

            # Log debug information
            print(f"[DEBUG] Received audio data from {client_address}")

            # Add new audio clients dynamically
            if client_address not in audio_clients:
                print(f"New audio client connected: {client_address}")
                audio_clients.add(client_address)

            # Send audio to all other clients except the sender
            for addr in list(audio_clients):  # Copying list to handle dynamic updates
                if addr != client_address:  # Avoid sending back to the sender
                    try:
                        audio_server_socket.sendto(audio_data, addr)
                    except Exception as e:
                        print(f"Error sending audio to {addr}: {e}")
                        audio_clients.discard(addr)  # Remove failed client
        except Exception as e:
            print(f"Error in audio relay loop: {e}")



def start_video_server():
    """Start the video server."""
    global server_running
    video_server_socket.listen(5)
    print(f"[VIDEO LISTENING] Server is listening on {INADDR_ANY}:{VIDEO_PORT}")
    while server_running:
        try:
            video_server_socket.settimeout(1.0)  # Timeout to check server_running
            client_socket, cli_addr = video_server_socket.accept()
            video_clients.append(client_socket)
            thread = threading.Thread(target=handle_video, args=(client_socket, cli_addr))
            thread.start()
            print(f"[ACTIVE VIDEO CONNECTIONS] {threading.active_count() - 1}")
        except socket.timeout:
            continue


def stop_server(signal, frame):
    """Handle Ctrl+C signal to stop the server."""
    global server_running
    print("\n[SHUTTING DOWN] Server is stopping...")
    server_running = False

    # Close all video client sockets
    for client in video_clients:
        try:
            client.close()
        except Exception as e:
            print(f"Error closing video client socket: {e}")

    # Close audio server socket
    try:
        audio_server_socket.close()
    except Exception as e:
        print(f"Error closing audio server socket: {e}")

    # Close video server socket
    try:
        video_server_socket.close()
    except Exception as e:
        print(f"Error closing video server socket: {e}")

    print("[SERVER STOPPED]")
    sys.exit(0)


# Attach signal handler for graceful shutdown
signal.signal(signal.SIGINT, stop_server)

# Start the server
print(f"Server running on {INADDR_ANY}, hostname: {socket.gethostname()}")
print("[STARTING] Server is starting...")

# Launch video and audio servers in separate threads
video_thread = threading.Thread(target=start_video_server, daemon=True)
audio_thread = threading.Thread(target=handle_audio, daemon=True)

video_thread.start()
audio_thread.start()

# Keep the main thread alive
try:
    while server_running:
        time.sleep(0.1)
except KeyboardInterrupt:
    stop_server(None, None)
