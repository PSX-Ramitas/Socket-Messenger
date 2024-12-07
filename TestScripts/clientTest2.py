import cv2
import imutils
import pyaudio
import socket
import threading
import pickle
import struct

# Server connection
SERVER_HOST = '192.168.1.68'  # Replace with the server's IP address
SERVER_PORT = 8080

# Video settings
cam = cv2.VideoCapture(0)

# Audio settings
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

def send_data(client_socket):
    """Capture and send video and audio data."""
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    while cam.isOpened():
        # Video capture
        _, frame = cam.read()
        frame = imutils.resize(frame, width=320)

        # Encode frame as bytes
        frame_data = pickle.dumps(frame)

        # Audio capture
        audio_data = stream.read(CHUNK)

        # Send both video and audio
        packet = struct.pack("Q", len(frame_data)) + frame_data + audio_data
        client_socket.sendall(packet)

def receive_data(client_socket):
    """Receive and display video and audio data."""
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    data_buffer = b""
    payload_size = struct.calcsize("Q")

    while True:
        while len(data_buffer) < payload_size:
            data_buffer += client_socket.recv(4096)
        packed_msg_size = data_buffer[:payload_size]
        data_buffer = data_buffer[payload_size:]
        msg_size = struct.unpack("Q", packed_msg_size)[0]

        while len(data_buffer) < msg_size:
            data_buffer += client_socket.recv(4096)
        
        frame_data = data_buffer[:msg_size]
        audio_data = data_buffer[msg_size:msg_size + CHUNK]
        data_buffer = data_buffer[msg_size + CHUNK:]

        # Decode video frame
        frame = pickle.loads(frame_data)
        cv2.imshow("Video Stream", frame)

        # Play audio
        stream.write(audio_data)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))

# Start threads
threading.Thread(target=send_data, args=(client_socket,)).start()
threading.Thread(target=receive_data, args=(client_socket,)).start()
