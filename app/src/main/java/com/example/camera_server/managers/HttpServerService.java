/**
 * Service that manages the HTTP server using NanoHTTPD.
 * It provides endpoints for the video stream and GPS data.
 */
package com.example.camera_server.managers;

import com.example.camera_server.utility.Constants;
import fi.iki.elonen.NanoHTTPD;

import java.io.IOException;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Enumeration;

public class HttpServerService extends NanoHTTPD {

    private final StreamManager streamManager;

    /**
     * Initializes and starts the HTTP server.
     *
     * @param port          The port on which the server will listen.
     * @param streamManager The manager responsible for providing stream data.
     * @throws IOException If the server fails to start.
     */
    public HttpServerService(int port, StreamManager streamManager) throws IOException {

        super(port);
        this.streamManager = streamManager;
        start(SOCKET_READ_TIMEOUT, false);
        System.out.println("HTTP Server started on port " + port);

    }

    /**
     * Handles incoming HTTP requests and routes them to the appropriate response.
     *
     * @param session The HTTP session containing request information.
     * @return An HTTP Response object.
     */
    @Override
    public Response serve(IHTTPSession session) {

        String uri = session.getUri();

        switch (uri) {

            case "/":
                // Serve a simple HTML page that displays the video stream
                String html = "<html><body>" + "<h2>Streaming Video</h2>" + "<img src='/video' width='" + Constants.STREAM_WIDTH + "' height='" + Constants.STREAM_HEIGHT + "' />" + "</body></html>";
                return newFixedLengthResponse(Response.Status.OK, "text/html", html);

            case "/video":
                // Route to the video stream response
                return streamManager.getStreamResponse();

            case "/gps":
                // Route to the GPS data response
                return streamManager.getGpsResponse();

            default:
                // Handle unknown endpoints
                return newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "404 Not Found");

        }

    }

}