import socket
import threading
import signal
import sys

# Server settings
INADDR_ANY = socket.gethostbyname(socket.gethostname())
VIDEO_PORT = 8888  # Port for video (TCP)
AUDIO_PORT = 8889  # Port for audio (UDP)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"

# Create TCP socket for video
video_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server.bind((INADDR_ANY, VIDEO_PORT))

# Create UDP socket for audio
audio_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
audio_server.bind((INADDR_ANY, AUDIO_PORT))

# Flags to control the server loop
server_running = True

# Clients list for TCP connections
clients = []

def handle_video_client(client_socket, cli_addr):
    """Handle video data from a TCP client."""
    print(f"[NEW VIDEO CONNECTION] {cli_addr} connected.")
    while server_running:
        try:
            data = client_socket.recv(4096)
            if not data:
                print(f"[{cli_addr}] Video client disconnected.")
                break

            print(f"Received video data from {cli_addr}, size: {len(data)} bytes")

            # Relay video data to other clients
            for c in clients:
                if c != client_socket:
                    try:
                        c.sendall(data)
                        print(f"Relayed video data to another client.")
                    except Exception as e:
                        print(f"Error sending video data to a client: {e}")
                        clients.remove(c)
        except ConnectionError as e:
            print(f"[{cli_addr}] Video connection error: {e}")
            break
        except Exception as e:
            print(f"[{cli_addr}] Unexpected video error: {e}")
            break

    # Cleanup
    client_socket.close()
    if client_socket in clients:
        clients.remove(client_socket)
    print(f"[VIDEO DISCONNECTED] {cli_addr} disconnected.")

def handle_audio():
    """Handle audio data from UDP clients."""
    print("[AUDIO SERVER STARTED]")
    while server_running:
        try:
            # Receive audio data and relay it to all clients
            audio_data, addr = audio_server.recvfrom(4096)
            print(f"Received audio packet from {addr}, size: {len(audio_data)} bytes")

            # Relay audio data to all connected clients
            for client in clients:
                try:
                    client.sendall(audio_data)
                    print(f"Relayed audio data to a client.")
                except Exception as e:
                    print(f"Error relaying audio data to a client: {e}")
                    clients.remove(client)
        except Exception as e:
            if server_running:  # Ignore errors during shutdown
                print(f"Error in audio handling: {e}")

def start_video_server():
    """Start the TCP video server."""
    video_server.listen(5)
    print(f"[LISTENING] Video server is listening on {INADDR_ANY}:{VIDEO_PORT}")
    while server_running:
        try:
            video_server.settimeout(1.0)  # Set a timeout to avoid blocking indefinitely
            client_socket, cli_addr = video_server.accept()
            print(f"Video client connected from {cli_addr}")
            clients.append(client_socket)
            thread = threading.Thread(target=handle_video_client, args=(client_socket, cli_addr))
            thread.start()
            print(f"[ACTIVE VIDEO CONNECTIONS] {threading.active_count() - 2}")  # Exclude audio thread and main thread
        except socket.timeout:
            continue  # Timeout allows checking the server_running flag
        except Exception as e:
            print(f"Error accepting video connection: {e}")

def stop_server(signal, frame):
    """Handle Ctrl+C signal to stop the server."""
    global server_running
    print("\n[SHUTTING DOWN] Server is stopping...")
    server_running = False

    # Close all client sockets
    for client in clients:
        try:
            client.close()
        except Exception as e:
            print(f"Error closing client socket: {e}")

    # Close the servers
    video_server.close()
    audio_server.close()
    print("[SERVER STOPPED]")
    sys.exit(0)

# Attach signal handler for graceful shutdown
signal.signal(signal.SIGINT, stop_server)

print("Server:", INADDR_ANY, "Name:", socket.gethostname())
print("[STARTING] server is starting...")

# Start server threads
video_thread = threading.Thread(target=start_video_server, daemon=True)
audio_thread = threading.Thread(target=handle_audio, daemon=True)

video_thread.start()
audio_thread.start()

# Keep the main thread running
try:
    while server_running:
        time.sleep(0.1)
except KeyboardInterrupt:
    stop_server(None, None)

