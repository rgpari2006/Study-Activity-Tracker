"""Application configuration constants."""

CAMERA_INDEX = 0
MJPEG_FPS = 15
WS_PUSH_INTERVAL_SEC = 1.0

# Detection & Smoothing settings
CONFIDENCE_THRESHOLD = 0.5
SMOOTHING_WINDOW_SEC = 2.0
PHONE_PROXIMITY_RATIO = 0.25
POSE_MODEL_NAME = "yolov8n-pose.pt"
OBJECT_MODEL_NAME = "yolov8n.pt"

# Database storage path
DB_PATH = "study_tracker.db"
