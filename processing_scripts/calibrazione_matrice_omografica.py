# Script to calibrate the Homography matrix (Pixel to Meters conversion)
# This allows the system to map 2D image coordinates to 3D real-world coordinates on the ground plane.

import cv2
import numpy as np
import sys

# Configuration
# Path to a sample frame captured from the camera in its final mounted position
IMAGE_PATH = 'calib_images/homography_sample.png'
NUM_POINTS = 4
clicked_points = []

# Real-world ground points in meters.
# These must exactly correspond to the physical measurements of the 4 points you will click on the image.
# Order is strictly: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
PTS_WORLD = np.array([
    [0.0, 1.0],  # Top-Left: 1 meter forward, 0 meters lateral
    [2.0, 1.0],  # Top-Right: 1 meter forward, 2 meters lateral
    [2.0, 4.0],  # Bottom-Right: 4 meters forward, 2 meters lateral
    [0.0, 4.0]   # Bottom-Left: 4 meters forward, 0 meters lateral
], dtype="float32")

# Mouse callback function
def mouse_callback(event, x, y, flags, param):

    """
    Captures the (x, y) pixel coordinates when the user left-clicks on the image.
    Draws a red circle and a number to visually track the selected points.
    """

    global clicked_points
    
    if event == cv2.EVENT_LBUTTONDOWN:

        if len(clicked_points) < NUM_POINTS:

            clicked_points.append((x, y))
            print(f"Point {len(clicked_points)} selected: ({x}, {y})")
            
            # Draw a solid red circle at the clicked position
            cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
            # Draw the point number next to the circle
            cv2.putText(img, str(len(clicked_points)), (x + 10, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("Homography Calibration", img)

        # Once all 4 points have been selected, calculate the matrix and exit
        if len(clicked_points) == NUM_POINTS:

            calculate_and_print_results()
            sys.exit()

# Homography calculation
def calculate_and_print_results():

    """
    Calculates the Perspective Transformation (Homography) matrix using the 4 selected pixel points
    and the 4 known real-world points. Prints the formatted arrays ready to be used in the main scripts.
    """

    pts_image_np = np.array(clicked_points, dtype="float32")
    
    try:

        # Calculate the 3x3 Homography matrix that maps image pixels to world coordinates
        h_matrix = cv2.getPerspectiveTransform(pts_image_np, PTS_WORLD)
        
        print("\n" + "=" * 70)
        print("PIXEL POINTS SELECTED AND HOMOGRAPHY MATRIX CALCULATED SUCCESSFULLY!")
        print("COPY AND PASTE THESE RESULTS INTO THE CONFIGURATION SECTION OF THE MAIN SCRIPT.")
        print("="*70)
        
    except cv2.error as e:

        print("\n" + "=" * 70)
        print("Unable to calculate the Perspective Transform matrix.")
        print("=" * 70)
        return

    # Print the formatted output to easily copy-paste into main.py
    print("\n# 1. IMAGE POINTS (Pixels)")
    print("PTS_IMAGE = np.array([")
    for i, (x, y) in enumerate(clicked_points):

        print(f"    [{x}.0, {y}.0],  # Point {i + 1}")
    print("], dtype=\"float32\")")
    
    print("\n# 2. WORLD POINTS (Meters)")
    # Format the PTS_WORLD array string to look clean and readable
    world_str = str(PTS_WORLD.tolist()).replace('], ', '],\n    ')
    print(f"PTS_WORLD = np.array({world_str}, dtype=\"float32\")")
    
# Main execution
try:

    # Load the calibration image
    img = cv2.imread(IMAGE_PATH)

    if img is None:

        print(f"Unable to load the image from '{IMAGE_PATH}'.")
        print("Make sure the file exists and the path is correct.")
        sys.exit()

    # Ensure the image matches the standard YOLO input size used in the project (640x640)
    # This guarantees the pixel coordinates clicked here match the ones during real-time inference
    if img.shape[0] != 640 or img.shape[1] != 640:

        img = cv2.resize(img, (640, 640))
        print("Image automatically resized to 640x640 pixels.")

    # Create the window and bind the mouse callback function
    cv2.imshow("Homography Calibration", img)
    cv2.setMouseCallback("Homography Calibration", mouse_callback)

    print("\nPlease click on the 4 ground points in the exact following order:")
    print("1. Top-Left  |  2. Top-Right  |  3. Bottom-Right  |  4. Bottom-Left")
    
    # Wait indefinitely until the user clicks all 4 points (handled by the callback)
    cv2.waitKey(0)

except Exception as e:

    print(f"An error occurred during execution: {e}")
finally:

    # Ensure all OpenCV windows are closed properly upon exit
    cv2.destroyAllWindows()