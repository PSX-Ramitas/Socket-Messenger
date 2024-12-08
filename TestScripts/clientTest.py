import cv2
import imutils
import pyaudio
import socket
import threading
import pickle
import struct
import time

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

# Check camera initialization
if not cam.isOpened():
    print("Error: Camera not initialized.")
    exit(1)

def send_data(client_socket):
    """Capture and send video and audio data."""
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        while True:
            ret, frame = cam.read()
            if not ret or frame is None:
                print("Error: Failed to capture video frame.")
                continue

            # Debug: Print confirmation of video capture
            print("Captured a video frame.")

            # Resize and serialize the frame
            frame = imutils.resize(frame, width=320)
            frame_data = pickle.dumps(frame)

            # Debug: Print size of serialized frame
            print(f"Serialized frame size: {len(frame_data)} bytes")

            # Capture audio data
            audio_data = stream.read(CHUNK)

            # Pack and send video + audio data
            packet = struct.pack("Q", len(frame_data)) + frame_data + audio_data
            client_socket.sendall(packet)

            # Debug: Confirm packet sent
            print("Packet sent to server.")
            # Debug: Throttle send rate
            time.sleep(0.5)  # Adjust delay as needed for smooth performance
    except Exception as e:
        print(f"Error in send_data: {e}")
    finally:
        print("Closing send_data...")
        cam.release()

def receive_data(client_socket):
    """Receive and display video and audio data."""
    print("Starting receive_data...")  # Debug
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
        data_buffer = b""
        payload_size = struct.calcsize("Q")

        while True:
            # Receive packet header (frame length)
            while len(data_buffer) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Connection closed by server.")
                data_buffer += packet

            # Debug: Confirm received data chunk
            print(f"Received {len(packet)} bytes from server.")

            # Unpack the frame length
            packed_msg_size = data_buffer[:payload_size]
            data_buffer = data_buffer[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            # Debug: Print expected frame size
            print(f"Expecting frame size: {msg_size} bytes")

            # Receive frame and audio data
            while len(data_buffer) < msg_size + CHUNK:
                packet = client_socket.recv(4096)
                if not packet:
                    raise ConnectionError("Incomplete data received from server.")
                data_buffer += packet

            frame_data = data_buffer[:msg_size]
            audio_data = data_buffer[msg_size:msg_size + CHUNK]
            data_buffer = data_buffer[msg_size + CHUNK:]

            # Debug: Confirm received full frame and audio
            print(f"Received full frame and audio, frame size: {len(frame_data)} bytes")

            # Deserialize video frame
            frame = pickle.loads(frame_data)

            # Debug: Confirm deserialization
            print("Deserialized video frame.")

            # Display video frame
            cv2.imshow("Video Stream", frame)

            # Play audio
            stream.write(audio_data)

            # Exit on 'q' or window close
            if cv2.waitKey(1) & 0xFF == ord('q') or cv2.getWindowProperty("Video Stream", cv2.WND_PROP_VISIBLE) < 1:
                break
    except Exception as e:
        print(f"Error in receive_data: {e}")
    finally:
        print("Closing receive_data...")
        cv2.destroyAllWindows()

# Create and connect the client socket
try:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))

    # Start threads
    send_thread = threading.Thread(target=send_data, args=(client_socket,))
    receive_thread = threading.Thread(target=receive_data, args=(client_socket,))

    send_thread.start()
    print("send_data thread started.")
    receive_thread.start()
    print("receive_data thread started.")

    # Wait for threads to finish
    send_thread.join()
    receive_thread.join()
except Exception as e:
    print(f"Error: {e}")
finally:
    client_socket.close()
