import socket
import threading
import time

# Server constants
HOST = socket.gethostbyname(socket.gethostname())
PORT = 8080

# Keep track of roles and connected clients
instructor_connected = False
students = []
instructor_socket = None
lock = threading.Lock()  # Thread lock to synchronize shared state access
client_usernames = {}  # Dictionary to map client sockets to usernames
muted_clients = {}  # Dictionary to track muted clients and their mute durations


def broadcast_user_list():
    """Broadcast the list of connected users (with roles) to all connected clients."""
    with lock:
        user_list = []

        # Include instructor only if connected
        if instructor_socket:
            user_list.append(f"{client_usernames.get(instructor_socket, 'Unknown')} (Instructor)")

        # Include students only if instructor is present
        if instructor_connected:
            for student in students:
                user_list.append(f"{client_usernames.get(student, 'Unknown')} (Student)")

        # Send the appropriate user list to all clients
        for client_socket in client_usernames.keys():
            try:
                if client_socket in students and not instructor_connected:
                    # Show only the student's name if the instructor is disconnected
                    user_list_str = f"{client_usernames.get(client_socket, 'Unknown')} (Student)"
                else:
                    # Show the full user list
                    user_list_str = ";".join(user_list)

                client_socket.send(f"USER_LIST|{user_list_str}".encode())
            except Exception as e:
                print(f"Error sending user list to client: {e}")


def broadcast_message(sender_socket, message):
    """Broadcast a message to all other connected clients."""
    global instructor_socket  # Declare this as global to access the global scope variable
    with lock:
        sender_username = client_usernames.get(sender_socket, "Unknown")
        for student in students:
            if student != sender_socket:
                try:
                    student.send(f"{sender_username}: {message}".encode())
                except Exception as e:
                    print(f"Error sending to a student: {e}")
                    students.remove(student)  # Remove broken sockets
        if instructor_socket and instructor_socket != sender_socket:
            try:
                instructor_socket.send(f"{sender_username}: {message}".encode())
            except Exception as e:
                print(f"Error sending to the instructor: {e}")
                instructor_socket = None


def handle_command(client_socket, command):
    """Handle instructor commands."""
    parts = command.split(" ", 2)
    cmd = parts[0]

    if cmd == "/whisper" and len(parts) > 2:
        recipient_name, whisper_msg = parts[1], parts[2]
        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            recipient_socket.send(f"[Whisper from {client_usernames[client_socket]}]: {whisper_msg}".encode())
        else:
            client_socket.send("User not found.".encode())

    elif cmd == "/kick" and client_socket == instructor_socket:
        recipient_name = parts[1]

        # Prevent self-kicking
        if recipient_name == client_usernames[client_socket]:
            client_socket.send("You cannot kick yourself.".encode())
            return

        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            recipient_socket.send("You have been kicked out by the instructor.".encode())
            disconnect_client(recipient_socket)
            broadcast_message(client_socket, f"{recipient_name} has been kicked out.")
        else:
            client_socket.send("User not found.".encode())


    elif cmd == "/mute" and client_socket == instructor_socket:
        recipient_name = parts[1]

        # Prevent self-muting
        if recipient_name == client_usernames[client_socket]:
            client_socket.send("You cannot mute yourself.".encode())
            return

        recipient_socket = next((sock for sock, name in client_usernames.items() if name == recipient_name), None)
        if recipient_socket:
            duration = int(parts[2]) if len(parts) > 2 else 60  # Default mute duration to 60 seconds
            muted_clients[recipient_socket] = time.time() + duration
            client_socket.send(f"{recipient_name} has been muted for {duration} seconds.".encode())
            recipient_socket.send(f"You have been muted by the instructor for {duration} seconds.".encode())
        else:
            client_socket.send("User not found.".encode())

    elif cmd == "/quit":
        client_socket.send("You have left the chat.".encode())
        disconnect_client(client_socket)

    else:
        client_socket.send("Invalid command or insufficient permissions.".encode())



def handle_client(client_socket, address):
    global instructor_connected, students, instructor_socket, client_usernames, muted_clients
    try:
        # Receive initial data from the client
        login_data = client_socket.recv(1024).decode().strip()
        role, username = login_data.split("|")
        print(f"[DEBUG] Role: {role}, Username: {username}")

        with lock:  # Lock for thread-safe access
            client_usernames[client_socket] = username  # Map the client socket to their username

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

        # Handle incoming messages
        while True:
            msg = client_socket.recv(1024).decode()
            if msg:
                if client_socket in muted_clients and time.time() < muted_clients[client_socket]:
                    client_socket.send("You are muted.".encode())
                    continue

                if msg.startswith("/"):
                    handle_command(client_socket, msg)
                else:
                    print(f"[{address}] {username}: {msg}")
                    broadcast_message(client_socket, msg)

    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        disconnect_client(client_socket)


def disconnect_client(client_socket):
    """Disconnect the client and clean up state."""
    global instructor_connected, instructor_socket, students
    with lock:
        if client_socket in client_usernames:
            del client_usernames[client_socket]
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
    """Broadcast user list periodically."""
    while True:
        broadcast_user_list()
        time.sleep(0.2)  # Send updates to all clients every 0.2 seconds


# Set up the server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"Server listening on {HOST}:{PORT}...")

# Start the thread for periodic user list broadcasting
threading.Thread(target=periodically_broadcast, daemon=True).start()

while True:
    try:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()
    except Exception as e:
        print(f"Error accepting connection: {e}")
