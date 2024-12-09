import socket
import threading
import signal
import sys

VIDEO_PORT = 8888
CHAT_PORT = 7777
MAX_CLIENTS = 8

video_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server_socket.bind(("", VIDEO_PORT))
video_server_socket.listen(MAX_CLIENTS)

chat_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
chat_server_socket.bind(("", CHAT_PORT))
chat_server_socket.listen(MAX_CLIENTS)

video_clients = []
chat_clients = []
server_running = True  # Global flag to control server state


def handle_video(client_socket):
    """Handle incoming video data and broadcast it to other connected clients."""
    while server_running:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            for c in video_clients:
                if c != client_socket:
                    c.sendall(data)
        except Exception:
            break

    client_socket.close()
    if client_socket in video_clients:
        video_clients.remove(client_socket)


def handle_chat(client_socket):
    """Handle chat message reception and broadcasting."""
    while server_running:
        try:
            message = client_socket.recv(1024).decode("utf-8")
            if not message:
                break
            for c in chat_clients:
                if c != client_socket:
                    c.sendall(message.encode("utf-8"))
        except Exception:
            break

    client_socket.close()
    if client_socket in chat_clients:
        chat_clients.remove(client_socket)


def start_video_server():
    """Accept and handle video connections."""
    while server_running:
        try:
            client_socket, _ = video_server_socket.accept()
            video_clients.append(client_socket)
            threading.Thread(target=handle_video, args=(client_socket,), daemon=True).start()
        except Exception:
            pass


def start_chat_server():
    """Accept and handle chat connections."""
    while server_running:
        try:
            client_socket, _ = chat_server_socket.accept()
            chat_clients.append(client_socket)
            threading.Thread(target=handle_chat, args=(client_socket,), daemon=True).start()
        except Exception:
            pass


def shutdown_server():
    """Shutdown server gracefully, closing all connections."""
    global server_running
    print("\nShutting down server...")
    server_running = False

    # Close all client sockets
    for c in video_clients:
        try:
            c.close()
        except Exception:
            pass
    for c in chat_clients:
        try:
            c.close()
        except Exception:
            pass

    # Close the server sockets
    try:
        video_server_socket.close()
        chat_server_socket.close()
    except Exception:
        pass

    print("All server sockets and connections have been closed.")
    sys.exit(0)


# Signal handling to capture `Ctrl+C`
signal.signal(signal.SIGINT, lambda signum, frame: shutdown_server())

if __name__ == "__main__":
    # Start video and chat servers in separate threads
    threading.Thread(target=start_video_server, daemon=True).start()
    threading.Thread(target=start_chat_server, daemon=True).start()

    print(f"Server is running on ports {VIDEO_PORT} (video) and {CHAT_PORT} (chat).")
    try:
        while server_running:  # Keep main thread alive
            threading.Event().wait(1)
    except KeyboardInterrupt:
        shutdown_server()
