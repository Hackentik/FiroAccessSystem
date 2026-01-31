#include <WiFi.h>
#include <WebServer.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <Wire.h>
#include <MFRC522_I2C.h>

#define RELAY_PIN 10
#define GREEN_LED_PIN 5
#define RED_LED_PIN 2
#define BUZZER_PIN 3
#define EXIT_BUTTON_PIN 6

#define I2C_SDA 8
#define I2C_SCL 2

class IndicatorSystem {
private:
  int ledConfig;
  bool buzzerEnabled;

public:
  IndicatorSystem(int config, bool useBuzzer) {
    ledConfig = config;
    buzzerEnabled = useBuzzer;

    if (ledConfig >= 1) {
      pinMode(RED_LED_PIN, OUTPUT);
      digitalWrite(RED_LED_PIN, LOW);
    }
    if (ledConfig >= 2) {
      pinMode(GREEN_LED_PIN, OUTPUT);
      digitalWrite(GREEN_LED_PIN, LOW);
    }
    if (buzzerEnabled) {
      pinMode(BUZZER_PIN, OUTPUT);
      digitalWrite(BUZZER_PIN, LOW);
    }
  }

  void indicateState(int state) {
    switch (state) {
      case 0:
        indicateBooting();
        break;
      case 1:
        indicateConfigMode();
        break;
      case 2:
      case 3:
        indicateWifiConnecting();
        break;
      case 4:
        indicateReady();
        break;
      case 5:
        indicateReadingCard();
        break;
      case 6:
        indicateAccessGranted();
        break;
      case 7:
        indicateAccessDenied();
        break;
      case 8:
        indicateDoorOpen();
        break;
      case 9:
        indicateError();
        break;
      case 10:
        indicateEvacuationMode();
        break;
      case 11:
        indicateLockdownMode();
        break;
    }
  }

  void indicateBooting() {
    if (ledConfig == 0 && buzzerEnabled) {
      tone(BUZZER_PIN, 1000, 100);
    } else if (ledConfig == 1) {
      for (int i = 0; i < 3; i++) {
        digitalWrite(RED_LED_PIN, HIGH);
        delay(100);
        digitalWrite(RED_LED_PIN, LOW);
        delay(100);
      }
    } else if (ledConfig == 2) {
      digitalWrite(RED_LED_PIN, HIGH);
      delay(200);
      digitalWrite(RED_LED_PIN, LOW);
      digitalWrite(GREEN_LED_PIN, HIGH);
      delay(200);
      digitalWrite(GREEN_LED_PIN, LOW);
    }
  }

  void indicateConfigMode() {
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
      lastBlink = millis();
      if (ledConfig >= 1) {
        digitalWrite(RED_LED_PIN, !digitalRead(RED_LED_PIN));
      }
    }
  }

  void indicateWifiConnecting() {
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 300) {
      lastBlink = millis();
      if (ledConfig >= 1) {
        digitalWrite(RED_LED_PIN, !digitalRead(RED_LED_PIN));
      }
    }
  }

  void indicateReady() {
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 2000) {
      lastBlink = millis();
      if (ledConfig == 2) {
        digitalWrite(GREEN_LED_PIN, HIGH);
        delay(100);
        digitalWrite(GREEN_LED_PIN, LOW);
      }
    }
  }

  void indicateReadingCard() {
    if (ledConfig == 2) {
      digitalWrite(GREEN_LED_PIN, HIGH);
      delay(300);
      digitalWrite(GREEN_LED_PIN, LOW);
    }
    if (buzzerEnabled) {
      tone(BUZZER_PIN, 1500, 100);
    }
  }

  void indicateAccessGranted() {
    if (ledConfig == 2) {
      digitalWrite(GREEN_LED_PIN, HIGH);
      delay(2000);
      digitalWrite(GREEN_LED_PIN, LOW);
    }
    if (buzzerEnabled) {
      tone(BUZZER_PIN, 1200, 200);
      delay(300);
      tone(BUZZER_PIN, 1500, 200);
    }
  }

  void indicateAccessDenied() {
    if (ledConfig >= 1) {
      for (int i = 0; i < 3; i++) {
        digitalWrite(RED_LED_PIN, HIGH);
        delay(300);
        digitalWrite(RED_LED_PIN, LOW);
        if (i < 2) delay(200);
      }
    }
    if (buzzerEnabled) {
      tone(BUZZER_PIN, 800, 300);
      delay(400);
      tone(BUZZER_PIN, 600, 300);
    }
  }

  void indicateDoorOpen() {
    if (ledConfig == 2) {
      digitalWrite(GREEN_LED_PIN, HIGH);
    }
  }

  void indicateError() {
    if (ledConfig >= 1) {
      digitalWrite(RED_LED_PIN, HIGH);
    }
    if (buzzerEnabled) {
      tone(BUZZER_PIN, 400, 1000);
    }
  }

  void indicateEvacuationMode() {
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 500) {
      lastBlink = millis();
      if (ledConfig == 2) {
        digitalWrite(RED_LED_PIN, !digitalRead(RED_LED_PIN));
        digitalWrite(GREEN_LED_PIN, !digitalRead(GREEN_LED_PIN));
      }
    }
  }

  void indicateLockdownMode() {
    if (ledConfig >= 1) {
      digitalWrite(RED_LED_PIN, HIGH);
    }
  }

  void resetIndicators() {
    if (ledConfig >= 1) digitalWrite(RED_LED_PIN, LOW);
    if (ledConfig == 2) digitalWrite(GREEN_LED_PIN, LOW);
    if (buzzerEnabled) digitalWrite(BUZZER_PIN, LOW);
  }

  void beep(int count = 1) {
    if (!buzzerEnabled) return;

    for (int i = 0; i < count; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      if (i < count - 1) delay(100);
    }
  }

private:
  void tone(int pin, int frequency, int duration) {
    for (long i = 0; i < duration * 1000L; i += frequency) {
      digitalWrite(pin, HIGH);
      delayMicroseconds(frequency);
      digitalWrite(pin, LOW);
      delayMicroseconds(frequency);
    }
  }
};

WebServer configServer(80);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Preferences preferences;
MFRC522_I2C mfrc522(0x28, 0xFF, &Wire);

int currentState = 0;
bool doorOpen = false;
bool doorOpenedBySchedule = false;
bool evacuationMode = false;
bool lockdownMode = false;
bool configMode = true;
String lastCardUID = "";
unsigned long doorOpenTime = 0;
unsigned long lastCardRead = 0;
const unsigned long DOOR_OPEN_DURATION = 5000;
unsigned long lastIndicationUpdate = 0;
bool mqttConnected = false;
bool doorLocked = false;
unsigned long modeActivatedTime = 0;
unsigned long lastCardSuccess = 0;
const unsigned long CARD_RESET_INTERVAL = 2000;

struct Config {
  char wifi_ssid[32];
  char wifi_password[64];
  char mqtt_broker[64];
  int mqtt_port;
  char device_id[24];
  int led_config;
  bool use_buzzer;
  bool rfid_enabled;
};

Config config;
IndicatorSystem* indicator = nullptr;

void openDoor(bool bySchedule = false) {
  if (lockdownMode && !bySchedule) {
    Serial.println("Lockdown: Door locked!");
    
    if (mqttClient.connected()) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = "lockdown_blocked";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = "Attempt to open door in lockdown";
      doc["attempt_type"] = bySchedule ? "schedule" : "manual";
      
      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);
    }
    return;
  }
  
  if (evacuationMode) {
    if (!doorOpen) {
      doorOpen = true;
      doorOpenedBySchedule = false;
      doorOpenTime = millis();

      pinMode(RELAY_PIN, OUTPUT);
      digitalWrite(RELAY_PIN, HIGH);

      Serial.println("Evacuation: Door open!");
      currentState = 8;

      if (mqttClient.connected()) {
        DynamicJsonDocument doc(256);
        doc["event_type"] = "evacuation_open";
        doc["device_id"] = config.device_id;
        doc["timestamp"] = millis();
        doc["message"] = "Door opened in evacuation mode";
        
        char buffer[256];
        serializeJson(doc, buffer);
        mqttClient.publish("access/events", buffer);
      }
    }
    return;
  }

  static unsigned long lastOpenTime = 0;
  if (doorOpen && millis() - doorOpenTime < 1000) {
    Serial.println("Door already open");
    return;
  }

  if (!doorOpen) {
    doorOpen = true;
    doorOpenedBySchedule = bySchedule;
    doorOpenTime = millis();
    lastOpenTime = millis();

    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);

    Serial.println("Door opened");
    currentState = 8;

    if (mqttClient.connected()) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = bySchedule ? "door_opened_sh" : "door_opened";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = bySchedule ? "Door opened by schedule" : "Door opened";

      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);
    }
  } else {
    if (bySchedule) {
      doorOpenedBySchedule = true;
    }
    doorOpenTime = millis();
  }
}

void resetRFIDReader() {
  mfrc522.PCD_StopCrypto1();
  delay(50);
  mfrc522.PCD_Init();
  delay(50);
}

void closeDoor(bool forceClose = false) {
  if (evacuationMode && !forceClose) {
    Serial.println("Evacuation: Door cannot be closed!");
    
    if (mqttClient.connected()) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = "evacuation_keep_open";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = "Attempt to close door in evacuation mode";
      
      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);
    }
    return;
  }
  
  if (lockdownMode && doorOpen) {
    forceClose = true;
  }

  if (doorOpen && (!doorOpenedBySchedule || forceClose)) {
    doorOpen = false;
    doorOpenedBySchedule = false;

    digitalWrite(RELAY_PIN, LOW);
    pinMode(RELAY_PIN, INPUT);

    Serial.println("Door closed");

    if (indicator) {
      indicator->resetIndicators();
    }

    if (mqttClient.connected()) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = "door_closed";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = forceClose ? "Door force closed" : "Door closed";
      doc["mode"] = evacuationMode ? "evacuation" : (lockdownMode ? "lockdown" : "normal");

      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);
    }

    if (!evacuationMode && !lockdownMode) {
      currentState = 4;
    } else if (lockdownMode) {
      currentState = 11;
    } else if (evacuationMode) {
      currentState = 10;
    }
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (length == 0) return;
  if (length > 512) length = 512;

  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';

  DynamicJsonDocument doc(512);
  DeserializationError error = deserializeJson(doc, message);

  if (error) return;

  const char* targetDevice = doc["device_id"];
  if (targetDevice && strcmp(targetDevice, config.device_id) != 0) return;

  if (strcmp(topic, "access/commands") == 0) {
    const char* command = doc["command"];

    if (!command) return;

    if (strcmp(command, "open_door") == 0) {
      openDoor(false);

      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "open_door";
      response["status"] = "executed";
      response["timestamp"] = millis();

      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);

    } else if (strcmp(command, "open_door_sh") == 0) {
      openDoor(true);

      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "open_door_sh";
      response["status"] = "executed";
      response["timestamp"] = millis();

      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);

    } else if (strcmp(command, "close_door") == 0) {
      closeDoor(false);

      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "close_door";
      response["status"] = doorOpen ? "ignored" : "executed";
      response["message"] = doorOpen ? "Door open by schedule" : "Door closed";
      response["timestamp"] = millis();

      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);

    } else if (strcmp(command, "close_door_sh") == 0) {
      closeDoor(true);

      DynamicJsonDocument eventDoc(256);
      eventDoc["event_type"] = "door_closed_sh";
      eventDoc["device_id"] = config.device_id;
      eventDoc["timestamp"] = millis();
      eventDoc["message"] = "Door closed by schedule";

      char eventBuffer[256];
      serializeJson(eventDoc, eventBuffer);
      mqttClient.publish("access/events", eventBuffer);

      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "close_door_sh";
      response["status"] = "executed";
      response["timestamp"] = millis();

      char responseBuffer[256];
      serializeJson(response, responseBuffer);
      mqttClient.publish("access/command_response", responseBuffer);

    } else if (strcmp(command, "reboot") == 0) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = "reboot";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = "Device rebooting";

      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);

      delay(2000);
      ESP.restart();

    } else if (strcmp(command, "beep") == 0) {
      int count = doc["count"] | 1;

      if (indicator) {
        indicator->beep(count);
      }

      DynamicJsonDocument doc(256);
      doc["event_type"] = "beep";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = String("Beep ") + count + " times";

      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);

    } else if (strcmp(command, "evacuation_on") == 0) {
      evacuationMode = true;
      lockdownMode = false;
      modeActivatedTime = millis();
      
      openDoor(false);
      currentState = 10;
      
      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "evacuation_on";
      response["status"] = "activated";
      response["timestamp"] = millis();
      response["message"] = "Evacuation mode activated";
      
      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);
      
      DynamicJsonDocument eventDoc(256);
      eventDoc["event_type"] = "evacuation_mode_on";
      eventDoc["device_id"] = config.device_id;
      eventDoc["timestamp"] = millis();
      eventDoc["message"] = "Evacuation mode activated";
      
      char eventBuffer[256];
      serializeJson(eventDoc, eventBuffer);
      mqttClient.publish("access/events", eventBuffer);

    } else if (strcmp(command, "evacuation_off") == 0) {
      evacuationMode = false;
      closeDoor(true);
      currentState = 4;
      
      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "evacuation_off";
      response["status"] = "deactivated";
      response["timestamp"] = millis();
      response["message"] = "Evacuation mode off";
      response["duration"] = millis() - modeActivatedTime;
      
      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);

    } else if (strcmp(command, "lockdown_on") == 0) {
      lockdownMode = true;
      evacuationMode = false;
      modeActivatedTime = millis();
      
      closeDoor(true);
      currentState = 11;
      
      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "lockdown_on";
      response["status"] = "activated";
      response["timestamp"] = millis();
      response["message"] = "Lockdown mode activated";
      
      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);
      
      DynamicJsonDocument eventDoc(256);
      eventDoc["event_type"] = "lockdown_mode_on";
      eventDoc["device_id"] = config.device_id;
      eventDoc["timestamp"] = millis();
      eventDoc["message"] = "Lockdown mode activated";
      
      char eventBuffer[256];
      serializeJson(eventDoc, eventBuffer);
      mqttClient.publish("access/events", eventBuffer);

    } else if (strcmp(command, "lockdown_off") == 0) {
      lockdownMode = false;
      currentState = 4;
      
      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "lockdown_off";
      response["status"] = "deactivated";
      response["timestamp"] = millis();
      response["message"] = "Lockdown mode off";
      response["duration"] = millis() - modeActivatedTime;
      
      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);

    } else if (strcmp(command, "get_mode") == 0) {
      DynamicJsonDocument response(256);
      response["device_id"] = config.device_id;
      response["command"] = "get_mode";
      response["evacuation_mode"] = evacuationMode;
      response["lockdown_mode"] = lockdownMode;
      response["current_state"] = currentState;
      response["door_open"] = doorOpen;
      response["timestamp"] = millis();
      response["mode_duration"] = modeActivatedTime > 0 ? millis() - modeActivatedTime : 0;
      
      char buffer[256];
      serializeJson(response, buffer);
      mqttClient.publish("access/command_response", buffer);
    }
  }
  else if (strcmp(topic, "access/responses") == 0) {
    bool success = doc["success"] | false;
    const char* requestId = doc["request_id"] | "";

    static String lastProcessedRequest = "";
    String currentRequest = String(requestId);
    
    if (currentRequest == lastProcessedRequest) return;
    lastProcessedRequest = currentRequest;

    if (lockdownMode) {
      if (indicator) indicator->indicateState(7);
      
      if (mqttClient.connected()) {
        DynamicJsonDocument eventDoc(256);
        eventDoc["event_type"] = "access_denied_lockdown";
        eventDoc["device_id"] = config.device_id;
        eventDoc["request_id"] = requestId;
        eventDoc["timestamp"] = millis();
        eventDoc["message"] = "Access denied (lockdown)";
        eventDoc["success"] = false;
        
        char buffer[256];
        serializeJson(eventDoc, buffer);
        mqttClient.publish("access/events", buffer);
      }
      return;
    }

    if (success) {
      openDoor(false);
      if (indicator) indicator->indicateState(6);
    } else {
      if (indicator) indicator->indicateState(7);

      if (config.use_buzzer) {
        for (int i = 0; i < 3; i++) {
          digitalWrite(BUZZER_PIN, HIGH);
          delay(200);
          digitalWrite(BUZZER_PIN, LOW);
          delay(150);
        }
      }
    }

    if (mqttClient.connected()) {
      DynamicJsonDocument eventDoc(256);
      eventDoc["event_type"] = success ? "access_granted" : "access_denied";
      eventDoc["device_id"] = config.device_id;
      eventDoc["request_id"] = requestId;
      eventDoc["timestamp"] = millis();
      eventDoc["message"] = doc["message"] | "";
      eventDoc["success"] = success;

      char buffer[256];
      serializeJson(eventDoc, buffer);
      mqttClient.publish("access/events", buffer);
    }
  }
}

void sendStatusToMQTT(String status) {
  if (!mqttClient.connected()) return;

  DynamicJsonDocument doc(256);
  doc["device_id"] = config.device_id;
  doc["status"] = status;
  doc["timestamp"] = millis();
  doc["ip_address"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["door_state"] = doorOpen ? "open" : "closed";
  doc["schedule_mode"] = doorOpenedBySchedule ? "true" : "false";
  doc["evacuation_mode"] = evacuationMode;
  doc["lockdown_mode"] = lockdownMode;

  char buffer[256];
  serializeJson(doc, buffer);
  mqttClient.publish("access/status", buffer);
}

void sendDeviceInfo() {
  if (!mqttClient.connected()) return;

  DynamicJsonDocument doc(512);
  doc["device_id"] = config.device_id;
  doc["device_type"] = "esp32_rfid_controller";
  doc["firmware_version"] = "1.0";
  doc["mac_address"] = WiFi.macAddress();
  doc["ip_address"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["uptime"] = millis();
  doc["rfid_enabled"] = config.rfid_enabled;
  doc["led_config"] = config.led_config;
  doc["buzzer_enabled"] = config.use_buzzer;
  doc["timestamp"] = millis();
  doc["door_state"] = doorOpen ? "open" : "closed";
  doc["schedule_mode"] = doorOpenedBySchedule ? "true" : "false";
  doc["evacuation_mode"] = evacuationMode;
  doc["lockdown_mode"] = lockdownMode;

  char buffer[512];
  serializeJson(doc, buffer);
  mqttClient.publish("access/device_info", buffer);
}

void saveConfigToFlash() {
  preferences.begin("rfid_access", false);
  preferences.clear();
  preferences.putBytes("config", &config, sizeof(config));
  preferences.end();
}

void loadConfigFromFlash() {
  preferences.begin("rfid_access", true);
  size_t savedSize = preferences.getBytesLength("config");

  if (savedSize == sizeof(config)) {
    preferences.getBytes("config", &config, sizeof(config));
    preferences.end();
    return;
  }

  preferences.end();

  memset(&config, 0, sizeof(config));
  strcpy(config.wifi_ssid, "");
  strcpy(config.wifi_password, "");
  strcpy(config.mqtt_broker, "mqtt.eclipseprojects.io");
  config.mqtt_port = 1883;
  strcpy(config.device_id, "esp32_rfid_1");
  config.led_config = 2;
  config.use_buzzer = true;
  config.rfid_enabled = true;
}

bool initRFID() {
  if (!config.rfid_enabled) return true;
  
  delay(3000);
  Wire.begin(I2C_SDA, I2C_SCL);
  mfrc522.PCD_Init();

  byte version = mfrc522.PCD_ReadRegister(0x37);

  if (version == 0x00 || version == 0xFF) return false;

  return true;
}

String readRFIDCard() {
  if (lockdownMode) return "";
  if (evacuationMode) return "";
  if (!config.rfid_enabled) return "";

  static unsigned long lastReset = 0;
  if (millis() - lastReset > 5000) {
    mfrc522.PCD_Init();
    lastReset = millis();
  }

  if (!mfrc522.PICC_IsNewCardPresent()) return "";
  if (!mfrc522.PICC_ReadCardSerial()) {
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return "";
  }

  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    char buf[3];
    sprintf(buf, "%02X", mfrc522.uid.uidByte[i]);
    uidString += buf;
  }
  uidString.toUpperCase();

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  delay(50);

  return uidString;
}

void processCard(String cardUID) {
  if (cardUID.length() == 0) return;

  lastCardRead = millis();

  if (indicator) indicator->indicateState(5);

  if (mqttClient.connected()) {
    DynamicJsonDocument eventDoc(256);
    eventDoc["event_type"] = "card_read";
    eventDoc["device_id"] = config.device_id;
    eventDoc["card_uid"] = cardUID;
    eventDoc["timestamp"] = millis();
    eventDoc["message"] = "Card read";

    char eventBuffer[256];
    serializeJson(eventDoc, eventBuffer);
    mqttClient.publish("access/events", eventBuffer);
  }

  if (lockdownMode) {
    if (indicator) indicator->indicateState(7);
    
    if (config.use_buzzer) {
      for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(200);
        digitalWrite(BUZZER_PIN, LOW);
        delay(150);
      }
    }
    return;
  }

  DynamicJsonDocument doc(256);
  doc["request_id"] = String("req_") + millis();
  doc["device_id"] = config.device_id;
  doc["card_number"] = cardUID;
  doc["timestamp"] = millis();
  doc["reader_type"] = "i2c_rfid";
  doc["location"] = "main_door";

  char buffer[256];
  serializeJson(doc, buffer);

  if (mqttClient.connected()) {
    mqttClient.publish("access/requests", buffer);
  }

  delay(300);
}

const char CONFIG_PAGE[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ESP32 RFID Configuration</title><style>
body{font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:20px;background:#f5f5f5;}
h1{text-align:center;color:#333;}
.section{background:white;padding:15px;margin:10px 0;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.1);}
label{display:block;margin:8px 0 4px;font-weight:bold;}
input,select{width:100%;padding:8px;margin:5px 0;box-sizing:border-box;}
.btn{background:#4CAF50;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;width:100%;margin:5px 0;}
.btn:hover{background:#45a049;}
.info{background:#e7f3fe;border-left:4px solid #2196F3;padding:10px;margin:10px 0;}
.status{padding:10px;margin:10px 0;border-radius:5px;}
.success{background:#d4edda;color:#155724;}
.error{background:#f8d7da;color:#721c24;}
</style></head>
<body>
<h1>Access Controller Setup</h1>
<div class="info">
<strong>AP:</strong> ESP32_RFID_Setup<br>
<strong>IP:</strong> 192.168.4.1<br>
<strong>Pins:</strong> Relay(4), Green(5), Red(2), Buzzer(3), Button(6)
</div>

<div class="section">
<h3>WiFi Settings</h3>
<input type="text" id="ssid" placeholder="WiFi SSID" required>
<input type="password" id="password" placeholder="WiFi Password">
</div>

<div class="section">
<h3>MQTT Settings</h3>
<input type="text" id="mqtt_broker" placeholder="Broker address" required>
<input type="number" id="mqtt_port" placeholder="Port" value="1883">
<input type="text" id="device_id" placeholder="Device ID" value="esp32_rfid">
</div>

<div class="section">
<h3>Hardware Settings</h3>
<label>LED Configuration:</label>
<select id="led_config">
<option value="0">No LEDs</option>
<option value="1">Red only</option>
<option value="2" selected>Both LEDs</option>
</select>
<label><input type="checkbox" id="use_buzzer" checked> Use buzzer</label>
<label><input type="checkbox" id="rfid_enabled" checked> Enable RFID reader</label>
</div>

<div class="section">
<button class="btn" onclick="saveConfig()" style="background:#4CAF50;">Save and reboot</button>
<button class="btn" onclick="testDoor()" style="background:#FF9800;">Test door</button>
</div>

<div id="status"></div>

<script>
function saveConfig(){
const cfg={
ssid:document.getElementById('ssid').value,
password:document.getElementById('password').value,
mqtt_broker:document.getElementById('mqtt_broker').value,
mqtt_port:parseInt(document.getElementById('mqtt_port').value),
device_id:document.getElementById('device_id').value,
led_config:parseInt(document.getElementById('led_config').value),
use_buzzer:document.getElementById('use_buzzer').checked,
rfid_enabled:document.getElementById('rfid_enabled').checked
};
fetch('/saveconfig',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)})
.then(r=>r.json()).then(d=>{
const s=document.getElementById('status');
s.className='status '+(d.success?'success':'error');
s.innerHTML=d.message;
});
}
function testDoor(){
fetch('/testdoor').then(r=>r.json()).then(d=>{
const s=document.getElementById('status');
s.className='status success';
s.innerHTML=d.message;
});
}
fetch('/getconfig').then(r=>r.json()).then(d=>{
if(d.ssid)document.getElementById('ssid').value=d.ssid;
if(d.mqtt_broker)document.getElementById('mqtt_broker').value=d.mqtt_broker;
if(d.device_id)document.getElementById('device_id').value=d.device_id;
if(d.led_config)document.getElementById('led_config').value=d.led_config;
document.getElementById('use_buzzer').checked=d.use_buzzer!==false;
document.getElementById('rfid_enabled').checked=d.rfid_enabled!==false;
});
</script>
</body></html>
)rawliteral";

void handleConfigPage() { configServer.send(200, "text/html", CONFIG_PAGE); }

void handleGetConfig() {
  DynamicJsonDocument json(512);
  json["ssid"] = config.wifi_ssid;
  json["mqtt_broker"] = config.mqtt_broker;
  json["device_id"] = config.device_id;
  json["led_config"] = config.led_config;
  json["use_buzzer"] = config.use_buzzer;
  json["rfid_enabled"] = config.rfid_enabled;

  String response;
  serializeJson(json, response);
  configServer.send(200, "application/json", response);
}

void handleSaveConfig() {
  if (configServer.method() != HTTP_POST) return;

  String body = configServer.arg("plain");
  DynamicJsonDocument json(1024);
  DeserializationError error = deserializeJson(json, body);

  if (error) {
    configServer.send(400, "application/json", "{\"success\":false,\"message\":\"JSON error\"}");
    return;
  }

  memset(&config, 0, sizeof(config));
  strlcpy(config.wifi_ssid, json["ssid"].as<String>().c_str(), sizeof(config.wifi_ssid));
  strlcpy(config.wifi_password, json["password"].as<String>().c_str(), sizeof(config.wifi_password));
  strlcpy(config.mqtt_broker, json["mqtt_broker"].as<String>().c_str(), sizeof(config.mqtt_broker));
  config.mqtt_port = json["mqtt_port"].as<int>();
  strlcpy(config.device_id, json["device_id"].as<String>().c_str(), sizeof(config.device_id));
  config.led_config = json["led_config"].as<int>();
  config.use_buzzer = json["use_buzzer"].as<bool>();
  config.rfid_enabled = json["rfid_enabled"].as<bool>();

  saveConfigToFlash();

  preferences.begin("rfid_access", true);
  byte savedConfig[sizeof(config)];
  preferences.getBytes("config", savedConfig, sizeof(config));
  preferences.end();

  if (memcmp(&config, savedConfig, sizeof(config)) == 0) {
    configServer.send(200, "application/json", "{\"success\":true,\"message\":\"Settings saved! Rebooting...\"}");
  } else {
    configServer.send(200, "application/json", "{\"success\":false,\"message\":\"Save error\"}");
    return;
  }

  delay(3000);
  ESP.restart();
}

void handleTestDoor() {
  openDoor(false);
  delay(2000);
  closeDoor(true);

  configServer.send(200, "application/json", "{\"success\":true,\"message\":\"Door test complete\"}");
}

void startConfigPortal() {
  WiFi.softAP("ESP32_RFID_Setup", NULL);

  configServer.on("/", handleConfigPage);
  configServer.on("/getconfig", handleGetConfig);
  configServer.on("/saveconfig", HTTP_POST, handleSaveConfig);
  configServer.on("/testdoor", handleTestDoor);

  configServer.begin();
  currentState = 1;

  while (configMode) {
    configServer.handleClient();
    delay(10);
  }
}

void setupWiFi() {
  currentState = 2;

  WiFi.disconnect(true);
  delay(1000);
  WiFi.mode(WIFI_STA);
  WiFi.begin(config.wifi_ssid, config.wifi_password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    attempts++;

    if (indicator) {
      static bool ledState = false;
      ledState = !ledState;
      if (config.led_config >= 1) {
        digitalWrite(RED_LED_PIN, ledState ? HIGH : LOW);
      }
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    if (indicator) {
      digitalWrite(RED_LED_PIN, LOW);
      if (config.led_config == 2) {
        digitalWrite(GREEN_LED_PIN, HIGH);
        delay(500);
        digitalWrite(GREEN_LED_PIN, LOW);
      }
    }
  } else {
    if (indicator) {
      for (int i = 0; i < 5; i++) {
        digitalWrite(RED_LED_PIN, HIGH);
        delay(200);
        digitalWrite(RED_LED_PIN, LOW);
        delay(200);
      }
    }

    currentState = 9;
    delay(3000);
    configMode = true;
    startConfigPortal();
  }
}

void setupMQTT() {
  currentState = 3;

  mqttClient.setServer(config.mqtt_broker, config.mqtt_port);
  mqttClient.setCallback(mqttCallback);

  String clientId = String(config.device_id) + "_" + String(random(0xffff), HEX);

  if (mqttClient.connect(clientId.c_str())) {
    mqttConnected = true;

    mqttClient.subscribe("access/commands");
    mqttClient.subscribe("access/responses");

    sendStatusToMQTT("online");
    sendDeviceInfo();

    currentState = 4;
  } else {
    mqttConnected = false;
    currentState = 9;
  }
}

bool factoryResetRequested = false;
unsigned long resetRequestTime = 0;

void checkSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();

    if (command == "factory_reset" || command == "reset" || command == "сброс") {
      factoryResetRequested = true;
      resetRequestTime = millis();

    } else if (command == "yes" && factoryResetRequested) {
      performFactoryReset();

    } else if (command == "no" && factoryResetRequested) {
      factoryResetRequested = false;

    } else if (command == "status") {
      Serial.printf("WiFi: %s\n", WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected");
      Serial.printf("MQTT: %s\n", mqttClient.connected() ? "Connected" : "Disconnected");
      Serial.printf("Door: %s\n", doorOpen ? "Open" : "Closed");
      Serial.printf("Schedule: %s\n", doorOpenedBySchedule ? "Yes" : "No");
      Serial.printf("Evacuation: %s\n", evacuationMode ? "ON" : "OFF");
      Serial.printf("Lockdown: %s\n", lockdownMode ? "ON" : "OFF");
      Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());

    } else if (command == "help" || command == "?" || command == "помощь") {
      Serial.println("factory_reset - factory reset");
      Serial.println("status - device status");
      Serial.println("open - open door");
      Serial.println("close - close door");
      Serial.println("evacuation - toggle evacuation mode");
      Serial.println("lockdown - toggle lockdown mode");
      Serial.println("reboot - reboot");
      Serial.println("config - show config");
      Serial.println("help - this help");

    } else if (command == "open") {
      openDoor(false);

    } else if (command == "close") {
      closeDoor(true);

    } else if (command == "evacuation" || command == "evac") {
      evacuationMode = !evacuationMode;
      lockdownMode = false;
      
      if (evacuationMode) {
        openDoor(false);
      } else {
        closeDoor(true);
      }
      
    } else if (command == "lockdown" || command == "lock") {
      lockdownMode = !lockdownMode;
      evacuationMode = false;
      
      if (lockdownMode) {
        closeDoor(true);
      }
      
    } else if (command == "reboot") {
      delay(1000);
      ESP.restart();

    } else if (command == "config") {
      Serial.printf("SSID: %s\n", config.wifi_ssid);
      Serial.printf("MQTT: %s:%d\n", config.mqtt_broker, config.mqtt_port);
      Serial.printf("Device ID: %s\n", config.device_id);
      Serial.printf("LED config: %d\n", config.led_config);
      Serial.printf("Buzzer: %s\n", config.use_buzzer ? "On" : "Off");
      Serial.printf("RFID: %s\n", config.rfid_enabled ? "On" : "Off");

    } else if (factoryResetRequested) {
    }
  }

  if (factoryResetRequested && millis() - resetRequestTime > 10000) {
    factoryResetRequested = false;
  }
}

void performFactoryReset() {
  if (indicator) {
    for (int i = 0; i < 10; i++) {
      digitalWrite(RED_LED_PIN, HIGH);
      if (config.led_config == 2) digitalWrite(GREEN_LED_PIN, HIGH);
      delay(200);
      digitalWrite(RED_LED_PIN, LOW);
      if (config.led_config == 2) digitalWrite(GREEN_LED_PIN, LOW);
      delay(200);
    }
  }

  if (config.use_buzzer) {
    for (int i = 0; i < 3; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(300);
      digitalWrite(BUZZER_PIN, LOW);
      delay(200);
    }
  }

  preferences.begin("rfid_access", false);
  preferences.clear();
  preferences.end();

  for (int i = 3; i > 0; i--) {
    delay(1000);
  }

  ESP.restart();
}

void resetDoorState() {
  digitalWrite(RELAY_PIN, LOW);
  pinMode(RELAY_PIN, INPUT);
  
  doorOpen = false;
  doorOpenedBySchedule = false;
  doorOpenTime = 0;
  currentState = 4;
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  loadConfigFromFlash();

  if (strlen(config.wifi_ssid) == 0) {
    configMode = true;
  } else {
    configMode = false;
  }

  pinMode(GREEN_LED_PIN, OUTPUT);
  digitalWrite(GREEN_LED_PIN, LOW);
  pinMode(RED_LED_PIN, OUTPUT);
  digitalWrite(RED_LED_PIN, LOW);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  pinMode(EXIT_BUTTON_PIN, INPUT_PULLUP);
  pinMode(RELAY_PIN, INPUT);
  digitalWrite(RELAY_PIN, LOW);

  if (strlen(config.wifi_ssid) == 0) {
    configMode = true;
  }

  if (configMode) {
    startConfigPortal();
    return;
  }

  indicator = new IndicatorSystem(config.led_config, config.use_buzzer);

  if (config.rfid_enabled) {
    if (!initRFID()) {
    }
  }

  setupWiFi();
  if (configMode) return;

  setupMQTT();
}

void loop() {
  if (configMode) {
    configServer.handleClient();
    if (indicator) {
      indicator->indicateState(currentState);
    }
    return;
  }
  
  checkSerialCommands();
  
  if (indicator && millis() - lastIndicationUpdate > 100) {
    indicator->indicateState(currentState);
    lastIndicationUpdate = millis();
  }

  if (!mqttClient.connected()) {
    static unsigned long lastReconnectAttempt = 0;
    if (millis() - lastReconnectAttempt > 30000) {
      lastReconnectAttempt = millis();
      setupMQTT();
    }
  } else {
    mqttClient.loop();
  }

  static unsigned long lastButton = 0;
  if (digitalRead(EXIT_BUTTON_PIN) == LOW && millis() - lastButton > 1000) {
    lastButton = millis();

    if (lockdownMode) {
      if (mqttClient.connected()) {
        DynamicJsonDocument doc(256);
        doc["event_type"] = "exit_button_blocked";
        doc["device_id"] = config.device_id;
        doc["timestamp"] = millis();
        doc["message"] = "Exit button in lockdown";
        
        char buffer[256];
        serializeJson(doc, buffer);
        mqttClient.publish("access/events", buffer);
      }
      
      if (config.use_buzzer) {
        for (int i = 0; i < 3; i++) {
          digitalWrite(BUZZER_PIN, HIGH);
          delay(200);
          digitalWrite(BUZZER_PIN, LOW);
          delay(150);
        }
      }
      return;
    }

    if (mqttClient.connected()) {
      DynamicJsonDocument doc(256);
      doc["event_type"] = evacuationMode ? "exit_button_evacuation" : "exit_button";
      doc["device_id"] = config.device_id;
      doc["timestamp"] = millis();
      doc["message"] = evacuationMode ? "Exit button in evacuation" : "Exit button pressed";
      
      char buffer[256];
      serializeJson(doc, buffer);
      mqttClient.publish("access/events", buffer);
    }

    openDoor(false);
  }

  static String lastCardUID = "";
  String cardUID = readRFIDCard();

  if (cardUID.length() > 0) {
    if (cardUID != lastCardUID || millis() - lastCardSuccess > 3000) {
      lastCardUID = cardUID;
      lastCardSuccess = millis();
      processCard(cardUID);
    }
  } else {
    if (millis() - lastCardSuccess > 2000) {
      lastCardUID = "";
    }
  }

  if (doorOpen && !doorOpenedBySchedule && !evacuationMode && millis() - doorOpenTime > DOOR_OPEN_DURATION) {
    closeDoor(true);
  }
  
  if (doorOpen && millis() - doorOpenTime > 60000) {
    if (!evacuationMode) {
      closeDoor(true);
    }
  }

  static unsigned long lastRFIDCheck = 0;
  if (config.rfid_enabled && millis() - lastRFIDCheck > 30000) {
    lastRFIDCheck = millis();
    if (!lockdownMode && !evacuationMode) {
      byte version = mfrc522.PCD_ReadRegister(0x37);
      if (version == 0x00 || version == 0xFF) {
        initRFID();
      }
    }
  }

  delay(50);
}
