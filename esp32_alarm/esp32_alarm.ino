#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "img_converters.h"

// ---------- YOUR WI-FI DETAILS ----------
const char* ssid = "Airtel_Addict";
const char* password = "Extinction@67";

// ---------- AI THINKER ESP32-CAM PINS ----------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5

#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t stream_httpd = NULL;

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  uint8_t *jpg_buf = NULL;
  size_t jpg_len = 0;
  esp_err_t res = ESP_OK;

  res = httpd_resp_set_type(
    req, "multipart/x-mixed-replace;boundary=frame"
  );

  if (res != ESP_OK) return res;

  while (true) {
    fb = esp_camera_fb_get();

    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
      break;
    }

    bool converted = frame2jpg(fb, 80, &jpg_buf, &jpg_len);

    if (!converted) {
      Serial.println("RGB565 to JPEG conversion failed");
      esp_camera_fb_return(fb);
      res = ESP_FAIL;
      break;
    }

    char header[64];
    size_t hlen = snprintf(
      header, sizeof(header),
      "--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
      (unsigned int)jpg_len
    );

    res = httpd_resp_send_chunk(req, header, hlen);

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(
        req, (const char *)jpg_buf, jpg_len
      );
    }

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }

    free(jpg_buf);
    jpg_buf = NULL;
    jpg_len = 0;

    esp_camera_fb_return(fb);
    fb = NULL;

    if (res != ESP_OK) break;
  }

  if (jpg_buf) free(jpg_buf);
  if (fb) esp_camera_fb_return(fb);

  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();

  // Stream server on port 80
  config.server_port = 80;
  config.ctrl_port = 32768;

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    Serial.println("Stream server started");
  } else {
    Serial.println("Failed to start stream server");
  }
}

void setup() {

  Serial.begin(115200);
  delay(1500);
  Serial.println("CAMERA SKETCH STARTED");  
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;

  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;

  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;

  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
config.pixel_format = PIXFORMAT_RGB565;
config.frame_size   = FRAMESIZE_QVGA;  // 320x240
config.fb_count     = 1;

  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;

  if (psramFound()) {
    Serial.println("PSRAM detected");
  } else {
    Serial.println("PSRAM not detected");
    config.frame_size = FRAMESIZE_QVGA;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);

  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Wi-Fi connected");
  Serial.print("Camera IP: http://");
  Serial.println(WiFi.localIP());

  startCameraServer();

  Serial.println("Stream URL:");
  Serial.print("http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");
}

void loop() {
  delay(10000);
}
