# ESP32-CAM Face Recognition Home Security (local computer)

Prototype architecture:
- AI Thinker ESP32-CAM streams video over your local Wi-Fi.
- A laptop/Raspberry Pi runs Python/OpenCV LBPH face recognition.
- A second ESP32 DevKit receives events over HTTP and controls a buzzer + LED.

This is an educational prototype, not a certified security system. LBPH is a basic face matcher and can be fooled by photos; do not use face recognition alone to unlock a real door.

## 1. Hardware

- AI Thinker ESP32-CAM + OV2640
- ESP32 DevKit (CP2102 USB)
- Stable regulated 5 V supply for ESP32-CAM (camera current peaks can reset a weak supply)
- USB data cable for ESP32 DevKit
- Active buzzer (preferably drive it through an NPN transistor/MOSFET if its current exceeds a GPIO's safe output)
- LED + 220–1k ohm resistor (optional; built-in LED wiring varies by board)
- Jumper wires and breadboard

## 2. Wiring: second ESP32 DevKit

Use the *second* ESP32 for the alarm controller.

| ESP32 GPIO | Connect to |
|---|---|
| GPIO 25 | LED anode through 220–1kΩ resistor; LED cathode to GND |
| GPIO 26 | Transistor driver input for active buzzer; buzzer powered from a suitable supply |
| GND | Common ground with LED/buzzer driver |
| 3V3 | Logic supply only where suitable |

Do not drive a high-current buzzer or siren directly from a GPIO. For a transistor driver, use a suitable NPN transistor, base resistor (e.g. 1k–4.7k), and common ground. If using a magnetic/inductive buzzer, add a flyback diode across it. Never connect a mains-powered siren directly to the ESP32.

No wire is required between the ESP32-CAM and the second ESP32; both join the same Wi-Fi network.

## 3. Flash the ESP32-CAM camera firmware

1. Install Arduino IDE and the Espressif **esp32** board package.
2. Open **File → Examples → ESP32 → Camera → CameraWebServer**.
3. In the example's `board_config.h` (or camera model selection file), enable `CAMERA_MODEL_AI_THINKER` and disable other camera models.
4. Enter your 2.4 GHz Wi-Fi SSID/password in the sketch.
5. Select an AI Thinker ESP32-CAM-compatible board target. Enable PSRAM if the menu offers it.
6. Connect the ESP32-CAM to a USB-to-TTL adapter if your board doesn't have USB:
   - Adapter TX → ESP32-CAM U0R / GPIO3
   - Adapter RX → ESP32-CAM U0T / GPIO1
   - GND → GND
   - 5V → 5V (only if the adapter's 5 V output is suitable)
   - For flashing, connect GPIO0 to GND, reset/power-cycle, upload, then disconnect GPIO0 from GND and reset again.
   - Use a stable 5 V supply; don't assume a 3.3 V USB-TTL adapter can power the camera.
7. Open Serial Monitor at 115200 baud. Copy the IP address printed by the camera sketch.
8. Open `http://CAMERA_IP/` in a browser. Confirm the camera page works.
9. The stream URL is usually `http://CAMERA_IP:81/stream`. Verify it in a browser before running Python.

Some ESP32-CAM USB programmer bases have their own BOOT/reset controls; follow the labels on your particular adapter.

## 4. Flash the alarm-controller firmware

1. Open `esp32_alarm/esp32_alarm.ino`.
2. Replace `WIFI_SSID`, `WIFI_PASSWORD`, and `API_KEY`.
3. Connect the ESP32 DevKit by USB, select **ESP32 Dev Module** (or the matching board), and upload.
4. Open Serial Monitor at 115200 baud and note the controller IP.
5. Test in a browser, substituting the IP and key:
   - `http://CONTROLLER_IP/ping?key=change-this-key`
   - `http://CONTROLLER_IP/event?key=change-this-key&state=unknown&name=Test`
   - `http://CONTROLLER_IP/event?key=change-this-key&state=known&name=Test`
6. Change the example key in the URL to the same value you placed in the firmware.

The controller and camera must be on the same LAN/Wi-Fi network. Many guest networks isolate clients and prevent them communicating.

## 5. Install Python software

Python 3.10 or 3.11 is a reasonable starting point for OpenCV packages.

In a terminal inside this project folder:

```bash
python -m venv .venv
```

Activate it:
- Windows: `.venv\\Scripts\\activate`
- macOS/Linux/Raspberry Pi: `source .venv/bin/activate`

Then install:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`opencv-contrib-python` is needed because it includes `cv2.face` (LBPH). Do not install multiple conflicting OpenCV wheel variants in the same environment.

## 6. Configure Python

Edit `config.py`:
- `CAMERA_STREAM_URL`: `http://CAMERA_IP:81/stream`
- `CONTROLLER_URL`: `http://CONTROLLER_IP`
- `API_KEY`: same key as firmware
- Adjust `CONFIDENCE_THRESHOLD` only after testing. For LBPH, *lower distance means a closer match*. The initial threshold is a starting point, not a universal value.

## 7. Enroll authorized faces

1. Make sure the ESP32-CAM stream is working.
2. Run:

```bash
python enroll.py --name Harry
```

Use a person's chosen label, not a legal name if privacy is a concern. Keep the face centered and capture varied samples: straight-on, slight left/right, normal indoor lighting. Enroll each household member separately.
3. Press `s` to save a sample when a face is detected; press `q` to quit.
4. Repeat for every authorized person. Samples are stored locally under `dataset/`.

Do not enroll visitors without appropriate notice/consent. Protect the dataset; it contains biometric data.

## 8. Train the model

```bash
python train.py
```

This creates `model/lbph.yml` and `model/labels.json`.

## 9. Run live recognition and alarm

```bash
python monitor.py
```

The app draws a box and label on the laptop display. If a face is unknown for multiple consecutive frames, it sends an `unknown` event to the second ESP32. Recognized people are displayed locally; by default, the alarm is not triggered for known people. Events are rate-limited to avoid repeated buzzer activation.

Press `q` to quit. For headless Raspberry Pi operation, remove/replace the display calls in `monitor.py` and run it under a service manager.

## 10. Troubleshooting

- **Camera stream doesn't open:** visit the camera root page first; verify `http://CAMERA_IP:81/stream`; check that laptop and camera are on the same Wi-Fi.
- **Camera keeps rebooting:** use a stable 5 V supply and short, solid power leads.
- **ESP32-CAM upload fails:** GPIO0 must be tied to GND only while entering download mode; reset after upload with GPIO0 disconnected from GND.
- **`cv2.face` missing:** ensure `opencv-contrib-python` is installed in the active virtual environment and remove conflicting `opencv-python` installs.
- **Many false unknowns:** improve lighting, collect more enrollment samples, ensure face size is adequate, and tune the threshold with testing. Do not simply raise the threshold without checking false accepts.
- **Alarm controller doesn't respond:** check its printed IP, shared LAN, firewall, Wi-Fi credentials, and matching API key.
- **Buzzer doesn't sound:** check its polarity, driver wiring, power supply and ground.

## Security/privacy notes

- This starter uses HTTP and a shared API key on a trusted local network; it is not encrypted and is not suitable for exposure to the public internet.
- Do not port-forward either device. Keep them on a trusted LAN and use a strong unique API key.
- LBPH is not liveness detection and can be fooled by a printed photo or phone display. This project must not be the sole control for a real lock.
- Keep enrollment images and model files private and delete them when no longer needed.
