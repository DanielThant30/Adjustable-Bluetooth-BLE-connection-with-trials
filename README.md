## Arduino Firmware 

### Overview
The Arduino sketch implements a BLE-controlled motor/vibration pattern generator. It connects via BLE and responds to mode commands to produce configurable burst patterns with rest periods.

### Pin Configuration
- **Motor 1**: Pin A0
- **Motor 2**: Pin A1

### Operating Modes
The device supports 4 modes via BLE characteristic (UUID: 19B10001-E8F2-537E-4F6C-D104768A1214):

| Mode | Frequency | Description |
|------|-----------|-------------|
| 0    | LOW      | LOW bursts |
| 1    | MED     | MEDIUM bursts |
| 2    | HIGH     | HIGH bursts |
| 3    | OFF       | Motors disabled |


### Key Features
- Microsecond-precision PWM timing for accurate frequency control
- BLE write-without-response characteristic for low-latency mode changes
- Immediate pattern reset on mode changes or device connection

### Configuration
Edit these constants in the sketch to customize behavior:
```cpp
const uint8_t DUTY_CYCLE = 50;      // % ON time
const unsigned long REST_MS = 500;  // rest time after burst in milliseconds
```

### BLE Service Details
- **Service UUID**: 19B10000-E8F2-537E-4F6C-D104768A1214
- **Device Name**: Somato (Change-it-to-your-use)
- **Characteristic UUID**: 19B10001-E8F2-537E-4F6C-D104768A1214
- **Characteristic Properties**: Read, Write Without Response

- # Adjustable Trials BLE Controller

A Python desktop application for running randomized sensory stimulation trials over Bluetooth Low Energy (BLE). Designed for research or clinical contexts where a BLE-connected device (e.g., an Arduino running ArduinoBLE) delivers vibrotactile or other stimulation at configurable frequencies.

---

## Features

- **BLE connectivity** — Scans for, connects to, and disconnects from a named BLE peripheral
- **Manual stimulation control** — Trigger stimulation at low, medium and high intensity vibrations, or turn it off
- **Randomized trial generation** — Generates a balanced, shuffled trial sequence across all four conditions (5 Hz, 10 Hz, 20 Hz, OFF)
- **Trial-by-trial navigation** — Step through trials one at a time with visual progress tracking
- **Connection monitoring** — Background monitor detects unexpected disconnections and distinguishes them from intentional disconnects

---

## Requirements

### Python packages

```
pip install bleak pandas
```

`tkinter` is included with most standard Python installations.

### Hardware

- A BLE peripheral advertising the name **`Somato`**
- The device must expose a writable GATT characteristic with UUID:
  ```
  19b10001-e8f2-537e-4f6c-d104768a1214
  ```

---

## BLE Protocol

The app sends a single byte to the write characteristic to set the stimulation mode:

| Byte value | Mode   |
|-----------|--------|
| `0x00`    | Low   |
| `0x01`    | Med  |
| `0x02`    | High  |
| `0x03`    | OFF    |

---

## Central Device Side



### 1. Connect to the device

Click **Connect BLE**. The status label will cycle through `SCANNING...` → `CONNECTING...` → `CONNECTED` (or an error state if the device is not found).

### 2. Manual stimulation (optional)

Use the buttons to send modes directly to the device at any time.

### 3. Run a trial sequence

1. Enter the desired number of trials in the **Total Trials** field (must be a multiple of 4; the app will round down automatically). Default is 20.
2. Click **Generate** to create a balanced, randomized trial order.
3. Click **Stimulate trial** to begin the first trial — the mode is sent to the device and the trial is marked in the order display.
4. Click **Next** to advance to the next trial (this also immediately sends the next mode).
5. Click **Ending** at any time to stop stimulation and return to idle, or let the sequence complete automatically.

---

## UI Overview

| Control | Description |
|---|---|
| **Connect / Disconnect BLE** | Manage the BLE connection |
| **BLE Status label** | Live connection status, polled every 500 ms |
| **Low / Med / High / OFF** | Manual mode buttons |
| **Total Trials entry** | Set trial count (multiple of 4) |
| **Generate** | Build and display the randomized trial order |
| **Stimulate trial** | Send the current trial's mode and mark it as active |
| **Next** | Send the next trial's mode |
| **Ending** | Send OFF and halt the sequence |
| **Trial order display** | Shows all trial modes; completed trials appear with strikethrough |

---

## Connection States

| Status message | Meaning |
|---|---|
| `DISCONNECTED` | No active connection; intentional state |
| `SCANNING...` | Searching for the target device |
| `CONNECTING...` | Found the device; establishing connection |
| `CONNECTED` | Successfully connected |
| `DISCONNECTING...` | Disconnect in progress |
| `POWER CUT` | Unexpected loss of connection detected |
| `Missing...` | Scan completed but target device not found |
| `BLE SCAN FAILED` | Bluetooth scan error |

---

## Notes

- Trial count is always rounded down to the nearest multiple of 4, since each of the four conditions appears an equal number of times.
- The app runs a dedicated asyncio event loop on a background thread so that BLE operations never block the UI.
- A background monitor coroutine checks the connection every second and updates the status if an unexpected disconnection is detected.
