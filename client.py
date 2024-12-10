import socket
import tkinter as tk
from tkinter import messagebox
import threading
from PIL import Image, ImageTk  # Import PIL for handling image formats


class ChatClient:
    def __init__(self):
        self.client_socket = None
        self.root = tk.Tk()
        self.root.title("Login")
        self.username = tk.StringVar()
        self.role = tk.StringVar()
        self.server_ip = tk.StringVar(value="localhost")
        self.server_port = tk.StringVar(value="8080")
        
        # Load scrolling background
        self.bg_image = Image.open("Assets/Images/background.jpg")
        self.bg_width, self.bg_height = self.bg_image.size
        self.bg_image_tk1 = ImageTk.PhotoImage(self.bg_image)
        self.bg_image_tk2 = ImageTk.PhotoImage(self.bg_image)  # Second image for seamless scrolling
        self.scroll_offset = 0

        # Load logo image
        self.logo_image = Image.open("Assets/Images/logo.png")
        self.logo_image_tk = ImageTk.PhotoImage(self.logo_image)

        # Setup UI with scrolling effect
        self.setup_login_ui()
        self.animate_background()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """Handle the client window close to disconnect properly."""
        try:
            if self.client_socket:
                self.client_socket.send("DISCONNECT".encode())  # Notify server about disconnection
                self.client_socket.close()
        except:
            pass
        self.root.destroy()

    def animate_background(self):
        """Scroll the background continuously left."""
        # Shift image by 1 pixel to the left
        self.scroll_offset -= 1

        # Reset scrolling if the first image scrolls off the screen
        if self.scroll_offset <= -self.bg_width:
            self.scroll_offset = 0

        # Redraw the scrolling images
        self.canvas.delete("all")
        self.canvas.create_image(self.scroll_offset, 0, anchor="nw", image=self.bg_image_tk1)
        self.canvas.create_image(self.scroll_offset + self.bg_width, 0, anchor="nw", image=self.bg_image_tk2)

        # Overlay the logo in the center of the canvas
        logo_x_position = 200  # Adjust X as needed to center the logo
        logo_y_position = 150   # Adjust Y as needed
        self.canvas.create_image(logo_x_position, logo_y_position, anchor="center", image=self.logo_image_tk)

        # Schedule the next scroll update
        self.root.after(20, self.animate_background)

    def setup_login_ui(self):
        """Setup the initial login screen with scrolling effect."""
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create Canvas for scrolling background
        self.canvas = tk.Canvas(self.root, width=400, height=300)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Set up widgets
        tk.Label(self.root, text="Server IP Address:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.server_ip).pack(pady=5)

        tk.Label(self.root, text="Server Port:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.server_port).pack(pady=5)

        tk.Label(self.root, text="Enter Username:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.username).pack(pady=5)

        tk.Label(self.root, text="Select Role:").pack(pady=5)
        role_options = tk.OptionMenu(self.root, self.role, "student", "instructor")
        self.role.set("student")
        role_options.pack(pady=5)

        tk.Button(self.root, text="Login", command=self.connect_to_server).pack(pady=10)

    def connect_to_server(self):
        """Attempt connection to server with the provided credentials."""
        if not self.username.get() or not self.role.get():
            messagebox.showerror("Error", "Please enter a valid username and select role")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_ip = self.server_ip.get()
            server_port = int(self.server_port.get())

            self.client_socket.connect((server_ip, server_port))

            # Send role and username as a single message to the server
            login_data = f"{self.role.get()}|{self.username.get()}"
            self.client_socket.send(login_data.encode())

            # Wait for server's response
            response = self.client_socket.recv(1024).decode().strip()
            print(f"[DEBUG] Server response: {response}")

            if "rejected" in response:
                messagebox.showerror("Connection Failed", response)
                self.client_socket.close()
            else:
                messagebox.showinfo("Success", response)
                self.setup_chat_ui()
                threading.Thread(target=self.receive_message, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Could not connect: {str(e)}")
            self.setup_login_ui()

    def setup_chat_ui(self):
        """Setup the main chat window UI with a sidebar."""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.main_frame = tk.Frame(self.root)
        self.root.title("Chat Lobby [" + self.username.get() + "]")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create the sidebar
        self.sidebar = tk.Frame(self.main_frame, width=200, bg="lightgrey")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        self.user_listbox = tk.Listbox(self.sidebar, height=20, bg="lightgrey")
        self.user_listbox.pack(padx=5, pady=5, fill=tk.Y)

        # Create the chat area
        self.chat_area = tk.Frame(self.main_frame)
        self.chat_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(self.chat_area, text="Connected! Type messages below:").pack(pady=5)
        self.chat_box = tk.Text(self.chat_area, height=15, width=50, state=tk.DISABLED)
        self.chat_box.pack(pady=5)

        self.msg_entry = tk.Entry(self.chat_area, width=40)
        self.msg_entry.pack(pady=5)
        self.msg_entry.bind("<KeyRelease>", self.show_command_suggestions)

        self.suggestion_frame = tk.Frame(self.chat_area, bg="white", relief="solid", bd=1)
        self.suggestion_frame.place_forget()

        tk.Button(self.chat_area, text="Send", command=self.send_message).pack(pady=10)

    def show_command_suggestions(self, event):
        """Display command suggestions when user types '/'."""
        input_text = self.msg_entry.get()
        if input_text.startswith("/"):
            commands = [
                "/whisper <username> text",
                "/mute <username> [duration]",
                "/kick <username>",
                "/create_room <room_name>",
                "/move_to_room <username> <room_name>",
                "/call_back <room_name>",
                "/quit"
            ]
            matching_commands = [cmd for cmd in commands if cmd.startswith(input_text)]

            if matching_commands:
                self.suggestion_frame.place(x=self.msg_entry.winfo_x(), y=self.msg_entry.winfo_y() - 50)
                for widget in self.suggestion_frame.winfo_children():
                    widget.destroy()

                for cmd in matching_commands:
                    lbl = tk.Label(self.suggestion_frame, text=cmd, bg="white", anchor="w")
                    lbl.pack(fill=tk.X)
                    lbl.bind("<Button-1>", lambda e, c=cmd: self.autocomplete_command(c))
            else:
                self.suggestion_frame.place_forget()
        else:
            self.suggestion_frame.place_forget()

    def autocomplete_command(self, command):
        """Autocomplete the selected command."""
        self.msg_entry.delete(0, tk.END)
        self.msg_entry.insert(0, command)
        self.suggestion_frame.place_forget()

    def send_message(self):
        """Send a chat message or handle a local command."""
        msg = self.msg_entry.get().strip()
        if msg:
            if msg.startswith("/"):
                self.process_local_command(msg)
            else:
                try:
                    self.client_socket.send(msg.encode())
                    self.msg_entry.delete(0, tk.END)
                    self.display_message(f"You: {msg}", "normal")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not send message: {str(e)}")

    def process_local_command(self, command):
        """Process local commands like /quit."""
        if command.startswith("/quit"):
            self.on_close()
        else:
            self.client_socket.send(command.encode())  # Send to the server for processing

    def receive_message(self):
        """Listen for server messages and handle them appropriately."""
        while True:
            try:
                msg = self.client_socket.recv(1024).decode()
                if msg.startswith("USER_LIST|"):
                    self.update_user_list(msg.split("|")[1])
                elif "moved to room" in msg or "called back" in msg:
                    messagebox.showinfo("Room Update", msg)
                else:
                    self.display_message(msg, "normal")
            except:
                self.display_message("[System] Lost connection to server.", "bold")
                break

    def update_user_list(self, user_list_str):
        """Update the Listbox sidebar with new user information."""
        self.user_listbox.delete(0, tk.END)
        for user in user_list_str.split(";"):
            self.user_listbox.insert(tk.END, user)

    def display_message(self, message, style):
        """Display messages in the chat box with different styles."""
        self.chat_box.config(state=tk.NORMAL)
        if style == "bold":
            self.chat_box.insert(tk.END, f"{message}\n", "bold")
        elif style == "italic":
            self.chat_box.insert(tk.END, f"{message}\n", "italic")
        else:
            self.chat_box.insert(tk.END, f"{message}\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state=tk.DISABLED)

    def run(self):
        """Start the main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    client = ChatClient()
    client.run()
