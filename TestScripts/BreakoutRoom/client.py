import cv2
import socket
import threading
import sys
import pickle
import struct
import tkinter as tk
import time
from tkinter import scrolledtext
from PIL import Image, ImageTk

SERVER_HOST = '192.168.1.68'
VIDEO_PORT = 8888
CHAT_PORT = 7777
CHUNK_SIZE = 4096

user_role = sys.argv[1] if len(sys.argv) > 1 else "Student"
stop_client = threading.Event()
camera_active = threading.Event()


def connect_to_server(port):
    """Establish connection to server."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, port))
        return client_socket
    except Exception as e:
        print(f"Connection failed on port {port}: {e}")
        sys.exit(1)


class VideoChatApp:
    def __init__(self, master, video_socket, chat_socket):
        self.master = master
        self.master.title("Breakout Room")
        self.master.geometry("1200x700")
        self.video_socket = video_socket
        self.chat_socket = chat_socket

        # Bind close window event
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # Video display area
        self.video_frame = tk.Frame(master, bg="black", width=700, height=500)
        self.video_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        self.canvas = tk.Canvas(self.video_frame, bg="black", width=700, height=500)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Chat UI
        self.chat_frame = tk.Frame(master, bg="white", width=300, height=500)
        self.chat_frame.grid(row=0, column=1, padx=10, pady=10, sticky="n")
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, state="disabled", width=40, height=25)
        self.chat_display.pack(padx=10, pady=10)

        self.chat_input = tk.Entry(master, width=50)
        self.chat_input.grid(row=1, column=1, padx=10, pady=5, sticky="s")
        self.chat_input.bind("<Return>", self.send_chat_message)

        # Camera toggle
        self.camera_toggle_btn = tk.Button(master, text="Toggle Camera (OFF)", command=self.toggle_camera, width=20, bg="gray", fg="white")
        self.camera_toggle_btn.grid(row=2, column=0, padx=10, sticky="e")

        # Start video and chat handling threads
        threading.Thread(target=self.receive_video, daemon=True).start()
        threading.Thread(target=self.receive_chat_message, daemon=True).start()
        threading.Thread(target=self.send_video, daemon=True).start()

    def toggle_camera(self):
        """Toggles camera feed on or off."""
        if camera_active.is_set():
            camera_active.clear()
            self.camera_toggle_btn.config(text="Toggle Camera (OFF)", bg="gray")
            print("Camera toggled OFF")
        else:
            camera_active.set()
            self.camera_toggle_btn.config(text="Toggle Camera (ON)", bg="green")
            print("Camera toggled ON")

    def send_video(self):
        """Capture and send video to server only when the camera is active."""
        cap = cv2.VideoCapture(0)
        while not stop_client.is_set():
            if camera_active.is_set() and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    frame = cv2.resize(frame, (320, 240))  # Resize to optimize performance
                    data = pickle.dumps(frame)
                    message = struct.pack("Q", len(data)) + data
                    try:
                        self.video_socket.sendall(message)
                    except Exception as e:
                        print(f"Error sending video: {e}")
                        break
            else:
                time.sleep(0.1)  # Sleep to reduce CPU usage when camera is inactive
        cap.release()

    def receive_video(self):
        """Receive video data from server and display it."""
        data = b""
        payload_size = struct.calcsize("Q")
        while not stop_client.is_set():
            try:
                while len(data) < payload_size:
                    packet = self.video_socket.recv(CHUNK_SIZE)
                    if not packet:
                        print("Server disconnected.")
                        return
                    data += packet

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += self.video_socket.recv(CHUNK_SIZE)

                frame_data = data[:msg_size]
                data = data[msg_size:]

                frame = pickle.loads(frame_data)
                self.display_frame(frame)
            except Exception as e:
                print(f"Error receiving video: {e}")
                break

    def display_frame(self, frame):
        """Render received frame on GUI canvas."""
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk  # Keep a reference to prevent garbage collection
        except Exception as e:
            print(f"Error displaying frame: {e}")

    def send_chat_message(self, event=None):
        """Send chat messages through the chat socket."""
        message = self.chat_input.get().strip()
        if message:
            try:
                self.chat_socket.sendall(message.encode("utf-8"))
                self.display_chat_message(f"You: {message}")
                self.chat_input.delete(0, tk.END)
            except Exception as e:
                print(f"Error sending chat message: {e}")

    def receive_chat_message(self):
        """Handle incoming chat messages."""
        while not stop_client.is_set():
            try:
                message = self.chat_socket.recv(1024).decode("utf-8")
                if message:
                    self.display_chat_message(message)
            except Exception as e:
                print(f"Error receiving chat message: {e}")
                break

    def display_chat_message(self, message):
        """Show messages in the chat window."""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state="disabled")
        self.chat_display.yview(tk.END)

    def on_close(self):
        """Cleanup before closing the app."""
        print("Disconnecting...")
        stop_client.set()
        self.video_socket.close()
        self.chat_socket.close()
        self.master.destroy()


if __name__ == "__main__":
    video_socket = connect_to_server(VIDEO_PORT)
    chat_socket = connect_to_server(CHAT_PORT)

    root = tk.Tk()
    camera_active.clear()  # Camera state starts as off
    app = VideoChatApp(root, video_socket, chat_socket)
    root.mainloop()

    stop_client.set()
    video_socket.close()
    chat_socket.close()
