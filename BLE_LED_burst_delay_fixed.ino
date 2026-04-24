#include <ArduinoBLE.h>

// ---------------- Pins ----------------
const int motor1 = A0;
const int motor2 = A1;

// ---------------- User settings ----------------
const uint8_t DUTY_CYCLE = 50;      // % ON time
const unsigned long REST_MS = 500;  // rest time after burst

// ---------------- BLE state ----------------
// 0=5Hz, 1=10Hz, 2=20Hz, 3=OFF
volatile uint8_t mode = 3;
int freq = 0;

// ---------------- Pattern state ----------------
enum Phase {
  BURSTING,
  RESTING
};
Phase phase = BURSTING;

unsigned long previousMotorMicros = 0;
bool motorIsOn = false;

int pulseCount = 0;
unsigned long restStartMillis = 0;

// ---------------- BLE UUIDs (custom) ----------------
BLEService vibService("19B10000-E8F2-537E-4F6C-D104768A1214");
BLEByteCharacteristic modeChar(
  "19B10001-E8F2-537E-4F6C-D104768A1214",
  BLERead | BLEWriteWithoutResponse);

// ---------------- Helpers ----------------
void startMotors() {
  digitalWrite(motor1, HIGH);
  digitalWrite(motor2, HIGH);
}

void stopMotors() {
  digitalWrite(motor1, LOW);
  digitalWrite(motor2, LOW);
}

void updateFreqFromMode() {
  switch (mode) {
    case 0: freq = 5; break;
    case 1: freq = 10; break;
    case 2: freq = 20; break;
    default: freq = 0; break;  // OFF
  }
}

void startBurst() {
  phase = BURSTING;
  pulseCount = 0;
  motorIsOn = false;
  previousMotorMicros = micros();
  stopMotors();
}

void resetPattern() {
  startBurst();
}

// One continuous burst of 2*freq pulses, then rest
void runPatternStep() {
  // OFF => stay off
  if (freq == 0) {
    stopMotors();
    return;
  }

  // REST after full burst
  if (phase == RESTING) {
    stopMotors();
    if (millis() - restStartMillis >= REST_MS) {
      startBurst();
    }
    return;
  }

  // BURSTING: exactly 2*freq pulses
  unsigned long nowUs = micros();
  unsigned long period_us = 1000000UL / (unsigned long)freq;
  unsigned long on_us = (period_us * (unsigned long)DUTY_CYCLE) / 100UL;
  unsigned long off_us = period_us - on_us;

  if (motorIsOn) {
    if (nowUs - previousMotorMicros >= on_us) {
      motorIsOn = false;
      previousMotorMicros = nowUs;
      stopMotors();
    }
  } else {
    if (nowUs - previousMotorMicros >= off_us) {
      motorIsOn = true;
      previousMotorMicros = nowUs;
      startMotors();

      pulseCount++;  // count ONE pulse

      if (pulseCount >= (2 * freq)) {
        stopMotors();
        motorIsOn = false;
        phase = RESTING;
        restStartMillis = millis();
      }
    }
  }
}

// ---------------- Setup ----------------
void setup() {
  pinMode(motor1, OUTPUT);
  pinMode(motor2, OUTPUT);

  stopMotors();

  Serial.begin(9600);
  delay(200);

  if (!BLE.begin()) {
    Serial.println("BLE failed to start");
    while (1) delay(1000);
  }

  BLE.setLocalName("Somato");
  BLE.setAdvertisedService(vibService);

  vibService.addCharacteristic(modeChar);
  BLE.addService(vibService);

  modeChar.writeValue(mode);  // default OFF
  updateFreqFromMode();
  resetPattern();

  BLE.advertise();
  Serial.println("Advertising as: Somato2");
}

// ---------------- Main loop ----------------
void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());

    resetPattern();  // start fresh on connect

    while (central.connected()) {
      BLE.poll();

      if (modeChar.written()) {
        uint8_t m = modeChar.value();
        if (m > 3) m = 3;
        mode = m;

        updateFreqFromMode();
        resetPattern();  // apply immediately

        Serial.print("Mode set to: ");
        Serial.print(mode);
        Serial.print("  Freq: ");
        Serial.println(freq);
      }

      runPatternStep();
    }

    stopMotors();
    resetPattern();
    Serial.println("Disconnected");
  } else {
    stopMotors();
  }
}