import socket
import threading
import signal
import sys

# Server settings
INADDR_ANY = socket.gethostbyname(socket.gethostname())
PORT = 8888  # Port for video (TCP)
AUDIO_PORT = 9999  # Port for audio (UDP)
FORMAT = "utf-8"

# Video (TCP) socket
video_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server_socket.bind((INADDR_ANY, PORT))

# Audio (UDP) socket
audio_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
audio_server_socket.bind((INADDR_ANY, AUDIO_PORT))

# Server state
server_running = True
clients = []

def handle_video(client_socket, cli_addr):
    """Handle video relaying for a client."""
    print(f"[NEW VIDEO CONNECTION] {cli_addr} connected.")
    while server_running:
        try:
            data = client_socket.recv(4096)
            if not data:
                break

            # Relay data to other clients
            for c in clients:
                if c != client_socket:
                    c.sendall(data)
        except Exception as e:
            print(f"[{cli_addr}] Video error: {e}")
            break
    print(f"[DISCONNECTED] {cli_addr} video disconnected.")
    client_socket.close()
    clients.remove(client_socket)

def handle_audio():
    """Relay audio data between clients."""
    print("[AUDIO SERVER STARTED]")
    while server_running:
        try:
            audio_data, client_address = audio_server_socket.recvfrom(4096)
            for client in clients:
                if client.getpeername() != client_address:
                    audio_server_socket.sendto(audio_data, client.getpeername())
        except Exception as e:
            print(f"Audio handling error: {e}")

def stop_server(signal, frame):
    """Handle Ctrl+C signal to stop the server."""
    global server_running
    print("\n[SHUTTING DOWN] Server is stopping...")
    server_running = False
    for client in clients:
        client.close()
    video_server_socket.close()
    audio_server_socket.close()
    print("[SERVER STOPPED]")
    sys.exit(0)

# Attach signal handler
signal.signal(signal.SIGINT, stop_server)

print(f"[STARTING] Video server on {INADDR_ANY}:{PORT}")
print(f"[STARTING] Audio server on {INADDR_ANY}:{AUDIO_PORT}")

# Start audio thread
audio_thread = threading.Thread(target=handle_audio, daemon=True)
audio_thread.start()

# Start video server
video_server_socket.listen()
while server_running:
    try:
        client_socket, cli_addr = video_server_socket.accept()
        clients.append(client_socket)
        thread = threading.Thread(target=handle_video, args=(client_socket, cli_addr), daemon=True)
        thread.start()
    except Exception as e:
        print(f"Server error: {e}")
