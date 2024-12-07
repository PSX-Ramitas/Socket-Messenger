import socket
import threading

# Server settings
HOST = '192.168.1.68'
PORT = 8080

clients = []

def handle_client(client_socket):
    """Relay data between clients."""
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            # Forward data to all connected clients except sender
            for c in clients:
                if c != client_socket:
                    c.sendall(data)
        except ConnectionResetError:
            break
    client_socket.close()
    clients.remove(client_socket)

def start_server():
    """Start the server."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Server listening on {HOST}:{PORT}")
    while True:
        client_socket, addr = server.accept()
        print(f"Client connected from {addr}")
        clients.append(client_socket)
        threading.Thread(target=handle_client, args=(client_socket,)).start()

start_server()
