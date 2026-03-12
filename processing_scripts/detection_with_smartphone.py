# Real-time free parking space detection using a smartphone camera stream over Wi-Fi, YOLO inference for object detection, and smartphone GPS data

import cv2
import requests
import numpy as np
from ultralytics import YOLO
import threading
import time
import json
import math

# Configuration & Network
BASE_URL = "http://..."    # Base URL of the Android smartphone local server (must match the App's displayed IP)
VIDEO_STREAM_URL = f"{BASE_URL}/video"
GPS_URL = f"{BASE_URL}/gps"

# Global variable to store the calculated Homography matrix
homography_matrix = None

# Intrinsic calibration parameters
# Camera Matrix (Focal lengths and optical centers) from calibrazione_matrice_videocamera.py
CAMERA_MATRIX = np.array(
[[2.98034313e+03, 0.00000000e+00, 8.68982989e+02],
 [0.00000000e+00, 3.00435775e+03, 1.65354000e+03],
 [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]]
)

# Distortion coefficients from calibrazione_matrice_videocamera.py
DIST_COEFFS = np.array(
[[ 0.36129782, -1.93728988, -0.05787092, -0.01022782, 2.09092017]]
)

# Homography calibration parameters
# 2D Image Points (Pixels) from calibrazione_matrice_omografica.py
PTS_IMAGE = np.array([
    [180, 200],  # Point 1 (Top-Left)
    [460, 200],  # Point 2 (Top-Right)
    [580, 500],  # Point 3 (Bottom-Right)
    [60,  500]   # Point 4 (Bottom-Left)
], dtype="float32")

# 2D Real-world ground coordinates corresponding to the image points (in meters)
PTS_WORLD = np.array([
    [0.0, 1.0],  # Point 1: 0m lateral, 1m forward
    [2.0, 1.0],  # Point 2: 2m lateral, 1m forward
    [2.0, 4.0],  # Point 3: 2m lateral, 4m forward
    [0.0, 4.0]   # Point 4: 0m lateral, 4m forward
], dtype="float32")

# Thread-safe dictionary to store the latest GPS coordinates fetched from the app
gps_data = {"latitude": 0.0, "longitude": 0.0, "timestamp": 0}
gps_lock = threading.Lock()

# Helper function to draw a dashed line (trajectory) from the vehicle to the target parking spot
def draw_dashed_line(image, start_pt, end_pt, color, thickness=1, dash_length=10, gap_length=5):

    dist = math.sqrt((start_pt[0] - end_pt[0])**2 + (start_pt[1] - end_pt[1])**2)
    
    if dist < dash_length:

        cv2.line(image, start_pt, end_pt, color, thickness)
        return

    num_dashes = int(dist / (dash_length + gap_length))
    
    start_pt = np.array(start_pt, dtype=np.float32)
    end_pt = np.array(end_pt, dtype=np.float32)
    
    dx = (end_pt[0] - start_pt[0]) / dist
    dy = (end_pt[1] - start_pt[1]) / dist
    
    for i in range(num_dashes):

        s_pt = (start_pt[0] + dx * i * (dash_length + gap_length), 
                start_pt[1] + dy * i * (dash_length + gap_length))
        e_pt = (start_pt[0] + dx * (i * (dash_length + gap_length) + dash_length),
                start_pt[1] + dy * (i * (dash_length + gap_length) + dash_length))
        
        cv2.line(image, tuple(np.round(s_pt).astype(int)), tuple(np.round(e_pt).astype(int)), color, thickness)

# Background thread function to continuously fetch the latest GPS data from the smartphone's local HTTP server every 5 seconds
def fetch_gps_data():

    global gps_data
    while True:

        try:

            response = requests.get(GPS_URL, timeout=2)
            if response.status_code == 200:

                with gps_lock:

                    gps_data = response.json()
                    gps_data["timestamp"] = time.time()
        except requests.exceptions.RequestException:

            pass # Silently ignore network errors to keep the thread alive
        
        time.sleep(5)

# Calculates the perspective transform matrix at startup
def calculate_homography_matrix():

    global homography_matrix
    try:

        homography_matrix = cv2.getPerspectiveTransform(PTS_IMAGE, PTS_WORLD)
        print("Homography Matrix calculated successfully.")
    except Exception as e:

        print(f"Failed to calculate Homography matrix: {e}")

# Converts 2D image pixel coordinates (u, v) to 2D real-world coordinates (X, Y in meters) on the ground plane using the calculated Homography matrix
def convert_pixel_to_real_world(u, v):

    if homography_matrix is None:

        return 0, 0
    
    point = np.array([[[u, v]]], dtype="float32")
    real_point = cv2.perspectiveTransform(point, homography_matrix)
    
    x_meters = real_point[0][0][0] 
    y_meters = real_point[0][0][1] 
    
    return x_meters, y_meters

# Converts the calculated real-world meter displacement into new GPS coordinates, using a flat-earth approximation which is highly accurate for short distances 
def add_meters_to_gps(start_lat, start_lon, x_meters, y_meters):

    # 1 degree of latitude is approximately 111,111 meters
    delta_lat = y_meters / 111111.0
    
    # 1 degree of longitude varies depending on the latitude (needs cosine correction)
    delta_lon = x_meters / (111111.0 * math.cos(math.radians(start_lat)))
    
    return start_lat + delta_lat, start_lon + delta_lon

# Model initialization
print("Loading YOLO model...")
model = YOLO('best_YOLO11s-seg.pt') # Load the custom trained model weights
print("Model loaded successfully.")

#Main loop: connects to the MJPEG stream, extracts frames, fixes optical distortion, runs YOLO inference, calculates target distances, and renders the UI
def process_video_stream():

    try:

        print(f"Connecting to video stream: {VIDEO_STREAM_URL}...")
        response = requests.get(VIDEO_STREAM_URL, stream=True, timeout=10)
        response.raise_for_status()
        print("Connected! Waiting for frames...")

        byte_stream = bytes()
        
        # Read the stream in chunks
        for chunk in response.iter_content(chunk_size=4096):

            byte_stream += chunk