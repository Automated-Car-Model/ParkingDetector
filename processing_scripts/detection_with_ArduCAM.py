# Real-time free parking space detection using ArduCAM Pico4ML USB stream, YOLO inference, and PC-based GPS data.

import serial
import numpy as np
import cv2
import time
from ultralytics import YOLO
import math
import geocoder

# Serial & image configuration
PORT = 'COM4'       # Serial port for the Pico4ML (change according to your OS)
BAUDRATE = 115200 
WIDTH = 80          # Width of the frame sent by the Pico (Grayscale)
HEIGHT = 160        # Height of the frame sent by the Pico (Grayscale)
YOLO_SIZE = 640     # Target resolution for YOLO inference
SYNC_PATTERN = b'\xAA\xBB\xCC\xDD'  # Synchronization pattern indicating the start of a new frame
FRAME_SIZE = WIDTH * HEIGHT  # Total number of bytes for a complete frame (1 byte/pixel)

model = None
homography_matrix = None

# Intrinsic calibration parameters
# Camera Matrix from calibrazione_matrice_videocamera.py
CAMERA_MATRIX = np.array(
[[1.16193344e+03, 0.00000000e+00, 2.78344527e+02],
 [0.00000000e+00, 1.15234040e+03, 4.09280837e+02],
 [0.00000000e+00, 0.00000000e+00, 1.00000000e+00]]
)

# Distortion coefficients from calibrazione_matrice_videocamera.py
DIST_COEFFS = np.array(
[[ 1.48311176e-01, -3.97728971e+00, -2.35651927e-02, -8.95685857e-03,
   5.07527563e+01]]
)

# Homography calibration parameters
# 2D Image Points (Pixels) from calibrazione_matrice_omografica.py
PTS_IMAGE = np.array([
    [180, 200],  # Point 1 (Top-Left)
    [460, 200],  # Point 2 (Top-Right)
    [580, 500],  # Point 3 (Bottom-Right)
    [60,  500]   # Point 4 (Bottom-Left)
], dtype="float32")

# Real-world ground coordinates corresponding to the image points (in meters)
PTS_WORLD = np.array([
    [0.0, 1.0],  # Point 1: 0m lateral, 1m forward
    [2.0, 1.0],  # Point 2: 2m lateral, 1m forward
    [2.0, 4.0],  # Point 3: 2m lateral, 4m forward
    [0.0, 4.0]   # Point 4: 0m lateral, 4m forward
], dtype="float32")

# Helper function to draw a dashed trajectory line from the vehicle to the target
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

# Calculates the perspective transform matrix for pixel -> meters conversion
def calculate_homography_matrix():

    global homography_matrix
    try:

        homography_matrix = cv2.getPerspectiveTransform(PTS_IMAGE, PTS_WORLD)
        print("Homography Matrix calculated successfully.")
    except Exception as e:

        print(f"Failed to calculate Homography matrix. {e}")

# Initializes and loads the pre-trained YOLO model
def initialize_model():
    
    global model
    try:

        model = YOLO('best_YOLO11s-seg.pt')
        print("YOLO Model loaded successfully.")
        return model
    except Exception as e:

        print(f"Failed to load YOLO model: {e}")
        return None

# Retrieves the approximate GPS location of the PC using its IP address (fallback method since the Pico4ML does not have a built-in GPS module)
def get_pc_location():
    
    try:

        g = geocoder.ip('me') 
        if g.ok and g.lat:

            return {"latitude": g.lat, "longitude": g.lng}
    except:

        pass
    return {"latitude": 0.0, "longitude": 0.0}

# Converts pixel coordinates (u,v) to real-world coordinates (X,Y) in meters on the ground plane using the Homography matrix
def convert_pixel_to_real_world(u, v):
    
    if homography_matrix is None:

        return 0, 0
    
    # Format point for perspectiveTransform
    point = np.array([[[u, v]]], dtype="float32")
    
    # Apply transformation
    real_point = cv2.perspectiveTransform(point, homography_matrix)
    
    # Extract calculated coordinates
    x_meters = real_point[0][0][0] 
    y_meters = real_point[0][0][1] 
    
    return x_meters, y_meters

# Converts displacements in meters to new GPS coordinates (assuming Y=North/South, X=East/West flat-earth approximation)
def add_meters_to_gps(start_lat, start_lon, x_meters, y_meters):
    
    # 1 degree of Latitude is approximately 111,111 meters
    delta_lat = y_meters / 111111.0
    
    # 1 degree of Longitude varies with latitude (cosine correction needed)
    delta_lon = x_meters / (111111.0 * math.cos(math.radians(start_lat)))
    
    return start_lat + delta_lat, start_lon + delta_lon

# Processes a single frame: applies undistortion, runs YOLO inference, calculates distances and GPS targets, and renders the UI.
def process_frame_and_detect(img_matrix_gs, yolo_model, current_gps_data):
    
    # Convert Grayscale image to 3-channel BGR (Required by YOLO)
    frame_bgr = cv2.cvtColor(img_matrix_gs, cv2.COLOR_GRAY2BGR)
    
    # Lens distortion correction and cropping
    h_orig, w_orig = frame_bgr.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(CAMERA_MATRIX, DIST_COEFFS, (w_orig, h_orig), 1, (w_orig, h_orig))
    undistorted_frame = cv2.undistort(frame_bgr, CAMERA_MATRIX, DIST_COEFFS, None, new_camera_matrix)
    x_roi, y_roi, w_roi, h_roi = roi
    cropped_undistorted_frame = undistorted_frame[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
    
    # Resize to target size for YOLO
    frame_yolo = cv2.resize(cropped_undistorted_frame, (YOLO_SIZE, YOLO_SIZE), interpolation=cv2.INTER_CUBIC)
    
    # YOLO Inference
    results = yolo_model(frame_yolo, verbose=False)
    processed_frame = results[0].plot()

    # Extract centroids, convert to real-world coordinates, and calculate target distance & GPS
    centroidi_data = [] 
    pc_lat = current_gps_data.get('latitude', 0.0)
    pc_lon = current_gps_data.get('longitude', 0.0)

    for result in results[0].boxes:

        x1, y1, x2, y2 = result.xyxy[0].cpu().numpy().astype(int)
        cx = int((x1 + x2) / 2)
        cy_ground = int(y2) 
        cy_center = int((y1 + y2) / 2)

        # Pixel -> Meters -> Target GPS
        real_x, real_y = convert_pixel_to_real_world(cx, cy_ground)
        dist_meters = math.sqrt(real_x**2 + real_y**2)
        target_lat, target_lon = add_meters_to_gps(pc_lat, pc_lon, real_x, real_y)
        
        # Save data for rendering
        centroidi_data.append({
            'center': (cx, cy_center),
            'ground_px': (cx, cy_ground),
            'dist': dist_meters,
            'coords': (target_lat, target_lon),
            'real_xy': (real_x, real_y)
        })

    # Find the closest target
    idx_min = -1
    if centroidi_data:

        distanze = [item['dist'] for item in centroidi_data]
        idx_min = distanze.index(min(distanze))

    # Draw UI elements on the frame 
    print(f"\n--- Frame Processed | PC GPS: ({pc_lat:.5f}, {pc_lon:.5f}) ---")

    # Vehicle starting point (Bottom-Center of the image)
    vehicle_start = (YOLO_SIZE // 2, YOLO_SIZE - 1) 
    font_generic = cv2.FONT_HERSHEY_SIMPLEX

    for i, item in enumerate(centroidi_data):

        cx, cy = item['center']
        dist = item['dist']
        lat, lon = item['coords']
        
        dist_str = f"{dist:.2f}m"

        if i == idx_min:

            # Highlight Target in RED
            color_red = (0, 0, 255) 
            
            # Solid red circle on target
            cv2.circle(processed_frame, (cx, cy), 8, color_red, -1)
            
            # Dashed trajectory line
            draw_dashed_line(processed_frame, vehicle_start, (cx, cy), color_red, thickness=2, dash_length=15, gap_length=10)

            # Target GPS Label
            target_label = f"TARGET ({lat:.5f} ; {lon:.5f})"
            font_scale_label = 0.5
            thickness_label = 1
            
            # Calculate text size to position the label correctly
            (label_w, label_h), baseline_label = cv2.getTextSize(target_label, font_generic, font_scale_label, thickness_label)
            
            # Position the red label above the target circle 
            label_pos = (cx - (label_w // 2), cy - label_h - baseline_label - 10)
            cv2.putText(processed_frame, target_label, label_pos, font_generic, font_scale_label, color_red, thickness_label)

            # Draw distance in a white rectangle next to the trajectory
            font_scale_text = 0.6
            color_text_black = (0, 0, 0)
            color_bg_white = (255, 255, 255)
            thickness_text = 1
            
            # Average position for text along the trajectory
            mid_x = (vehicle_start[0] + cx) // 2
            mid_y = (vehicle_start[1] + cy) // 2
            text_base_pos = (mid_x + 15, mid_y - 10) # Offset for visual alignment

            (t_width, t_height), baseline = cv2.getTextSize(dist_str, font_generic, font_scale_text, thickness_text)
            
            # Define coordinates for the background rectangle (with padding)
            rect_start = (text_base_pos[0] - 4, text_base_pos[1] - t_height - 4)
            rect_end = (text_base_pos[0] + t_width + 4, text_base_pos[1] + baseline + 4)
            
            # Draw filled white rectangle
            cv2.rectangle(processed_frame, rect_start, rect_end, color_bg_white, cv2.FILLED)
            # Place black text on top of the white rectangle
            cv2.putText(processed_frame, dist_str, text_base_pos, font_generic, font_scale_text, color_text_black, thickness_text)

            # Print target info to terminal
            print(f"[TARGET] Distance: {dist:.2f}m -> GPS: ({lat:.5f}, {lon:.5f})")

        else:

            # Highlight other available slots in GREEN
            color_other = (0, 255, 0)
            cv2.circle(processed_frame, (cx, cy), 5, color_other, -1) 
    
    return processed_frame

# Handles the serial connection, reads frames, and applies processing
def run_stream(yolo_model, initial_gps_data):

    try:

        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        print(f"Connected to {PORT}. Starting YOLO inference stream...")
    except Exception as e:

        print(f"Failed to open serial port {PORT}: {e}")
        return

    buffer = b''
    
    try:

        while True:

            # Read incoming bytes from the serial buffer
            if ser.in_waiting > 0:

                buffer += ser.read(ser.in_waiting)

            # Synchronization: look for the start-of-frame pattern
            if SYNC_PATTERN in buffer:

                split_index = buffer.find(SYNC_PATTERN)
                
                # Check if enough bytes are received for a full frame
                if len(buffer) >= split_index + 4 + FRAME_SIZE:
                    
                    start_data = split_index + 4
                    img_raw = buffer[start_data : start_data + FRAME_SIZE]
                    buffer = buffer[start_data + FRAME_SIZE:]

                    # Decode raw bytes to numpy array
                    img_array = np.frombuffer(img_raw, dtype=np.uint8)
                    img_matrix_gs = img_array.reshape((HEIGHT, WIDTH))
                    
                    # Process frame (YOLO + Georeferencing)
                    processed_frame = process_frame_and_detect(img_matrix_gs, yolo_model, initial_gps_data)
                    
                    # Display the final frame
                    cv2.imshow('YOLO + Georeferencing (Foto-Style)', processed_frame)
                    
            # Exit 
            if cv2.waitKey(1) & 0xFF == ord('q'):

                print("Exit requested by user.")
                break

    except Exception as e:

        print(f"Error during the streaming loop: {e}")
    finally:

        print("Closing serial port and windows.")
        if 'ser' in locals() and ser.is_open:

            ser.close()
        cv2.destroyAllWindows()


def main():
    
    # Calculate Homography Matrix at startup
    calculate_homography_matrix()
    
    # Load YOLO model
    yolo_model = initialize_model()
    
    if yolo_model:

        # Get PC GPS location
        initial_gps_data = get_pc_location()

        # Start streaming and inference
        run_stream(yolo_model, initial_gps_data)
    else:

        print("Failed to start the system: YOLO model is missing.")


if __name__ == "__main__":

    main()