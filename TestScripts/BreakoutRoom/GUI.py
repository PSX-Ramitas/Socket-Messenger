import tkinter as tk
from tkinter import messagebox
import subprocess

# GUI for role selection
def start_gui():
    def launch_client(role):
        """Launch the client with the selected role."""
        global user_role
        user_role = role
        try:
            subprocess.Popen(["python", "TestScripts\BreakoutRoom\client.py", role])
            root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch client: {e}")

    root = tk.Tk()
    root.title("Breakout Room Role Selection")
    root.geometry("300x150")

    tk.Label(root, text="Select your role:", font=("Arial", 14)).pack(pady=10)

    tk.Button(root, text="Instructor", width=15, command=lambda: launch_client("Instructor")).pack(pady=5)
    tk.Button(root, text="Student", width=15, command=lambda: launch_client("Student")).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    start_gui()
