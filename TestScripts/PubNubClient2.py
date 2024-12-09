import tkinter as tk
import uuid
from tkinter import scrolledtext, messagebox
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback


user_uuid = str(uuid.uuid4())
print(user_uuid)  # This will generate and print a random UUID

# PubNub configuration
pnconfig = PNConfiguration()
pnconfig.publish_key = 'pub-c-fbb34a75-55a3-47e8-9f98-40c0fabd5314'
pnconfig.subscribe_key = 'sub-c-4505ddd2-a387-402f-884f-57a8f76a5c14'
pnconfig.uuid = user_uuid


current_channel = "main_room"
instructor_count = 0  # Counter to track if an instructor is already in the room
pubnub = None  # PubNub instance will be created dynamically


# GUI Class
class MessagingClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Breakout Room Messaging Client")
        self.username = None
        self.role = None

        # Initialize login screen
        self.create_login_screen()

    def create_login_screen(self):
        self.clear_screen()

        tk.Label(self.root, text="Enter your username:").grid(row=0, column=0, padx=10, pady=5)
        self.username_entry = tk.Entry(self.root, width=30)
        self.username_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self.root, text="Select your role:").grid(row=1, column=0, padx=10, pady=5)
        self.role_var = tk.StringVar(value="Student")
        tk.OptionMenu(self.root, self.role_var, "Student", "Instructor").grid(row=1, column=1, padx=10, pady=5)

        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect)
        self.connect_button.grid(row=2, column=0, columnspan=2, pady=10)

    def connect(self):
        global pubnub, instructor_count

        self.username = self.username_entry.get()
        self.role = self.role_var.get()

        if not self.username:
            messagebox.showerror("Error", "Username cannot be empty!")
            return

        # Set the UUID dynamically and initialize PubNub
        pnconfig.uuid = self.username
        pubnub = PubNub(pnconfig)

        # Handle role logic
        if self.role == "Instructor":
            pubnub.publish().channel('role_check').message({'type': 'join_request', 'role': 'Instructor'}).sync()
        else:
            self.start_chat()

    def start_chat(self):
        pubnub.add_listener(self.PubNubListener(self))
        pubnub.subscribe().channels([current_channel]).execute()

        self.clear_screen()
        self.create_chat_screen()

    def create_chat_screen(self):
        # Message display area
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state='disabled', height=20, width=50)
        self.text_area.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Message entry field
        self.message_entry = tk.Entry(self.root, width=40)
        self.message_entry.grid(row=1, column=0, padx=10, pady=5)

        # Send button
        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=5)

        # Room label
        self.room_label = tk.Label(self.root, text=f"Room: {current_channel}")
        self.room_label.grid(row=2, column=0, columnspan=2, pady=5)

        self.append_message(f"Welcome, {self.username} ({self.role})!")

    def send_message(self):
        message = self.message_entry.get()
        if message:
            pubnub.publish().channel(current_channel).message({'text': message, 'sender': self.username}).sync()
            self.message_entry.delete(0, tk.END)

    def append_message(self, message):
        self.text_area.configure(state='normal')
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.configure(state='disabled')
        self.text_area.see(tk.END)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # PubNub Listener for Incoming Messages
    class PubNubListener(SubscribeCallback):
        def __init__(self, client):
            self.client = client

        def message(self, pubnub, message):
            msg = message.message
            if msg.get('type') == 'instructor_exists':
                messagebox.showerror("Error", "Instructor already exists in the lobby!")
                self.client.root.destroy()  # Close the program
            elif msg.get('type') == 'join_accepted':
                self.client.append_message("You are now the instructor for the breakout room.")
                self.client.start_chat()
            elif 'text' in msg:
                self.client.append_message(f"{msg.get('sender', 'Anonymous')}: {msg['text']}")


# Role-check listener for instructor validation
class RoleCheckListener(SubscribeCallback):
    def message(self, pubnub, message):
        global instructor_count
        msg = message.message
        if msg.get('type') == 'join_request' and msg.get('role') == 'Instructor':
            if instructor_count == 0:
                instructor_count += 1
                pubnub.publish().channel('role_check').message({'type': 'join_accepted'}).sync()
            else:
                pubnub.publish().channel('role_check').message({'type': 'instructor_exists'}).sync()


# Run the Tkinter app
if __name__ == "__main__":
    root = tk.Tk()
    app = MessagingClient(root)

    # Create PubNub instance for role-check listener
    pubnub = PubNub(pnconfig)
    pubnub.subscribe().channels(['role_check']).execute()
    pubnub.add_listener(RoleCheckListener())

    root.mainloop()
