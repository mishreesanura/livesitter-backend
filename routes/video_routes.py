"""
Video Streaming Routes
RTSP to MJPEG streaming for browser compatibility
Supports: RTSP streams, HTTP streams, local video files, and webcam
"""

import os
import cv2
import time
import threading
import urllib.request
from flask import Blueprint, Response, request, jsonify

video_bp = Blueprint("video", __name__)

# Default RTSP URL from environment variable
DEFAULT_RTSP_URL = os.getenv("RTSP_URL", "")

# Sample video URL for testing (Big Buck Bunny)
SAMPLE_VIDEO_URL = (
    "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
)


class VideoCamera:
    """
    Video Camera class to handle video stream capture
    Uses OpenCV to capture frames from RTSP/HTTP URLs, files, or webcam
    """

    def __init__(self, source):
        """
        Initialize the video camera with source

        Args:
            source: RTSP URL, HTTP URL, file path, or webcam index (0, 1, etc.)
        """
        self.source = source
        self.video = None
        self.frame = None
        self.is_running = False
        self.lock = threading.Lock()
        self.last_access = time.time()
        self.thread = None
        self.error_message = None

    def start(self):
        """Start the video capture in a separate thread"""
        if self.is_running:
            return True

        # Configure OpenCV for RTSP - use TCP and set timeout
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "rtsp_transport;tcp|timeout;5000000"
        )

        # Determine capture method based on source type
        if isinstance(self.source, int) or self.source.isdigit():
            # Webcam
            source_id = (
                int(self.source) if isinstance(self.source, str) else self.source
            )
            self.video = cv2.VideoCapture(source_id)
        elif self.source.startswith(("rtsp://", "rtmp://")):
            # RTSP/RTMP stream
            self.video = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        elif self.source.startswith(("http://", "https://")):
            # HTTP stream or video file
            self.video = cv2.VideoCapture(self.source)
        else:
            # Local file
            self.video = cv2.VideoCapture(self.source)

        if not self.video.isOpened():
            self.error_message = f"Failed to open stream: {self.source}"
            print(f"❌ {self.error_message}")
            return False

        # Set buffer size to reduce latency
        self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

        print(f"✅ Started stream: {self.source}")
        return True

    def _capture_loop(self):
        """Continuously capture frames from the stream"""
        reconnect_attempts = 0
        max_reconnect_attempts = 3

        while self.is_running:
            try:
                success, frame = self.video.read()

                if success:
                    reconnect_attempts = 0
                    with self.lock:
                        self.frame = frame
                        self.last_access = time.time()
                else:
                    reconnect_attempts += 1
                    if reconnect_attempts >= max_reconnect_attempts:
                        print(f"⚠️ Max reconnect attempts reached for: {self.source}")
                        self.is_running = False
                        break

                    # Try to reconnect if stream fails
                    print(
                        f"⚠️ Frame capture failed, attempting to reconnect ({reconnect_attempts}/{max_reconnect_attempts})..."
                    )
                    time.sleep(1)
                    self.video.release()
                    if self.source.startswith(("rtsp://", "rtmp://")):
                        self.video = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                    else:
                        self.video = cv2.VideoCapture(self.source)

            except Exception as e:
                print(f"❌ Error capturing frame: {e}")
                time.sleep(1)

    def get_frame(self):
        """
        Get the current frame encoded as JPEG

        Returns:
            JPEG encoded frame bytes or None
        """
        with self.lock:
            if self.frame is None:
                return None

            self.last_access = time.time()

            # Encode frame as JPEG
            ret, jpeg = cv2.imencode(".jpg", self.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

            if ret:
                return jpeg.tobytes()
            return None

    def stop(self):
        """Stop the video capture"""
        self.is_running = False
        if self.video:
            self.video.release()
        print(f"🛑 Stopped stream: {self.source}")

    def __del__(self):
        """Cleanup on destruction"""
        self.stop()


# Cache for active camera instances
cameras = {}
cameras_lock = threading.Lock()


def get_camera(rtsp_url):
    """
    Get or create a camera instance for the given RTSP URL

    Args:
        rtsp_url: RTSP stream URL

    Returns:
        VideoCamera instance
    """
    with cameras_lock:
        if rtsp_url not in cameras:
            cameras[rtsp_url] = VideoCamera(rtsp_url)
        return cameras[rtsp_url]


def cleanup_inactive_cameras(timeout=300):
    """
    Remove cameras that haven't been accessed recently

    Args:
        timeout: Seconds of inactivity before cleanup (default 5 minutes)
    """
    with cameras_lock:
        current_time = time.time()
        inactive = [
            url
            for url, cam in cameras.items()
            if current_time - cam.last_access > timeout
        ]
        for url in inactive:
            cameras[url].stop()
            del cameras[url]
            print(f"🧹 Cleaned up inactive camera: {url}")


def generate_frames(camera):
    """
    Generator function to yield MJPEG frames

    Args:
        camera: VideoCamera instance

    Yields:
        MJPEG frame data with multipart boundaries
    """
    while True:
        frame = camera.get_frame()

        if frame is None:
            # Return a placeholder frame if no video
            time.sleep(0.1)
            continue

        # Yield frame in MJPEG multipart format
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

        # Control frame rate (~30 FPS max)
        time.sleep(0.033)


@video_bp.route("/video_feed", methods=["GET"])
def video_feed():
    """
    GET /video_feed
    Stream RTSP video as MJPEG for browser compatibility

    Query Parameters:
        rtsp_url: RTSP stream URL (optional if RTSP_URL env var is set)

    Returns:
        Multipart MJPEG stream response
    """
    # Get RTSP URL from query parameter or environment variable
    rtsp_url = request.args.get("rtsp_url", DEFAULT_RTSP_URL)

    if not rtsp_url:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "No RTSP URL provided. Pass rtsp_url query parameter or set RTSP_URL environment variable.",
                }
            ),
            400,
        )

    # Get or create camera for this URL
    camera = get_camera(rtsp_url)

    # Start camera if not running
    if not camera.start():
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to connect to RTSP stream: {rtsp_url}",
                }
            ),
            503,
        )

    # Return MJPEG stream
    return Response(
        generate_frames(camera),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


@video_bp.route("/video_feed/status", methods=["GET"])
def video_status():
    """
    GET /video_feed/status
    Get status of active video streams

    Returns:
        JSON with active streams information
    """
    with cameras_lock:
        streams = []
        for url, cam in cameras.items():
            streams.append(
                {
                    "url": url,
                    "is_running": cam.is_running,
                    "last_access": cam.last_access,
                }
            )

    return (
        jsonify({"success": True, "active_streams": len(streams), "streams": streams}),
        200,
    )


@video_bp.route("/video_feed/stop", methods=["POST"])
def stop_stream():
    """
    POST /video_feed/stop
    Stop a specific RTSP stream

    Request Body:
        rtsp_url: RTSP stream URL to stop
    """
    data = request.get_json() or {}
    rtsp_url = data.get("rtsp_url") or request.args.get("rtsp_url")

    if not rtsp_url:
        return jsonify({"success": False, "error": "No RTSP URL provided"}), 400

    with cameras_lock:
        if rtsp_url in cameras:
            cameras[rtsp_url].stop()
            del cameras[rtsp_url]
            return (
                jsonify({"success": True, "message": f"Stream stopped: {rtsp_url}"}),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Stream not found"}), 404


@video_bp.route("/video_feed/stop_all", methods=["POST"])
def stop_all_streams():
    """
    POST /video_feed/stop_all
    Stop all active RTSP streams
    """
    with cameras_lock:
        count = len(cameras)
        for cam in cameras.values():
            cam.stop()
        cameras.clear()

    return jsonify({"success": True, "message": f"Stopped {count} stream(s)"}), 200


@video_bp.route("/video_feed/webcam", methods=["GET"])
def webcam_feed():
    """
    GET /video_feed/webcam
    Stream from local webcam (index 0) for testing

    Query Parameters:
        camera_index: Camera index (default 0)

    Returns:
        Multipart MJPEG stream response
    """
    camera_index = request.args.get("camera_index", "0")

    # Get or create camera for webcam
    camera = get_camera(camera_index)

    # Start camera if not running
    if not camera.start():
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to open webcam {camera_index}. Make sure a webcam is connected.",
                }
            ),
            503,
        )

    # Return MJPEG stream
    return Response(
        generate_frames(camera),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


@video_bp.route("/video_feed/test", methods=["GET"])
def test_video_feed():
    """
    GET /video_feed/test
    Generate a test pattern video feed for development/testing
    No RTSP stream or webcam required.

    Returns:
        Multipart MJPEG stream response with test pattern
    """
    return Response(
        generate_test_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


def generate_test_frames():
    """
    Generator function to yield test pattern frames
    Creates a moving color pattern for testing without a real stream

    Yields:
        MJPEG frame data with multipart boundaries
    """
    import numpy as np

    frame_count = 0
    width, height = 640, 480

    while True:
        # Create a test pattern frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Moving gradient background
        offset = (frame_count * 2) % 256
        for y in range(height):
            for x in range(0, width, 10):  # Step by 10 for performance
                frame[y, x : x + 10, 0] = (x + offset) % 256  # Blue
                frame[y, x : x + 10, 1] = (y + offset) % 256  # Green
                frame[y, x : x + 10, 2] = (128 + offset) % 256  # Red

        # Add timestamp text
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"Test Stream - {timestamp}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"Frame: {frame_count}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            frame,
            "LiveSitter Test Pattern",
            (width // 2 - 150, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
        )

        # Encode as JPEG
        ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        if ret:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
            )

        frame_count += 1
        time.sleep(0.033)  # ~30 FPS


@video_bp.route("/video_feed/sources", methods=["GET"])
def list_sources():
    """
    GET /video_feed/sources
    List available video source options for testing

    Returns:
        JSON with available video sources
    """
    return (
        jsonify(
            {
                "success": True,
                "sources": [
                    {
                        "name": "Test Pattern",
                        "url": "/video_feed/test",
                        "description": "Generated test pattern - no camera or stream needed",
                    },
                    {
                        "name": "Webcam",
                        "url": "/video_feed/webcam",
                        "description": "Local webcam (camera index 0)",
                    },
                    {
                        "name": "RTSP Stream",
                        "url": "/video_feed?rtsp_url=YOUR_RTSP_URL",
                        "description": "Custom RTSP stream URL",
                    },
                ],
                "hint": "Use /video_feed/test for development without a real camera",
            }
        ),
        200,
    )
