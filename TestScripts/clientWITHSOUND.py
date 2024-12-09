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
SERVER_PORT = 8888  # Port for video (TCP)
AUDIO_PORT = 9999  # Port for audio (UDP)

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

def send_video(client_socket):
    """Send video frames over TCP."""
    while not stop_client.is_set():
        try:
            ret, frame = cam.read()
            if not ret or frame is None:
                print("Error: Failed to capture video frame.")
                continue

            # Resize and serialize the frame
            frame = imutils.resize(frame, width=320)
            frame_data = pickle.dumps(frame)
            packet = struct.pack("Q", len(frame_data)) + frame_data

            # Send the frame data
            client_socket.sendall(packet)
            time.sleep(0.03)  # Throttle to maintain a reasonable frame rate
        except Exception as e:
            print(f"Error in send_video: {e}")
            break
    print("Closing send_video...")
    cam.release()

def receive_video(client_socket):
    """Receive and display video frames over TCP."""
    data_buffer = b""
    payload_size = struct.calcsize("Q")

    while not stop_client.is_set():
        try:
            # Receive the message size
            while len(data_buffer) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Server disconnected.")
                data_buffer += packet

            packed_msg_size = data_buffer[:payload_size]
            data_buffer = data_buffer[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            # Receive the frame data
            while len(data_buffer) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Server disconnected.")
                data_buffer += packet

            frame_data = data_buffer[:msg_size]
            data_buffer = data_buffer[msg_size:]

            # Deserialize and display the video frame
            frame = pickle.loads(frame_data)
            cv2.imshow("Video Stream", frame)

            if cv2.waitKey(1) & 0xFF == ord('q') or cv2.getWindowProperty("Video Stream", cv2.WND_PROP_VISIBLE) < 1:
                break
        except Exception as e:
            print(f"Error in receive_video: {e}")
            break
    print("Closing receive_video...")
    cv2.destroyAllWindows()

def send_audio(audio_socket, audio_server):
    """Capture and send audio data via UDP."""
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        while not stop_client.is_set():
            try:
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"Audio capture error: {e}")
                audio_data = b'\x00' * CHUNK  # Send silence if there's an error

            audio_socket.sendto(audio_data, audio_server)  # Send audio to the server
    except Exception as e:
        print(f"Error in send_audio: {e}")
    finally:
        print("Closing send_audio...")



def receive_audio(audio_socket):
    """Receive and play audio data over UDP."""
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    while not stop_client.is_set():
        try:
            audio_data, _ = audio_socket.recvfrom(4096)
            if not audio_data:
                print("[WARNING] Received empty audio packet.")
                continue
            # Ensure audio packet size matches CHUNK
            if len(audio_data) != CHUNK:
                print(f"[DEBUG] Received audio packet of unexpected size: {len(audio_data)}")
            stream.write(audio_data)
        except Exception as e:
            print(f"Error in receive_audio: {e}")
            break
    print("Closing receive_audio...")


def stop_client_handler(signal, frame):
    """Handle Ctrl+C signal to stop the client."""
    print("\n[SHUTTING DOWN] Client is stopping...")
    stop_client.set()  # Signal threads to stop

# Attach signal handler for graceful shutdown
signal.signal(signal.SIGINT, stop_client_handler)

# Main client execution
try:
    # Video socket (TCP)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))

    # Audio socket (UDP)
    audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    audio_server = (SERVER_HOST, AUDIO_PORT)
    # Start threads
    video_send_thread = threading.Thread(target=send_video, args=(client_socket,), daemon=True)
    video_receive_thread = threading.Thread(target=receive_video, args=(client_socket,), daemon=True)
    audio_send_thread = threading.Thread(target=send_audio, args=(audio_socket, audio_server), daemon=True)
    audio_receive_thread = threading.Thread(target=receive_audio, args=(audio_socket,), daemon=True)

    video_send_thread.start()
    video_receive_thread.start()
    audio_send_thread.start()
    audio_receive_thread.start()

    print("Client threads started. Press Ctrl+C to stop.")

    # Keep the main thread running to handle Ctrl+C
    while not stop_client.is_set():
        time.sleep(0.1)
except Exception as e:
    print(f"Error: {e}")
finally:
    stop_client.set()
    client_socket.close()
    print("Client sockets closed.")
