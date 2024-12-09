import socket
import threading


# Server constants
HOST = '129.8.215.21'
PORT = 8080

# Keep track of roles and connected clients
instructor_connected = False
students = []
instructor_socket = None
lock = threading.Lock()  # Thread lock to synchronize shared state access


def broadcast_message(sender_socket, message):
    """Broadcast message to all other connected clients."""
    global instructor_socket  # Declare this as global to access the global scope variable
    with lock:
        for student in students:
            if student != sender_socket:
                try:
                    student.send(message.encode())
                except Exception as e:
                    print(f"Error sending to a student: {e}")
                    students.remove(student)  # Remove broken sockets
        if instructor_socket and instructor_socket != sender_socket:
            try:
                instructor_socket.send(message.encode())
            except Exception as e:
                print(f"Error sending to the instructor: {e}")
                instructor_socket = None



def handle_client(client_socket, address):
    global instructor_connected, students, instructor_socket
    try:
        # Prompt the client for their role
        client_socket.send("Please enter your role (student/instructor): ".encode())

        # Wait for role choice
        role = client_socket.recv(1024).decode().strip().lower()
        print(f"[DEBUG] Role received from {address}: {role}")  # Debugging log

        with lock:  # Lock for thread-safe access to shared state
            if role == 'instructor':
                if instructor_connected:
                    client_socket.send(
                        "Connection rejected: Instructor already connected.".encode()
                    )
                    client_socket.close()
                    return
                else:
                    instructor_connected = True
                    instructor_socket = client_socket
                    client_socket.send("Instructor connected successfully!".encode())
            elif role == 'student':
                if not instructor_connected:
                    client_socket.send(
                        "Connection rejected: No instructor connected yet.".encode()
                    )
                    client_socket.close()
                    return
                else:
                    students.append(client_socket)
                    client_socket.send("Student connected successfully!".encode())
            else:
                client_socket.send("Connection rejected: Invalid role.".encode())
                client_socket.close()
                return

        # Handle incoming messages
        while True:
            msg = client_socket.recv(1024).decode()
            if msg:
                print(f"[{address}] {role}: {msg}")
                # Send the formatted message to other clients
                formatted_message = f"{address} {role.capitalize()}: {msg}"
                broadcast_message(client_socket, formatted_message)

    except Exception as e:
        print(f"Error with {address}: {e}")
    finally:
        # Clean up
        with lock:
            if role == "instructor":
                instructor_connected = False
                instructor_socket = None
            elif role == "student" and client_socket in students:
                students.remove(client_socket)

        client_socket.close()


# Set up the server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"Server listening on {HOST}:{PORT}...")

while True:
    client_socket, client_address = server_socket.accept()
    print(f"Connection from {client_address}")
    thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
    thread.start()