import cv2
import imutils
import pyaudio
import socket
import threading
import pickle
import struct
import time
import signal
import sys

# Server connection details
SERVER_HOST = '192.168.1.68'  # Replace with your server's IP address
VIDEO_PORT = 8888  # TCP port for video
AUDIO_PORT = 9999  # UDP port for audio

# Video capture settings
cam = cv2.VideoCapture(0)

# Audio settings
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

# Global stop flag for threads
stop_client = threading.Event()

if not cam.isOpened():
    print("Error: Camera not initialized.")
    sys.exit(1)


def send_video(client_socket):
    """Capture and send video frames to server."""
    while not stop_client.is_set():
        try:
            ret, frame = cam.read()
            if not ret:
                print("Error: Video capture failed.")
                continue

            # Resize and send video frames
            frame = imutils.resize(frame, width=320)
            frame_data = pickle.dumps(frame)
            packet = struct.pack("Q", len(frame_data)) + frame_data
            client_socket.sendall(packet)
            time.sleep(0.03)  # Adjust frame rate
        except Exception as e:
            print(f"Error sending video: {e}")
            break
    print("Stopping video stream...")
    cam.release()


def receive_video(client_socket):
    """Receive and display server video feed."""
    data_buffer = b""
    payload_size = struct.calcsize("Q")

    while not stop_client.is_set():
        try:
            while len(data_buffer) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    print("Server disconnected.")
                    return
                data_buffer += packet

            packed_msg_size = data_buffer[:payload_size]
            data_buffer = data_buffer[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data_buffer) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    print("Server disconnected.")
                    return
                data_buffer += packet

            frame = pickle.loads(data_buffer[:msg_size])
            data_buffer = data_buffer[msg_size:]

            cv2.imshow("Video Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print(f"Error receiving video: {e}")
            break
    cv2.destroyAllWindows()


def stop_client_handler(signal, frame):
    """Stop client threads safely."""
    print("\n[SHUTTING DOWN] Client is stopping...")
    stop_client.set()


signal.signal(signal.SIGINT, stop_client_handler)

# Main client execution
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, VIDEO_PORT))

    # Threads for video handling
    threading.Thread(target=send_video, args=(client_socket,), daemon=True).start()
    threading.Thread(target=receive_video, args=(client_socket,), daemon=True).start()

    while not stop_client.is_set():
        time.sleep(0.1)

except Exception as e:
    print(f"Error: {e}")
finally:
    stop_client.set()
    client_socket.close()
    print("Disconnected from server.")
