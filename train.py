import json
import os
import cv2
import numpy as np

DATASET_DIR = "dataset"
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "lbph.yml")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")

def main():
    if not hasattr(cv2, "face"):
        raise SystemExit("cv2.face missing. Install opencv-contrib-python in this Python environment.")
    images, ids = [], []
    labels = {}
    label_id = 0
    for person in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, person)
        if not os.path.isdir(person_dir):
            continue
        person_images = []
        for filename in sorted(os.listdir(person_dir)):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                path = os.path.join(person_dir, filename)
                img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    person_images.append(cv2.resize(img, (160, 160)))
        if person_images:
            labels[str(label_id)] = person
            images.extend(person_images)
            ids.extend([label_id] * len(person_images))
            print(f"{person}: {len(person_images)} samples")
            label_id += 1
    if not images:
        raise SystemExit("No training images found. Run enroll.py first.")
    os.makedirs(MODEL_DIR, exist_ok=True)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images, np.asarray(ids, dtype=np.int32))
    recognizer.write(MODEL_PATH)
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)
    print(f"Saved model to {MODEL_PATH} and labels to {LABELS_PATH}")
    print("Important: validate false accepts/rejects with people not in the dataset before relying on alerts.")

if __name__ == "__main__":
    main()
