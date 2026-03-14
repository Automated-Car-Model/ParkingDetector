/**
 * Class containing global constants for the application.
 */
package com.example.camera_server.utility;

public class Constants {

    // HTTP Server Configuration
    /** Port number for the HTTP server */
    public static final int SERVER_PORT = 8080;
    /** Boundary string for the MJPEG stream */
    public static final String MJPEG_BOUNDARY = "Boundary";

    // Camera and Stream Configuration
    /** Width of the video stream in pixels */
    public static final int STREAM_WIDTH = 640;
    /** Height of the video stream in pixels */
    public static final int STREAM_HEIGHT = 480;
    /** JPEG compression quality (0-100) */
    public static final int JPEG_QUALITY = 85;

    // GPS Location Configuration
    /** Minimum time interval between GPS updates in milliseconds */
    public static final long GPS_UPDATE_INTERVAL_MS = 5000; // 5 seconds
    /** Minimum distance change for GPS updates in meters */
    public static final float GPS_UPDATE_DISTANCE_M = 10; // 10 meters

    // UI Strings (Buttons and Status messages)
    public static final String BTN_START_SERVER = "Avvia Server";
    public static final String BTN_STOP_SERVER = "Ferma Server";
    public static final String BTN_START_STREAM = "Avvia Stream";
    public static final String BTN_STOP_STREAM = "Ferma Stream";
    public static final String STATUS_SERVER_INACTIVE = "Server non attivo";
    public static final String STATUS_SERVER_ACTIVE_PREFIX = "Server attivo: http://";
    public static final String STATUS_SERVER_ERROR_PREFIX = "Errore avvio server: ";

}
