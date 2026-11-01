# ESP32-CAM Local Face Monitor

Install on Windows:
```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Run (change URL if camera IP changes):
```bat
set CAMERA_URL=http://192.168.1.11/stream
python app.py
```
Open `http://127.0.0.1:5000` on the PC. For phone/other LAN device, open `http://PC_IP:5000`; allow Python through Windows Firewall on Private networks. Reserve the PC's IP in the router for a stable address.

Register: enter name, capture 10–20 images with varied lighting/angle, then Train. Samples are stored in `data/faces`, events/snapshots in `data/events`.

Browser notifications require permission and dashboard open. Telegram alert integration can be added next. This Haar + LBPH implementation is a lightweight prototype, not security-grade; false matches/misses are possible. Do not rely on it as the sole lock/security mechanism.
