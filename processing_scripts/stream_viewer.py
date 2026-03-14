# Test script to visualize the live raw USB video stream from the ArduCAM Pico4ML

import serial
import numpy as np
import cv2
import time

# Configuration Parameters
PORT = 'COM4'       # Serial port assigned to the ArduCAM (change according to your OS)
BAUDRATE = 115200   # Baudrate (must match the Pico4ML configuration)
WIDTH = 80          # Width of the cropped frame sent by the Pico
HEIGHT = 160        # Height of the cropped frame sent by the Pico

# Synchronization pattern (4 bytes) to identify the start of a new frame.
# This prevents frame tearing or shifting if bytes are lost during USB transmission.
SYNC_PATTERN = b'\xAA\xBB\xCC\xDD'

def run_stream():

    try:

        # Open the serial connection to the Pico4ML
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        print(f"Connected to {PORT}. Press 'q' on the video window to exit.")
    except Exception as e:

        print(f"Error opening serial port: {e}")
        return

    buffer = b''
    # Total bytes expected per frame (1 byte per pixel for 8-bit Grayscale images)
    FRAME_SIZE = WIDTH * HEIGHT 

    while True:

        # Read all available incoming data from the serial buffer
        if ser.in_waiting > 0:

            buffer += ser.read(ser.in_waiting)

        # Search for the start-of-frame synchronization pattern
        if SYNC_PATTERN in buffer:

            # Find the exact index of the sync pattern to align the frame data.
            # If multiple patterns exist in a huge buffer, we align to the first one found.
            split_index = buffer.find(SYNC_PATTERN)
            
            # Check if the buffer contains enough data for a complete frame 
            # (Sync pattern length = 4 bytes + total frame bytes)
            if len(buffer) >= split_index + 4 + FRAME_SIZE:

                # Extract the raw binary image data exactly after the sync pattern
                start_data = split_index + 4
                img_raw = buffer[start_data : start_data + FRAME_SIZE]
                
                # Remove the processed data (including the sync pattern) from the buffer
                # to free memory and prepare for the next frame
                buffer = buffer[start_data + FRAME_SIZE:]

                # Convert the raw bytes into a 2D OpenCV image
                try:

                    # Convert raw bytes to a flat 1D numpy array of unsigned 8-bit integers (grayscale)
                    img_array = np.frombuffer(img_raw, dtype=np.uint8)
                    
                    # Reshape the 1D array into a 2D matrix (Height x Width)
                    img_matrix = img_array.reshape((HEIGHT, WIDTH))
                    
                    # Upscale the image (4x) for better visualization on the PC monitor.
                    # Using INTER_NEAREST interpolation to keep the original pixelated look without blurring.
                    img_big = cv2.resize(img_matrix, (WIDTH*4, HEIGHT*4), interpolation=cv2.INTER_NEAREST)
                    
                    # Display the live stream in a window
                    cv2.imshow('Pico4ML Raw USB Stream', img_big)
                    
                except Exception as err:
                    
                    print(f"Frame decoding error: {err}")

        # Listen for the 'q' key to gracefully exit the application
        if cv2.waitKey(1) & 0xFF == ord('q'):

            print("Exit requested by the user.")
            break
    
    # Clean up resources and close ports
    ser.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":

    run_stream()