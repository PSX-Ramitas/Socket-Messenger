import socket
import threading
import time

# Server constants
HOST = socket.gethostbyname(socket.gethostname())
PORT = 8080

# Keep track of roles and connected clients
rooms = {"main": []}  # Default room is "main"
instructor_connected = False
students = []
instructor_socket = None
lock = threading.Lock()  # Thread lock to synchronize shared state access
client_usernames = {}  # Dictionary to map client sockets to usernames
muted_clients = {}  # Dictionary to track muted clients and their mute durations
client_rooms = {}  # Dictionary to track client sockets and their room names


def broadcast_user_list():
    """Broadcast the list of connected users (with roles and room info) to all clients."""
    with lock:
        user_list = []
        for room, clients in rooms.items():
            for client in clients:
                role = "Instructor" if client == instructor_socket else "Student"
                username = client_usernames.get(client, "Unknown")
                user_list.append(f"{username} ({role}, Room: {room})")

        for client_socket in client_usernames.keys():
            user_list_str = ";".join(user_list)
            try:
                client_socket.send(f"USER_LIST|{user_list_str}".encode())
            except Exception as e:
                print(f"Error sending user list to client: {e}")


def broadcast_message(sender_socket, message):
    """Broadcast a message to all clients in the sender's room."""
    with lock:
        sender_room = next((room for room, clients in rooms.items() if sender_socket in clients), None)
        if sender_room:
            for client in rooms[sender_room]:
                if client != sender_socket:
                    try:
                        client.send(f"{client_usernames[sender_socket]}: {message}".encode())
                    except Exception as e:
                        print(f"Error sending message: {e}")


def handle_command(client_socket, command):
    """Handle instructor commands."""
    parts = command.split(" ", 2)
    cmd = parts[0]

    if cmd == "/whisper" and len(parts) > 2:
        recipient_name, whisper_msg = parts[1], parts[2]
        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            sender_room = client_rooms.get(client_socket, None)
            recipient_room = client_rooms.get(recipient_socket, None)
            # Check room restrictions
            if client_socket != instructor_socket and sender_room != recipient_room:
                client_socket.send("You can only whisper to users in your room.".encode())
            else:
                recipient_socket.send(f"[Whisper from {client_usernames[client_socket]}]: {whisper_msg}".encode())
        else:
            client_socket.send("User not found.".encode())

    elif cmd == "/kick" and client_socket == instructor_socket:
        recipient_name = parts[1]
        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            recipient_socket.send("You have been kicked out by the instructor.".encode())
            disconnect_client(recipient_socket)
            broadcast_message(client_socket, f"{recipient_name} has been kicked out.")
        else:
            client_socket.send("User not found.".encode())

    elif cmd == "/mute" and client_socket == instructor_socket:
        recipient_name = parts[1]
        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            duration = int(parts[2]) if len(parts) > 2 else 60  # Default mute duration to 60 seconds
            muted_clients[recipient_socket] = time.time() + duration
            client_socket.send(f"{recipient_name} has been muted for {duration} seconds.".encode())
            recipient_socket.send(f"You have been muted by the instructor for {duration} seconds.".encode())
        else:
            client_socket.send("User not found.".encode())

    elif cmd == "/create_room" and client_socket == instructor_socket:
        room_name = parts[1]
        if room_name not in rooms:
            rooms[room_name] = []
            client_socket.send(f"Room '{room_name}' created.".encode())
        else:
            client_socket.send("Room already exists.".encode())

    elif cmd == "/move_to_room" and client_socket == instructor_socket:
        recipient_name, room_name = parts[1], parts[2]
        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket and room_name in rooms:
            with lock:
                # Remove client from the current room
                for clients in rooms.values():
                    if recipient_socket in clients:
                        clients.remove(recipient_socket)
                        break
                
                # Add client to the new room
                rooms[room_name].append(recipient_socket)
                client_rooms[recipient_socket] = room_name  # Update the room tracking
                
            recipient_socket.send(f"You have been moved to room '{room_name}'.".encode())
            broadcast_user_list()
        else:
            client_socket.send("Invalid room name or user not found.".encode())


    elif cmd == "/call_back" and client_socket == instructor_socket:
        room_name = parts[1]
        if room_name in rooms:
            with lock:
                for student in rooms[room_name]:
                    student.send(f"You have been called back to main.".encode())
                    rooms["main"].append(student)
                    client_rooms[student] = "main"
                rooms[room_name] = []
            broadcast_user_list()

    elif cmd == "/quit":
        client_socket.send("You have left the chat.".encode())
        disconnect_client(client_socket)

    else:
        client_socket.send("Invalid command or insufficient permissions.".encode())


def handle_client(client_socket, address):
    global instructor_connected, students, instructor_socket, client_usernames, muted_clients
    try:
        login_data = client_socket.recv(1024).decode().strip()
        role, username = login_data.split("|")
        print(f"[DEBUG] Role: {role}, Username: {username}")

        with lock:
            client_usernames[client_socket] = username
            rooms["main"].append(client_socket)
            client_rooms[client_socket] = "main"
            if role == 'instructor':
                if instructor_connected:
                    client_socket.send("Connection rejected: Instructor already connected.".encode())
                    client_socket.close()
                    del client_usernames[client_socket]
                    return
                else:
                    instructor_connected = True
                    instructor_socket = client_socket
                    client_socket.send("Instructor connected successfully!".encode())
            elif role == 'student':
                if not instructor_connected:
                    client_socket.send("Connection rejected: No instructor connected yet.".encode())
                    client_socket.close()
                    del client_usernames[client_socket]
                    return
                else:
                    students.append(client_socket)
                    client_socket.send("Student connected successfully!".encode())

        while True:
            msg = client_socket.recv(1024).decode()
            if msg:
                if client_socket in muted_clients and time.time() < muted_clients[client_socket]:
                    client_socket.send("You are muted.".encode())
                    continue

                if msg.startswith("/"):
                    handle_command(client_socket, msg)
                else:
                    broadcast_message(client_socket, msg)

    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        disconnect_client(client_socket)


def disconnect_client(client_socket):
    global instructor_connected, instructor_socket, students
    with lock:
        if client_socket in client_usernames:
            del client_usernames[client_socket]
        for room, clients in rooms.items():
            if client_socket in clients:
                clients.remove(client_socket)
                break
        if client_socket == instructor_socket:
            instructor_connected = False
            instructor_socket = None
            for student in students:
                try:
                    student.send("Instructor disconnected. Connection terminated.".encode())
                    student.close()
                except Exception as e:
                    print(f"[ERROR] Unable to disconnect student: {e}")
            students.clear()
        elif client_socket in students:
            students.remove(client_socket)

    client_socket.close()


def periodically_broadcast():
    while True:
        broadcast_user_list()
        time.sleep(0.2)


# Set up the server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"Server listening on {HOST}:{PORT}...")

threading.Thread(target=periodically_broadcast, daemon=True).start()

while True:
    try:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()
    except Exception as e:
        print(f"Error accepting connection: {e}")

