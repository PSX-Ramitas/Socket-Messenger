import socket
import threading
import signal
import sys

# Server settings
INADDR_ANY = socket.gethostbyname(socket.gethostname())
PORT = 8888
serv_addr = (INADDR_ANY, PORT)
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"

# Create a socket and bind it to the address
server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.bind(serv_addr)

# Flag to control the server loop
server_running = True

clients = []

def handle_client(client_socket, cli_addr):
    print(f"[NEW CONNECTION] {cli_addr} connected.")
    while server_running:
        try:
            data = client_socket.recv(4096)
            if not data:
                print(f"[{cli_addr}] Client disconnected.")
                break

            # Debug: Print size of received data
            print(f"Received data from {cli_addr}, size: {len(data)} bytes")

            # Relay data to other clients
            for c in clients:
                if c != client_socket:
                    try:
                        c.sendall(data)
                        # Debug: Confirm data relayed
                        print(f"Relayed data to another client.")
                    except Exception as e:
                        print(f"Error sending data to a client: {e}")
                        clients.remove(c)
        except ConnectionError as e:
            print(f"[{cli_addr}] Connection error: {e}")
            break
        except Exception as e:
            print(f"[{cli_addr}] Unexpected error: {e}")
            break

    # Cleanup
    client_socket.close()
    clients.remove(client_socket)
    print(f"[DISCONNECTED] {cli_addr} disconnected.")

def start_server():
    """Start the server."""
    global server_running
    server.listen(5)
    print(f"[LISTENING] Server is listening on {INADDR_ANY}")
    while server_running:
        try:
            server.settimeout(1.0)  # Set a timeout to avoid blocking indefinitely
            client_socket, cli_addr = server.accept()
            print(f"Client connected from {cli_addr}")
            clients.append(client_socket)
            thread = threading.Thread(target=handle_client, args=(client_socket, cli_addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() -1}")
        except socket.timeout:
            continue  # Timeout allows checking the server_running flag

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

    server.close()
    print("[SERVER STOPPED]")
    sys.exit(0)

# Attach signal handler for graceful shutdown
signal.signal(signal.SIGINT, stop_server)

print("Server:", INADDR_ANY," Name:", socket.gethostname())
print("[STARTING] server is starting...")
start_server()
