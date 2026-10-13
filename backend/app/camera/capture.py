"""Camera capture thread, posture & object detection, multi-activity smoothing, and MJPEG stream."""

import logging
import threading
import time
from typing import Generator, List, Optional

import cv2
import numpy as np

from app.camera.detector import StudyActivityDetector
from app.camera.smoothing import MultiActivitySmoother
from app.config import CAMERA_INDEX, MJPEG_FPS

logger = logging.getLogger(__name__)


def _make_status_frame(title: str, subtitle: str = "") -> bytes:
    """Create a dark, clean status placeholder frame."""
    frame = np.full((480, 640, 3), 20, dtype=np.uint8)
    cv2.rectangle(frame, (10, 10), (630, 470), (45, 55, 72), 2)
    cv2.putText(
        frame,
        title,
        (40, 230),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (240, 240, 240),
        2,
        cv2.LINE_AA,
    )
    if subtitle:
        cv2.putText(
            frame,
            subtitle,
            (40, 270),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (160, 174, 192),
            1,
            cv2.LINE_AA,
        )
    _, jpeg = cv2.imencode(".jpg", frame)
    return jpeg.tobytes()


class CameraThread:
    """Runs zero-lag camera capture, pose & object analysis using decoupled grab and process threads."""

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self._camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False

        # Threads
        self._grab_thread: Optional[threading.Thread] = None
        self._process_thread: Optional[threading.Thread] = None

        # Synchronization
        self._lock = threading.Lock()
        self._raw_lock = threading.Lock()
        self._new_frame_event = threading.Event()

        # Frames & states
        self._latest_raw_frame: Optional[np.ndarray] = None
        self._frame: Optional[bytes] = None
        self._current_activities: List[str] = ["away"]

        # Detector and multi-activity smoother
        self._detector: Optional[StudyActivityDetector] = None
        self._smoother = MultiActivitySmoother()

    @property
    def is_running(self) -> bool:
        return self._running

    def warmup(self) -> None:
        """Pre-load YOLO models and perform initial warm inference."""
        if self._detector is None:
            try:
                detector = StudyActivityDetector()
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                detector.detect(blank)
                self._detector = detector
            except Exception as e:
                logger.warning(f"Camera detector warmup error: {e}")

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """Try opening camera with DirectShow first (fast on Windows) and set buffer size = 1."""
        candidates = []
        try:
            candidates.append((self._camera_index, cv2.CAP_DSHOW))
        except AttributeError:
            pass
        candidates.append((self._camera_index, None))

        if self._camera_index != 0:
            try:
                candidates.append((0, cv2.CAP_DSHOW))
            except AttributeError:
                pass
            candidates.append((0, None))

        for idx, backend in candidates:
            try:
                cap = cv2.VideoCapture(idx, backend) if backend is not None else cv2.VideoCapture(idx)
                if cap.isOpened():
                    # Set resolution & minimum buffer size to eliminate driver-side queue lag
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        logger.info(f"Opened camera index {idx} with backend {backend}")
                        return cap
                cap.release()
            except Exception as e:
                logger.warning(f"Failed opening camera candidate {idx}: {e}")

        return None

    def start(self) -> None:
        """Open camera and start decoupled grab and process threads."""
        if self._running:
            return

        with self._lock:
            self._frame = _make_status_frame("Starting camera...", "Initializing capture feed")
            self._current_activities = ["away"]

        if self._detector is None:
            self._detector = StudyActivityDetector()

        self._smoother.reset("away")

        self._cap = self._open_camera()
        if self._cap is None:
            logger.warning(f"Could not open hardware camera at index {self._camera_index}.")
            with self._lock:
                self._frame = _make_status_frame(
                    "Camera Device Unavailable",
                    "Webcam in use by another app or permissions restricted.",
                )
                self._current_activities = ["undefined"]

        self._running = True
        self._new_frame_event.clear()

        # Dedicated grabber thread continuously empties OS buffer so frames are always fresh
        if self._cap is not None:
            self._grab_thread = threading.Thread(target=self._grab_loop, daemon=True)
            self._grab_thread.start()

        # Worker thread processes latest frame and publishes MJPEG bytes
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

    def stop(self) -> None:
        """Stop grabber & processor loops and release hardware camera."""
        self._running = False
        self._new_frame_event.set()

        if self._grab_thread is not None:
            self._grab_thread.join(timeout=2.0)
            self._grab_thread = None

        if self._process_thread is not None:
            self._process_thread.join(timeout=2.0)
            self._process_thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        with self._lock:
            self._frame = None
            self._current_activities = []
        with self._raw_lock:
            self._latest_raw_frame = None

    def get_frame(self) -> Optional[bytes]:
        """Return the latest JPEG-encoded annotated frame, or None."""
        with self._lock:
            return self._frame

    def get_current_activities(self) -> List[str]:
        """Return the latest list of smoothed detected activities."""
        with self._lock:
            return list(self._current_activities)

    def _grab_loop(self) -> None:
        """Continuously drain camera buffer at hardware rate (30 FPS) to prevent queued latency."""
        while self._running and self._cap is not None:
            ret, frame = self._cap.read()
            if ret and frame is not None:
                with self._raw_lock:
                    self._latest_raw_frame = frame
                self._new_frame_event.set()
            else:
                time.sleep(0.01)

    def _process_loop(self) -> None:
        """Run AI detection and MJPEG encoding on the most recent frame at configured FPS."""
        interval = 1.0 / MJPEG_FPS

        while self._running:
            t_start = time.time()

            if self._cap is None:
                standby = _make_status_frame(
                    "Camera Device Unavailable",
                    "Check device permissions or close apps using the webcam.",
                )
                with self._lock:
                    self._frame = standby
                    self._current_activities = ["undefined"]
                time.sleep(interval)
                continue

            # Wait for next fresh frame (with short timeout)
            self._new_frame_event.wait(timeout=interval)
            self._new_frame_event.clear()

            with self._raw_lock:
                raw_frame = self._latest_raw_frame

            if raw_frame is None:
                time.sleep(0.01)
                continue

            # Run combined detection
            if self._detector is not None:
                raw_posture, raw_objects, annotated = self._detector.detect(raw_frame)
                smoothed_activities = self._smoother.update(raw_posture, raw_objects)
            else:
                annotated = raw_frame
                smoothed_activities = ["undefined"]

            # JPEG-encode annotated frame
            _, jpeg = cv2.imencode(
                ".jpg",
                annotated,
                [int(cv2.IMWRITE_JPEG_QUALITY), 80],
            )
            with self._lock:
                self._frame = jpeg.tobytes()
                self._current_activities = smoothed_activities

            # Throttle to target FPS without accumulating drift
            t_elapsed = time.time() - t_start
            sleep_time = interval - t_elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


def mjpeg_stream(camera: CameraThread) -> Generator[bytes, None, None]:
    """Yield multipart JPEG frames for an MJPEG StreamingResponse."""
    interval = 1.0 / MJPEG_FPS
    while camera.is_running:
        frame = camera.get_frame()
        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(interval)
