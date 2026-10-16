import json
import os
import time
import urllib.parse
import requests
import cv2
from config import (
    CAMERA_STREAM_URL, CONTROLLER_URL, API_KEY, CONFIDENCE_THRESHOLD,
    UNKNOWN_CONSECUTIVE_FRAMES, EVENT_COOLDOWN_SECONDS,
    FACE_SCALE_FACTOR, FACE_MIN_NEIGHBORS, MIN_FACE_SIZE
)

MODEL_PATH = os.path.join("model", "lbph.yml")
LABELS_PATH = os.path.join("model", "labels.json")

def send_event(state, name=""):
    params = {"key": API_KEY, "state": state, "name": name[:40]}
    url = CONTROLLER_URL.rstrip("/") + "/event?" + urllib.parse.urlencode(params)
    try:
        response = requests.get(url, timeout=2.5)
        response.raise_for_status()
        print(f"Controller event sent: {state} ({name})")
    except requests.RequestException as exc:
        print(f"Could not contact alarm controller: {exc}")

def main():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        raise SystemExit("Model not found. Enroll users and run `python train.py` first.")
    if not hasattr(cv2, "face"):
        raise SystemExit("cv2.face missing. Install opencv-contrib-python in this environment.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        labels = json.load(f)

    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(CAMERA_STREAM_URL)
    if not cap.isOpened():
        raise SystemExit(f"Could not open stream {CAMERA_STREAM_URL}")

    unknown_streak = 0
    last_event_time = 0.0
    last_event_state = None
    print("Monitoring started. Press Q in the video window to stop.")
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("Stream frame failed; reconnecting...")
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(CAMERA_STREAM_URL)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(
            gray, scaleFactor=FACE_SCALE_FACTOR,
            minNeighbors=FACE_MIN_NEIGHBORS, minSize=MIN_FACE_SIZE
        )
        frame_has_unknown = False
        for (x, y, w, h) in faces:
            crop = cv2.resize(gray[y:y+h, x:x+w], (160, 160), interpolation=cv2.INTER_AREA)
            label_id, distance = recognizer.predict(crop)
            label = labels.get(str(label_id), "Unknown")
            known = distance <= CONFIDENCE_THRESHOLD
            if not known:
                label = "UNKNOWN"
                frame_has_unknown = True
            display = f"{label} | d={distance:.1f}"
            color = (0, 200, 0) if known else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, display, (x, max(25, y-8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        unknown_streak = unknown_streak + 1 if frame_has_unknown else 0
        now = time.time()
        if (unknown_streak >= UNKNOWN_CONSECUTIVE_FRAMES
                and now - last_event_time >= EVENT_COOLDOWN_SECONDS):
            send_event("unknown", "Unknown visitor")
            last_event_time = now
            last_event_state = "unknown"
            unknown_streak = 0

        cv2.putText(frame, "Q: quit | local processing", (10, frame.shape[0]-12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.imshow("ESP32-CAM Home Security", frame)
        if (cv2.waitKey(1) & 0xFF) in (ord("q"), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
