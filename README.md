## Arduino Firmware (BLE_LED_burst_delay_fixed.ino)

### Overview
The Arduino sketch implements a BLE-controlled motor/vibration pattern generator. It connects via BLE and responds to mode commands to produce configurable burst patterns with rest periods.

### Pin Configuration
- **Motor 1**: Pin A0
- **Motor 2**: Pin A1

### Operating Modes
The device supports 4 modes via BLE characteristic (UUID: 19B10001-E8F2-537E-4F6C-D104768A1214):

| Mode | Frequency | Description |
|------|-----------|-------------|
| 0    | 5 Hz      | LOW frequency bursts |
| 1    | 10 Hz     | MEDIUM frequency bursts |
| 2    | 20 Hz     | HIGH frequency bursts |
| 3    | OFF       | Motors disabled |

### Burst Pattern Behavior
- **Pattern**: Generates exactly `2 × frequency` pulses per burst cycle
- **Duty cycle**: 50% ON time (configurable via `DUTY_CYCLE` constant)
- **Rest period**: 500ms between bursts (configurable via `REST_MS` constant)

### Key Features
- Microsecond-precision PWM timing for accurate frequency control
- BLE write-without-response characteristic for low-latency mode changes
- Two-phase state machine: BURSTING → RESTING
- Pulse counting to ensure exact burst lengths
- Immediate pattern reset on mode changes or device connection

### Configuration
Edit these constants in the sketch to customize behavior:
```cpp
const uint8_t DUTY_CYCLE = 50;      // % ON time
const unsigned long REST_MS = 500;  // rest time after burst in milliseconds
```

### BLE Service Details
- **Service UUID**: 19B10000-E8F2-537E-4F6C-D104768A1214
- **Device Name**: Somato
- **Characteristic UUID**: 19B10001-E8F2-537E-4F6C-D104768A1214
- **Characteristic Properties**: Read, Write Without Response
