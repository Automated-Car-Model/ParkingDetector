/**
 * Manager class responsible for handling the video stream buffer and GPS data.
 * It provides methods to push new frames and retrieve them via HTTP responses.
 */
package com.example.camera_server.managers;

import com.example.camera_server.utility.Constants;
import fi.iki.elonen.NanoHTTPD;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.LinkedBlockingQueue;

public class StreamManager {

    /** Maximum number of frames to keep in the buffer to prevent memory issues */
    private static final int MAX_BUFFERED_FRAMES = 5;
    /** Buffer to store encoded JPEG frames */
    private final LinkedBlockingQueue<byte[]> frameBuffer = new LinkedBlockingQueue<>(MAX_BUFFERED_FRAMES);
    /** Flag to indicate if streaming is currently active */
    private volatile boolean isStreaming = false;

    // GPS Coordinates
    private volatile double latitude = 0.0;
    private volatile double longitude = 0.0;

    /**
     * Starts the streaming process. Clears any existing frames in the buffer.
     */
    public void startStream() {

        frameBuffer.clear();
        isStreaming = true;
        System.out.println("Stream started");

    }

    /**
     * Stops the streaming process and clears the buffer.
     */
    public void stopStream() {

        isStreaming = false;
        frameBuffer.clear();
        System.out.println("Stream stopped");

    }

    /**
     * Adds a new JPEG frame to the buffer. If the buffer is full, the oldest frame is discarded.
     *
     * @param jpegData The byte array containing the JPEG image data.
     */
    public void pushFrame(byte[] jpegData) {

        if (!isStreaming || jpegData == null) return;

        if (frameBuffer.size() >= MAX_BUFFERED_FRAMES) {

            frameBuffer.poll(); // Discard the oldest frame if the buffer is full

        }

        frameBuffer.offer(jpegData);

    }

    /**
     * Updates the current GPS coordinates stored in the manager.
     *
     * @param lat The new latitude.
     * @param lon The new longitude.
     */
    public void updateGpsCoordinates(double lat, double lon) {

        this.latitude = lat;
        this.longitude = lon;

    }

    /**
     * Returns an HTTP response containing the current GPS coordinates in JSON format.
     *
     * @return A NanoHTTPD Response object with JSON data.
     */
    public NanoHTTPD.Response getGpsResponse() {

        try {

            JSONObject json = new JSONObject();
            json.put("latitude", this.latitude);
            json.put("longitude", this.longitude);
            return NanoHTTPD.newFixedLengthResponse(NanoHTTPD.Response.Status.OK, "application/json", json.toString());

        } catch (JSONException e) {

            return NanoHTTPD.newFixedLengthResponse(NanoHTTPD.Response.Status.INTERNAL_ERROR, "text/plain", "JSON Error");

        }

    }

    /**
     * Returns an HTTP response for the MJPEG stream.
     * This method creates an InputStream that waits for and retrieves frames from the buffer.
     *
     * @return A NanoHTTPD Response object configured for MJPEG streaming.
     */
    public NanoHTTPD.Response getStreamResponse() {

        if (!isStreaming) {

            return NanoHTTPD.newFixedLengthResponse(NanoHTTPD.Response.Status.BAD_REQUEST, "text/plain", "Stream not active");

        }

        InputStream stream = new InputStream() {

            private byte[] currentChunk = null;
            private int currentChunkPosition = 0;

            @Override
            public int read() throws IOException {

                // Not used in this implementation as read(byte[], int, int) is preferred
                return -1;

            }

            @Override
            public int read(byte[] b, int off, int len) throws IOException {

                if (currentChunk == null || currentChunkPosition >= currentChunk.length) {

                    try {

                        // Wait for a new frame from the buffer
                        byte[] frame = frameBuffer.take();

                        // Construct the MJPEG part header
                        String header = "--" + Constants.MJPEG_BOUNDARY + "\r\n" +
                                "Content-Type: image/jpeg\r\n" +
                                "Content-Length: " + frame.length + "\r\n\r\n";
                        byte[] headerBytes = header.getBytes();
                        byte[] footer = "\r\n".getBytes();

                        // Combine header, frame, and footer into one chunk
                        currentChunk = concat(headerBytes, frame, footer);
                        currentChunkPosition = 0;

                    } catch (InterruptedException e) {

                        throw new IOException("Stream interrupted", e);

                    }

                }

                // Copy the chunk data into the output buffer
                int bytesToRead = Math.min(len, currentChunk.length - currentChunkPosition);
                System.arraycopy(currentChunk, currentChunkPosition, b, off, bytesToRead);
                currentChunkPosition += bytesToRead;

                return bytesToRead;

            }

        };

        return NanoHTTPD.newChunkedResponse(NanoHTTPD.Response.Status.OK, "multipart/x-mixed-replace; boundary=" + Constants.MJPEG_BOUNDARY, stream);

    }

    /**
     * Helper method to concatenate multiple byte arrays into a single array.
     *
     * @param arrays Variable number of byte arrays to concatenate.
     * @return A single byte array containing all the input arrays' data.
     */
    private byte[] concat(byte[]... arrays) {

        int total = 0;
        for (byte[] arr : arrays)
            total += arr.length;

        byte[] result = new byte[total];
        int pos = 0;
        for (byte[] arr : arrays) {

            System.arraycopy(arr, 0, result, pos, arr.length);
            pos += arr.length;

        }

        return result;

    }

}