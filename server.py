import socket
import threading

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


def handle_video(client_socket):
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            # Broadcast video
            for c in video_clients:
                if c != client_socket:
                    c.sendall(data)
        except Exception:
            break

    client_socket.close()
    video_clients.remove(client_socket)


def handle_chat(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode("utf-8")
            if not message:
                break
            # Broadcast chat messages
            for c in chat_clients:
                if c != client_socket:
                    c.sendall(message.encode("utf-8"))
        except Exception:
            break

    client_socket.close()
    chat_clients.remove(client_socket)


def start_video_server():
    while True:
        client_socket, _ = video_server_socket.accept()
        video_clients.append(client_socket)
        threading.Thread(target=handle_video, args=(client_socket,), daemon=True).start()


def start_chat_server():
    while True:
        client_socket, _ = chat_server_socket.accept()
        chat_clients.append(client_socket)
        threading.Thread(target=handle_chat, args=(client_socket,), daemon=True).start()


if __name__ == "__main__":
    threading.Thread(target=start_video_server, daemon=True).start()
    threading.Thread(target=start_chat_server, daemon=True).start()

    print(f"Server is running on ports {VIDEO_PORT} (video) and {CHAT_PORT} (chat).")
    threading.Event().wait()  # Keep main thread alive
