import argparse
import os
import time
import cv2
from config import CAMERA_STREAM_URL, FACE_SCALE_FACTOR, FACE_MIN_NEIGHBORS, MIN_FACE_SIZE

def main():
    parser = argparse.ArgumentParser(description="Capture face samples for one enrolled person.")
    parser.add_argument("--name", required=True, help="Label for this person, e.g. Harry")
    args = parser.parse_args()
    name = "".join(c for c in args.name.strip() if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")
    if not name:
        raise SystemExit("Name must contain letters or numbers.")
    out_dir = os.path.join("dataset", name)
    os.makedirs(out_dir, exist_ok=True)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    cap = cv2.VideoCapture(CAMERA_STREAM_URL)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera stream: {CAMERA_STREAM_URL}")

    print("Press S to save the largest detected face; Q to quit.")
    saved = 0
    last_save = 0.0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("Frame read failed; retrying...")
            time.sleep(0.2)
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(
            gray, scaleFactor=FACE_SCALE_FACTOR,
            minNeighbors=FACE_MIN_NEIGHBORS, minSize=MIN_FACE_SIZE
        )
        largest = None
        if len(faces):
            largest = max(faces, key=lambda r: r[2] * r[3])
            x, y, w, h = largest
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "S: save face | Q: quit", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No face detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        cv2.imshow("Face enrollment", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("s") and largest is not None and time.time() - last_save > 0.4:
            x, y, w, h = largest
            crop = gray[y:y+h, x:x+w]
            crop = cv2.resize(crop, (160, 160), interpolation=cv2.INTER_AREA)
            filename = os.path.join(out_dir, f"{int(time.time()*1000)}.png")
            if cv2.imwrite(filename, crop):
                saved += 1
                last_save = time.time()
                print(f"Saved {filename} ({saved} this session)")
    cap.release()
    cv2.destroyAllWindows()
    print(f"Enrollment finished. Captured {saved} samples in {out_dir}.")

if __name__ == "__main__":
    main()
