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

# Server connection
SERVER_HOST = '192.168.1.140'  # Replace with the server's IP address
SERVER_PORT = 8888

# Video settings
cam = cv2.VideoCapture(0)

# Audio settings
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

# Global flag for stopping threads
stop_client = threading.Event()

# Check camera initialization
if not cam.isOpened():
    print("Error: Camera not initialized.")
    sys.exit(1)

def send_data(client_socket):
    """Capture and send video frames only."""
    try:
        while not stop_client.is_set():
            ret, frame = cam.read()
            if not ret or frame is None:
                print("Error: Failed to capture video frame.")
                continue

            # Resize and serialize the frame
            frame = imutils.resize(frame, width=320)
            frame_data = pickle.dumps(frame)
            packet = struct.pack("Q", len(frame_data)) + frame_data
            client_socket.sendall(packet)
            print(f"Packet sent, frame size: {len(frame_data)} bytes")
            time.sleep(0.5)  # Throttle to avoid overwhelming the server
    except (ConnectionError, BrokenPipeError):
        print("Server disconnected. Stopping send_data...")
    except Exception as e:
        print(f"Error in send_data: {e}")
    finally:
        print("Closing send_data...")
        cam.release()

def receive_data(client_socket):
    """Receive and display video frames only."""
    print("Starting receive_data...")
    try:
        data_buffer = b""
        payload_size = struct.calcsize("Q")

        while not stop_client.is_set():
            while len(data_buffer) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Server disconnected.")
                data_buffer += packet

            packed_msg_size = data_buffer[:payload_size]
            data_buffer = data_buffer[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data_buffer) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Server disconnected.")
                data_buffer += packet

            frame_data = data_buffer[:msg_size]
            data_buffer = data_buffer[msg_size:]

            frame = pickle.loads(frame_data)
            cv2.imshow("Video Stream", frame)

            if cv2.waitKey(1) & 0xFF == ord('q') or cv2.getWindowProperty("Video Stream", cv2.WND_PROP_VISIBLE) < 1:
                break
    except (ConnectionError, BrokenPipeError):
        print("Server disconnected. Stopping receive_data...")
    except Exception as e:
        print(f"Error in receive_data: {e}")
    finally:
        print("Closing receive_data...")
        cv2.destroyAllWindows()

def stop_client_handler(signal, frame):
    """Handle Ctrl+C signal to stop the client."""
    print("\n[SHUTTING DOWN] Client is stopping...")
    stop_client.set()  # Signal threads to stop

# Attach signal handler for graceful shutdown
signal.signal(signal.SIGINT, stop_client_handler)

# Main client execution
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))

    # Start threads
    send_thread = threading.Thread(target=send_data, args=(client_socket,), daemon=True)
    receive_thread = threading.Thread(target=receive_data, args=(client_socket,), daemon=True)

    send_thread.start()
    print("send_data thread started.")
    receive_thread.start()
    print("receive_data thread started.")

    # Keep the main thread running to handle Ctrl+C
    while not stop_client.is_set():
        time.sleep(0.1)
except Exception as e:
    print(f"Error: {e}")
finally:
    stop_client.set()  # Ensure all threads exit
    client_socket.close()
    print("Client socket closed.")

