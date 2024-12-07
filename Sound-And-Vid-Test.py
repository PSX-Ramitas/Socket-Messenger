import cv2
import imutils
import time
import queue
import os
import threading
import pyaudio

# Video settings
q = queue.Queue(maxsize=10)
cam = cv2.VideoCapture(0)

# Get default framerate from the camera
FPS = cam.get(cv2.CAP_PROP_FPS)
print('FPS: ', FPS)
TS = 1 / FPS
print("TS: ", TS, " seconds")

# Audio settings
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
audio_queue = queue.Queue(maxsize=10)

# Audio playback
p = pyaudio.PyAudio()

def video_stream_gen():
    """Generate video frames and put them in a queue."""
    WIDTH = 320
    while cam.isOpened():
        _, frame = cam.read()
        frame = imutils.resize(frame, width=WIDTH)
        q.put(frame)
        print('Queue size: ', q.qsize())
    cam.release()

def audio_stream_gen():
    """Capture audio and put it in a queue."""
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    while True:
        data = stream.read(CHUNK)
        audio_queue.put(data)

def audio_playback():
    """Play back audio in real time"""
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True)
    while True:
        if not audio_queue.empty():
            data = audio_queue.get()
            stream.write(data)

# Start threads
video_thread = threading.Thread(target=video_stream_gen, args=())
audio_thread = threading.Thread(target=audio_stream_gen, args=())
playback_thread = threading.Thread(target=audio_playback, args=())

video_thread.start()
audio_thread.start()
playback_thread.start()

# Display loop
fps, st, frames_to_count, cnt = (0, 0, 1, 0)

while True:
    # Video frame
    frame = q.get()

    # Calculate FPS
    frame = cv2.putText(frame, 'FPS: ' + str(round(fps, 1)), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    if cnt == frames_to_count:
        try:
            fps = frames_to_count / (time.time() - st)
            st = time.time()
            cnt = 0
        except ZeroDivisionError:
            pass
    cnt += 1

    # Display frame
    cv2.imshow('Video Stream', frame)

    # Quit on 'q' key press
    key = cv2.waitKey(int(TS * 1000)) & 0xFF
    if key == ord('q'):
        os._exit(1)
