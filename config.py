# Update these values for your network.
CAMERA_STREAM_URL = "http://192.168.1.50:81/stream"
CONTROLLER_URL = "http://192.168.1.51"
API_KEY = "change-this-key"

# LBPH distance threshold: lower is a closer match. Tune using your own tests.
CONFIDENCE_THRESHOLD = 65.0
UNKNOWN_CONSECUTIVE_FRAMES = 5
EVENT_COOLDOWN_SECONDS = 15
FACE_SCALE_FACTOR = 1.2
FACE_MIN_NEIGHBORS = 5
MIN_FACE_SIZE = (80, 80)
