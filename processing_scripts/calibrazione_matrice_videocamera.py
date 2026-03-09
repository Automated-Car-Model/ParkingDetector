# Script for intrinsic camera calibration of the ArduCAM Pico4ML using chessboard images
# This process computes the Camera Matrix and Distortion Coefficients needed to undistort frames.

import numpy as np
import cv2
import glob
import sys

# Checkerboard configuration
# Number of inner corners horizontally (number of squares per row minus 1)
CHECKERBOARD_X = 12 
# Number of inner corners vertically (number of squares per column minus 1)
CHECKERBOARD_Y = 9

# Side length of a single printed square in meters (e.g., 0.022 = 2.2 cm)
SQUARE_SIZE = 0.022 

# Termination criteria for the iterative sub-pixel corner refinement algorithm.
# It stops calculating after 30 iterations or when the accuracy reaches 0.001 pixels.
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points (3D coordinates in the real-world space).
# We assume the chessboard lies perfectly flat on the Z=0 plane.
# Coordinates will look like: (0,0,0), (1,0,0), (2,0,0) ... scaled by SQUARE_SIZE.
objp = np.zeros((CHECKERBOARD_X * CHECKERBOARD_Y, 3), np.float32)
objp[:, :2] = np.mgrid[0:CHECKERBOARD_X, 0:CHECKERBOARD_Y].T.reshape(-1, 2) * SQUARE_SIZE

# Arrays to store object points and image points from all the calibration images
objpoints = [] # 3D points in real-world space
imgpoints = [] # 2D points in the image plane (pixels)

# Path to the folder containing the chessboard calibration images.
# Using a relative path so it works out-of-the-box in the cloned GitHub repository.
images = glob.glob('calib_images/*.jpg') 

if not images:

    print("No images found in the 'calib_images/' directory.")
    print("Please create the 'calib_images/' folder and add your chessboard photos.")
    sys.exit()

print(f"Found {len(images)} images for calibration...")

# Loop through all the provided chessboard images
for fname in images:

    img = cv2.imread(fname)
    if img is None:

        print(f"Failed to read image {fname}. Skipping.")
        continue
    
    # Convert image to grayscale (required by the corner detection algorithm)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Find the chessboard inner corners
    ret, corners = cv2.findChessboardCorners(gray, (CHECKERBOARD_X, CHECKERBOARD_Y), None)
    
    # If the corners are successfully found
    if ret == True:

        # Add the 3D object points to the array
        objpoints.append(objp)
        
        # Refine the detected corner coordinates to sub-pixel accuracy for a much better calibration
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        imgpoints.append(corners2)
        
        # Draw the detected corners on the image for visual feedback
        img = cv2.drawChessboardCorners(img, (CHECKERBOARD_X, CHECKERBOARD_Y), corners2, ret)
        
        # Display the image with corners (resized to fit the screen)
        cv2.imshow('Chessboard Detection', cv2.resize(img, (640, 640)))
        cv2.waitKey(500) # Wait 500ms before moving to the next image
    else:

        print(f"Chessboard corners not found in image: {fname}")

cv2.destroyAllWindows()

# Camera calibration calculation
print("\nStarting calibration process...")
if len(objpoints) > 0:
    
    # Perform camera calibration to get the camera matrix and distortion coefficients
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    
    if ret:

        print("Intrinsic calibration completed successfully!")
        print("\n" + "="*70)
        print("\nRESULTS TO COPY INTO THE MAIN SCRIPT")
        print("\n" + "="*70)
        
        # Print Camera Matrix (Focal lengths fx, fy and optical centers cx, cy)
        print("\n# Camera Matrix (Intrinsics):")
        print("CAMERA_MATRIX = np.array(")
        print(mtx)
        print(")")
        
        # Print Distortion Coefficients (k1, k2, p1, p2, k3)
        print("\n# Distortion Coefficients:")
        print("DIST_COEFFS = np.array(")
        print(dist)
        print(")")
        
        # Calculate the Mean Re-projection Error.
        # This evaluates how closely the mathematical model maps the 3D points back to the 2D image.
        mean_error = 0
        for i in range(len(objpoints)):

            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            mean_error += error
            
        print(f"\nMean Re-projection Error (ideally < 1.0): {mean_error / len(objpoints):.4f} pixels")
    else:

        print("CALIBRATION FAILED.")
else:
    
    print("Not enough valid corners were found across the images to perform calibration.")