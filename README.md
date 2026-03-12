# Real-Time Free Parking Space Detection via In-Vehicle Camera

<div align="center">
  <img src="media/example.gif" alt="Parking Detection Demo" width="700"/>
</div>

<br>

This repository contains the code and resources for an Edge AI system designed to detect available parking spaces in real-time using a vehicle-mounted camera. 

The project aims to tackle the "cruising for parking" phenomenon, providing a scalable, low-cost solution to reduce urban traffic congestion, polluting emissions, and driver stress. This work was developed as a Bachelor's Degree Thesis in Electronic and Information Technology Engineering at the University of Genoa.

---

## Repository Structure

    ParkingDetector/
    ├── .gitignore                              
    ├── README.md                               
    ├── Android_app/                            (Acquisition Unit with smartphone)
    │   └── ... (Source code, Gradle files, etc.)
    ├── ArduCAM_firmware/                       (Acquisition Unit with ArduCAM)
    │   ├── lib/
    │   ├── main.c
    │   ├── image.pio
    │   └── CMakeLists.txt
    ├── processing_scripts/                     (Python Scripts (Processing Unit))
    │   ├── calib_images/                       (Images for intrinsic calibration)
    │   │   ├── arducam/                        (Chessboard images taken with ArduCAM)
    │   │   └── smartphone/                     (Chessboard images taken with Smartphone)
    │   ├── weights/                            (YOLO11s pre-trained model weights)
    │   ├── homography_matrix_calibration.py
    │   ├── camera_matrix_calibration.py.py
    │   ├── detection_with_smartphone.py
    │   ├── detection_with_arducam.py
    │   └── requirements.txt
    └── media/                                  (Assets for documentation)
        └── example.gif

*(Note: The full dataset of 6000+ images is available externally on Roboflow: [Parking Slots Segmentation Dataset](https://app.roboflow.com/riccardo-xeg03/parking-slots-segmentation-gjrcw/15))*.

---

## System Architecture

The system operates on a distributed architecture divided into two main modules:

* **Acquisition Unit:** Captures the front-facing video stream. It can be implemented using either a custom Android application on a smartphone (acting as a local HTTP server) or an ArduCAM Pico4ML Dev Kit (transmitting raw frames via USB serial).
* **Processing Unit:** A dedicated host computer that receives the frames, runs the machine learning inference via a Python script, and processes spatial coordinates to calculate the distance and GPS position of the closest available parking slot.

---

## Model and Dataset

* **Machine Learning Model:** The system uses **YOLO11s** (Small) for instance segmentation, selected for its optimal balance between high detection accuracy and low computational latency.
* **Custom Dataset:** Over 6,000 images were collected and annotated using Roboflow. The dataset ensures model robustness by including indoor/outdoor environments, various times of day (including night), and multiple camera angles.

---

## Data Processing Pipeline

1. **Pre-processing:** Frames are converted to BGR, corrected for optical lens distortion using intrinsic calibration parameters, and resized to match YOLO's input (640x640).
2. **Inference:** YOLO11s detects free parking slots and outputs segmentation masks.
3. **Centroid Calculation:** The geometric centroid of each parking space is calculated in pixel coordinates.
4. **Spatial Conversion:** 2D pixel coordinates are converted into 3D real-world geographic coordinates via perspective transformation (Homography matrix).
5. **Target Selection:** The system calculates the distance to all detected slots and highlights the closest one ("Target"), displaying its distance and GPS coordinates.

---

## Installation and Setup

Clone the repository to your local machine:

    git clone https://github.com/Automated-Car-Model/ParkingDetector.git
    cd ParkingDetector

### 1. Host Computer (Python Processing)
Ensure you have **Python 3.8+** installed. Use a virtual environment:

    cd processing_scripts
    python -m venv venv
    source venv\Scripts\activate
    pip install -r requirements.txt

### 2. Android Smartphone (Acquisition Option A)
1. Open the Android_app folder in **Android Studio**.
2. Connect your Android device (USB Debugging enabled).
3. Build and run the app (Requires API Level 31+).

### 3. ArduCAM Pico4ML Dev Kit (Acquisition Option B)
1. Install the **Raspberry Pi Pico SDK**.
2. Build the firmware:

    cd ArduCAM_firmware
    mkdir build && cd build
    cmake ..
    make

3. Connect the ArduCAM while holding the **BOOTSEL** button and drag the .uf2 file into the RPI-RP2 drive.

---

## Usage Instructions

### Step 1: Calibration
Before running the inference, update the calibration matrices in the main scripts:
1. **Intrinsic Calibration:** Run `camera_matrix_calibration.py` (point it to either the `smartphone` or `arducam` image folder) to calculate `CAMERA_MATRIX` and `DIST_COEFFS`.
2. **Homography Calibration:** Run `homography_matrix_calibration.py` and click on 4 known ground points to map pixels to meters.

### Step 2: Running Inference

**If using the Android App:**
1. Connect both devices to the same Wi-Fi. Then start the Server and Stream on the app.
2. Ensure `BASE_URL` in `detection_with_smartphone.py` matches the app's IP.
3. Run: `detection_with_smartphone.py`

**If using the ArduCAM:**
1. Connect the ArduCAM via USB.
2. Update the `PORT` variable in `detection_with_arducam.py` (e.g., COM4 or /dev/ttyACM0).
3. Run: `python detection_with_arducam.py`

---

## Credits

* **Author:** Riccardo Divoto
* **Supervisors:** Prof. Riccardo Berta, Prof. Luca Lazzaroni
* **Co-Supervisor:** Dott. Alessandro Pighetti
* **Institution:** Università di Genova (University of Genoa)
* **Academic Year:** 2024-2025







