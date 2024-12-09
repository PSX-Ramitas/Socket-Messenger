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
                stop_client.set()
                break
        except Exception as e:
            print(f"Error receiving video: {e}")
            break
    cv2.destroyAllWindows()


def send_audio():
    """Capture audio from the microphone and send to server via UDP."""
    print("[AUDIO SEND STARTED]")
    # Setup PyAudio input stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    # Setup UDP socket for sending
    audio_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while not stop_client.is_set():
        try:
            audio_data = stream.read(CHUNK, exception_on_overflow=False)
            audio_client_socket.sendto(audio_data, (SERVER_HOST, AUDIO_PORT))
        except Exception as e:
            print(f"Error sending audio: {e}")
            continue

    stream.stop_stream()
    stream.close()
    audio_client_socket.close()
    print("[Audio Send Stopped]")


def receive_audio():
    """Receive audio from server and play it."""
    print("[AUDIO RECEIVE STARTED]")
    # Setup PyAudio playback stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=CHUNK)

    # Setup UDP socket for receiving
    audio_receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    audio_receive_socket.bind((SERVER_HOST, AUDIO_PORT))

    while not stop_client.is_set():
        try:
            # Receive audio from the server
            audio_data, _ = audio_receive_socket.recvfrom(4096)
            if audio_data:
                stream.write(audio_data)
        except Exception as e:
            print(f"Error receiving audio: {e}")
            continue

    stream.stop_stream()
    stream.close()
    audio_receive_socket.close()
    print("[Audio Receive Stopped]")


def stop_client_handler(signal, frame):
    """Stop client threads safely."""
    print("\n[SHUTTING DOWN] Client is stopping...")
    stop_client.set()


signal.signal(signal.SIGINT, stop_client_handler)

# Main client execution
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, VIDEO_PORT))

    # Start threads for video handling
    threading.Thread(target=send_video, args=(client_socket,), daemon=True).start()
    threading.Thread(target=receive_video, args=(client_socket,), daemon=True).start()

    # Start threads for audio
    threading.Thread(target=send_audio, daemon=True).start()
    threading.Thread(target=receive_audio, daemon=True).start()

    # Main loop waits until stop_client is triggered
    while not stop_client.is_set():
        time.sleep(0.1)

except Exception as e:
    print(f"Error: {e}")
finally:
    stop_client.set()
    client_socket.close()
    print("Disconnected from server.")
