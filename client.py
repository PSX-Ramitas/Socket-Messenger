import socket
import tkinter as tk
from tkinter import messagebox
import threading


class ChatClient:
    def __init__(self):
        self.client_socket = None
        self.root = tk.Tk()
        self.username = tk.StringVar()
        self.role = tk.StringVar()
        self.server_ip = tk.StringVar(value="localhost")
        self.server_port = tk.StringVar(value="8080")
        
        self.setup_login_ui()

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

    def setup_login_ui(self):
        """Setup the initial login window UI."""
        for widget in self.root.winfo_children():
            widget.destroy()

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
        self.root.title(self.username.get())
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

        tk.Button(self.chat_area, text="Send", command=self.send_message).pack(pady=10)

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
        """Listen for server messages and display them in real-time."""
        while True:
            try:
                msg = self.client_socket.recv(1024).decode()
                if msg:
                    if msg.startswith("USER_LIST|"):
                        self.update_user_list(msg.split("|")[1])
                    elif msg.startswith("[System]"):
                        self.display_message(msg, "bold")
                    elif msg.startswith("Whisper"):
                        self.display_message(msg, "italic")
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
        """Start the client main loop."""
        self.root.mainloop()


if __name__ == "__main__":
    client = ChatClient()
    client.run()
