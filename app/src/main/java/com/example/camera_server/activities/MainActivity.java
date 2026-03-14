/**
 * Main activity of the application.
 * This activity manages the user interface, handles permissions,
 * starts/stops the HTTP server, and manages the camera and GPS lifecycle.
 */
package com.example.camera_server.activities;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.text.format.Formatter;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.example.camera_server.R;
import com.example.camera_server.managers.HttpServerService;
import com.example.camera_server.managers.StreamManager;
import com.example.camera_server.utility.Constants;
import com.google.common.util.concurrent.ListenableFuture;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity implements LocationListener {

    private static final int PERMISSION_REQUEST_CODE = 101;
    
    // Managers
    private StreamManager streamManager;
    private HttpServerService httpServer;
    private ExecutorService cameraExecutor;
    private LocationManager locationManager;
    
    // UI Elements
    private TextView tvStatus;
    private Button btnServerToggle;
    private Button btnStreamToggle;
    private PreviewView previewView;
    
    // State flags
    private boolean isServerRunning = false;
    private boolean isStreaming = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Initialize UI components
        tvStatus = findViewById(R.id.tvStatus);
        btnServerToggle = findViewById(R.id.btnServerToggle);
        btnStreamToggle = findViewById(R.id.btnStreamToggle);
        previewView = findViewById(R.id.previewView);

        // Initialize managers and executors
        streamManager = new StreamManager();
        cameraExecutor = Executors.newSingleThreadExecutor();
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);

        // Request necessary permissions for Camera and GPS
        checkAndRequestPermissions();

        // Stream button is disabled until the server starts
        btnStreamToggle.setEnabled(false);

        // Server toggle button logic
        btnServerToggle.setOnClickListener(v -> {

            if (isServerRunning) {

                stopServer();

            } else {

                startServer();

            }

        });

        // Stream toggle button logic
        btnStreamToggle.setOnClickListener(v -> {

            if (isStreaming) {

                stopStreaming();

            } else {

                startStreaming();

            }

        });

    }

    /**
     * Checks if the required permissions (Camera and Location) are granted.
     * If not, it requests them from the user.
     */
    private void checkAndRequestPermissions() {

        String[] permissions = {Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION};

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(this, permissions, PERMISSION_REQUEST_CODE);

        }

    }

    /**
     * Starts the HTTP server on the predefined port.
     * Updates the UI to show the server's IP address.
     */
    @SuppressLint("SetTextI18n")
    private void startServer() {

        try {

            httpServer = new HttpServerService(Constants.SERVER_PORT, streamManager);
            String ip = getLocalIpAddress();
            tvStatus.setText(Constants.STATUS_SERVER_ACTIVE_PREFIX + ip + ":" + Constants.SERVER_PORT + "/");
            btnServerToggle.setText(Constants.BTN_STOP_SERVER);
            btnStreamToggle.setEnabled(true);
            isServerRunning = true;

        } catch (IOException e) {

            e.printStackTrace();
            tvStatus.setText(Constants.STATUS_SERVER_ERROR_PREFIX + e.getMessage());

        }

    }

    /**
     * Stops the HTTP server and the video stream if it's running.
     * Resets the UI components to their initial state.
     */
    private void stopServer() {

        if (isStreaming) {

            stopStreaming();

        }

        if (httpServer != null) {

            httpServer.stop();
            httpServer = null;

        }

        tvStatus.setText(Constants.STATUS_SERVER_INACTIVE);
        btnServerToggle.setText(Constants.BTN_START_SERVER);
        btnStreamToggle.setEnabled(false);
        isServerRunning = false;

    }

    /**
     * Starts the video stream and GPS tracking.
     */
    private void startStreaming() {

        streamManager.startStream();
        startCamera();
        startGps();
        btnStreamToggle.setText(Constants.BTN_STOP_STREAM);
        isStreaming = true;

    }

    /**
     * Stops the video stream and GPS tracking.
     */
    private void stopStreaming() {

        streamManager.stopStream();
        stopCamera();
        stopGps();
        btnStreamToggle.setText(Constants.BTN_START_STREAM);
        isStreaming = false;

    }

    /**
     * Initializes and starts GPS location updates using the LocationManager.
     */
    private void startGps() {

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {

            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, Constants.GPS_UPDATE_INTERVAL_MS, Constants.GPS_UPDATE_DISTANCE_M, this);

        }

    }

    /**
     * Stops receiving GPS location updates.
     */
    private void stopGps() {

        locationManager.removeUpdates(this);

    }

    /**
     * Callback for location changes. Updates the stream manager with new coordinates.
     */
    @Override
    public void onLocationChanged(@NonNull Location location) {

        streamManager.updateGpsCoordinates(location.getLatitude(), location.getLongitude());

    }

    /**
     * Configures and binds the CameraX use cases (Preview and ImageAnalysis).
     */
    private void startCamera() {

        ListenableFuture<ProcessCameraProvider> cameraProviderFuture = ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {

            try {

                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();

                // Setup the preview use case
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(previewView.getSurfaceProvider());

                // Setup the image analysis use case
                ImageAnalysis imageAnalysis = new ImageAnalysis.Builder()
                        .setTargetResolution(new android.util.Size(Constants.STREAM_WIDTH, Constants.STREAM_HEIGHT))
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                        .build();

                imageAnalysis.setAnalyzer(cameraExecutor, this::analyzeImage);

                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

                // Unbind any previous use cases and bind the new ones
                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis);

            } catch (ExecutionException | InterruptedException e) {

                e.printStackTrace();

            }

        }, ContextCompat.getMainExecutor(this));

    }

    /**
     * Unbinds all CameraX use cases to stop the camera.
     */
    private void stopCamera() {

        ListenableFuture<ProcessCameraProvider> cameraProviderFuture = ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {

            try {

                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();
                cameraProvider.unbindAll();

            } catch (ExecutionException | InterruptedException e) {

                e.printStackTrace();

            }

        }, ContextCompat.getMainExecutor(this));

    }

    /**
     * Analyzes each frame from the camera, converts it to JPEG, and pushes it to the stream manager.
     * Handles frame rotation if necessary.
     *
     * @param image The ImageProxy from CameraX analysis.
     */
    private void analyzeImage(@NonNull ImageProxy image) {

        try {

            if (image.getFormat() == ImageFormat.YUV_420_888) {

                // Convert YUV_420_888 to NV21 (compatible with YuvImage)
                byte[] nv21Data = YUV_420_888_to_NV21(image);

                // Compress NV21 to JPEG
                YuvImage yuvImage = new YuvImage(nv21Data, ImageFormat.NV21, image.getWidth(), image.getHeight(), null);
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                yuvImage.compressToJpeg(new Rect(0, 0, image.getWidth(), image.getHeight()), Constants.JPEG_QUALITY, out);
                byte[] jpegData = out.toByteArray();

                int rotationDegrees = image.getImageInfo().getRotationDegrees();
                byte[] finalJpegData;

                if (rotationDegrees == 0) {

                    finalJpegData = jpegData;

                } else {

                    // Rotate the image if required by device orientation
                    Bitmap bitmap = BitmapFactory.decodeByteArray(jpegData, 0, jpegData.length);
                    Matrix matrix = new Matrix();
                    matrix.postRotate(rotationDegrees);
                    Bitmap rotatedBitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
                    bitmap.recycle();

                    ByteArrayOutputStream rotatedOut = new ByteArrayOutputStream();
                    rotatedBitmap.compress(Bitmap.CompressFormat.JPEG, Constants.JPEG_QUALITY, rotatedOut);
                    rotatedBitmap.recycle();
                    finalJpegData = rotatedOut.toByteArray();

                }

                // Push the frame to the stream manager's buffer
                streamManager.pushFrame(finalJpegData);

            }

        } finally {

            image.close();

        }

    }

    /**
     * Helper method to convert YUV_420_888 ImageProxy to NV21 byte array.
     *
     * @param image The input ImageProxy.
     * @return The resulting NV21 byte array.
     */
    private byte[] YUV_420_888_to_NV21(ImageProxy image) {

        int width = image.getWidth();
        int height = image.getHeight();
        
        byte[] nv21 = new byte[width * height * 3 / 2];

        ByteBuffer yBuffer = image.getPlanes()[0].getBuffer();
        int yRowStride = image.getPlanes()[0].getRowStride();

        ByteBuffer uBuffer = image.getPlanes()[1].getBuffer();
        int uRowStride = image.getPlanes()[1].getRowStride();
        int uPixelStride = image.getPlanes()[1].getPixelStride();

        ByteBuffer vBuffer = image.getPlanes()[2].getBuffer();
        int vRowStride = image.getPlanes()[2].getRowStride();
        int vPixelStride = image.getPlanes()[2].getPixelStride();

        // Copy Y plane (Luma)
        int yDestPos = 0;
        if (yRowStride == width) {

            yBuffer.get(nv21, 0, yBuffer.remaining());

        } else {

            for (int row = 0; row < height; row++) {

                yBuffer.position(row * yRowStride);
                yBuffer.get(nv21, yDestPos, width);
                yDestPos += width;

            }

        }

        // Copy UV planes (Chroma)
        int uvDestPos = width * height;
        for (int row = 0; row < height / 2; row++) {

            for (int col = 0; col < width / 2; col++) {

                int vSrcPos = row * vRowStride + col * vPixelStride;
                int uSrcPos = row * uRowStride + col * uPixelStride;
                
                if (uvDestPos < nv21.length - 1) {

                    // NV21 stores V then U
                    nv21[uvDestPos++] = vBuffer.get(vSrcPos);
                    nv21[uvDestPos++] = uBuffer.get(uSrcPos);

                }

            }

        }

        return nv21;

    }

    /**
     * Gets the local IP address of the device on the Wi-Fi network.
     *
     * @return A string representation of the IP address.
     */
    private String getLocalIpAddress() {

        WifiManager wm = (WifiManager) getApplicationContext().getSystemService(WIFI_SERVICE);
        return Formatter.formatIpAddress(wm.getConnectionInfo().getIpAddress());

    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Ensure the server is stopped when the activity is destroyed
        if (isServerRunning) {

            stopServer();

        }

        cameraExecutor.shutdown();

    }

}