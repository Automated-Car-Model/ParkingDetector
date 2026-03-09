# Real-Time Free Parking Space Detection via In-Vehicle Camera

<div align="center">
  <img src="media/example.gif" alt="Parking Detection Demo" width="700"/>
</div>

<br>

This repository contains the code and resources for an Edge AI system designed to detect available parking spaces in real-time using a vehicle-mounted camera. 

The project aims to tackle the "cruising for parking" phenomenon, providing a scalable, low-cost solution to reduce urban traffic congestion, polluting emissions, and driver stress. This work was developed as a Bachelor's Degree Thesis in Electronic and Information Technology Engineering at the University of Genoa.

---

## Repository Structure

The project is divided into three main components:

1. **`Android_App/`**: Source code for an Android application that acts as a local HTTP server, streaming the smartphone's camera feed (MJPEG) and GPS data (JSON).
2. **`ArduCAM_Firmware/`**: C/C++ Firmware for the ArduCAM Pico4ML Dev Kit. It captures grayscale frames and outputs them over USB Serial using a dual-core Raspberry Pi RP2040 setup.
3. **`Processing_Scripts/`**: Python scripts for the Host Computer. Includes camera calibration tools, perspective transformation, and the main YOLO11 inference scripts.
   * *`weights/`*: Contains the pre-trained YOLO11s model (`.pt`).
   * *`calib_images/`*: Chessboard images for intrinsic camera calibration.
   * *`dataset_sample/`*: A small sample of the custom dataset used for training. *(Note: The full dataset of 6000+ images is available externally on Roboflow: [Parking Slots Segmentation Dataset](https://app.roboflow.com/riccardo-xeg03/parking-slots-segmentation-gjrcw/15))*.

---

## System Architecture

* **Acquisition Unit:** Captures the front-facing video stream (Smartphone or ArduCAM).
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
```bash
git clone [https://github.com/Automated-Car-Model/ParkingDetector.git](https://github.com/Automated-Car-Model/ParkingDetector.git)

cd ParkingDetector


