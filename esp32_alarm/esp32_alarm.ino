#include <WiFi.h>
#include <WebServer.h>

// Change these to match your 2.4 GHz Wi-Fi network.
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Change this to a long, unique value and use the same value in config.py.
const char* API_KEY = "change-this-key";

constexpr int LED_PIN = 25;
constexpr int BUZZER_DRIVER_PIN = 26;
WebServer server(80);

unsigned long alarmOffAt = 0;
bool alarmActive = false;

void setAlarm(bool on) {
  alarmActive = on;
  digitalWrite(LED_PIN, on ? HIGH : LOW);
  digitalWrite(BUZZER_DRIVER_PIN, on ? HIGH : LOW);
  if (on) alarmOffAt = millis() + 3000; // alarm pulse: 3 seconds
}

bool authorized() {
  return server.hasArg("key") && server.arg("key") == API_KEY;
}

void handlePing() {
  if (!authorized()) {
    server.send(401, "text/plain", "Unauthorized");
    return;
  }
  server.send(200, "text/plain", "ESP32 alarm controller OK");
}

void handleEvent() {
  if (!authorized()) {
    server.send(401, "text/plain", "Unauthorized");
    return;
  }

  String state = server.arg("state");
  String name = server.arg("name");
  if (state == "unknown") {
    Serial.printf("UNKNOWN VISITOR: %s\n", name.c_str());
    setAlarm(true);
    server.send(200, "text/plain", "Unknown visitor alarm triggered");
  } else if (state == "known") {
    Serial.printf("Known person: %s\n", name.c_str());
    server.send(200, "text/plain", "Known person logged; no alarm");
  } else {
    server.send(400, "text/plain", "state must be unknown or known");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_DRIVER_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_DRIVER_PIN, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Alarm controller IP: ");
  Serial.println(WiFi.localIP());

  server.on("/ping", HTTP_GET, handlePing);
  server.on("/event", HTTP_GET, handleEvent);
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/plain", "ESP32 alarm controller. Use authenticated /ping or /event.");
  });
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
  if (alarmActive && (long)(millis() - alarmOffAt) >= 0) {
    setAlarm(false);
  }
}
