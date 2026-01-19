# MicroBit Elderly Fall Detection System

A mesh-networked fall detection system using BBC MicroBit V2 devices. Designed to detect falls in elderly users and dispatch alerts to a central monitoring station.

## Features

- **Intelligent Fall Detection**: Uses accelerometer spike + stillness pattern to detect real falls while ignoring normal activities
- **Simulated GPS Tracking**: Location data included with alerts (ready for external GPS module integration)
- **Mesh Network Routing**: If direct communication fails, alerts route through other wearables
- **Battery Monitoring**: Continuous battery level reporting to central hub
- **Visual & Audio Alerts**: Immediate feedback on both wearable and hub

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MESH NETWORK                             │
│                                                                 │
│  ┌─────────┐        ┌─────────┐        ┌─────────┐              │
│  │Wearable │◄──────►│Wearable │◄──────►│Wearable │              │
│  │   #1    │        │   #2    │        │   #3    │              │
│  │(Elderly)│        │ (Relay) │        │(Elderly)│              │
│  └────┬────┘        └────┬────┘        └────┬────┘              │
│       │                  │                  │                   │
│       └──────────────────┼──────────────────┘                   │
│                          │                                      │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │ CENTRAL HUB │──► Serial Monitor             │
│                   │  (Station)  │──► External Systems           │
│                   └─────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Hardware Requirements

- **Minimum**: 2 BBC MicroBit V2 (1 wearable + 1 hub)
- **Recommended**: 4+ BBC MicroBit V2 (for mesh network testing)

## Quick Start

### 1. Flash the Devices

**For Wearable Devices:**
```python
# In wearable_device.py, change DEVICE_ID for each unit:
DEVICE_ID = 1  # Wearable 1
DEVICE_ID = 2  # Wearable 2
# etc.
```

Flash `wearable_device.py` to each wearable MicroBit.

**For Central Hub:**
Flash `central_hub.py` to the hub MicroBit.

### 2. Connect the Hub

Connect the hub MicroBit to a computer via USB to monitor serial output.

### 3. Test Communication

1. Power on all devices
2. Hub displays device count as wearables connect
3. Enter test mode on wearable (hold Button A during startup)
4. Press Button A to simulate a fall
5. Verify hub receives and displays alert

## Fall Detection Algorithm

The system uses a two-phase detection algorithm:

```
Phase 1: Impact Detection
┌─────────────────────────────────────────────────┐
│  Continuous Monitoring                          │
│  ┌───────────────────────────────────────────┐  │
│  │ Calculate acceleration magnitude:         │  │
│  │ magnitude = √(x² + y² + z²)               │  │
│  │                                           │  │
│  │ If magnitude > IMPACT_THRESHOLD (2500mg)  │──┼──► Enter Phase 2
│  │ Then: Potential fall detected             │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

Phase 2: Stillness Confirmation
┌─────────────────────────────────────────────────┐
│  Post-Impact Monitoring (2 seconds)             │
│  ┌───────────────────────────────────────────┐  │
│  │ If |magnitude - 1000mg| < 150mg           │  │
│  │ For duration > STILLNESS_DURATION         │──┼──► FALL CONFIRMED
│  │ Then: Person is lying still               │  │
│  │                                           │  │
│  │ If movement resumes: Cancel alert         │──┼──► Return to Phase 1
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

This two-phase approach distinguishes real falls from:
- **Running/Walking**: Continuous movement, no sustained stillness
- **Sitting down quickly**: Lower impact, immediate movement after
- **Stumbling with recovery**: Impact but quick movement resumption

## Message Protocol

All messages follow this format:
```
TYPE|SENDER_ID|TARGET_ID|DATA|HOP_COUNT
```

### Message Types

| Type   | Description              | Data Format                    |
|--------|--------------------------|--------------------------------|
| FALL   | Fall alert               | GPS:lat,lon;ACC:magnitude      |
| BATT   | Battery status           | percentage (0-100)             |
| HBEAT  | Heartbeat (keep-alive)   | timestamp                      |
| ACK    | Acknowledgment           | OK                             |
| RELAY  | Message for relay        | (original message data)        |

## Mesh Network Failover

```
Normal Operation:
    Wearable ─────────────────► Hub
              Direct message

Failover (Hub unreachable):
    Wearable ─────► Relay Node ─────► Hub
              Detects failure,    Forwards
              sends via peer      message
```

**Failover triggers when:**
- 3 consecutive heartbeats go unacknowledged
- Timeout: 15 seconds (3 × 5 second heartbeat interval)

**Hop limit:** Messages relay through maximum 3 intermediate nodes to prevent infinite loops.

## Configuration Parameters

### Wearable Device (`wearable_device.py`)

```python
# Device Identity
DEVICE_ID = 1                    # Unique ID (1, 2, 3, etc.)

# Fall Detection Tuning
IMPACT_THRESHOLD = 2500          # mg - spike detection
STILLNESS_THRESHOLD = 150        # mg - deviation from 1g
STILLNESS_DURATION_MS = 2000     # ms - stillness window

# Network
RADIO_GROUP = 42                 # Must match all devices
RADIO_POWER = 7                  # 0-7 (7 = max range)
HEARTBEAT_INTERVAL_MS = 5000     # Heartbeat frequency
```

### Central Hub (`central_hub.py`)

```python
# Timeouts
DEVICE_TIMEOUT_MS = 20000        # Device offline threshold
ALERT_DISPLAY_MS = 10000         # Alert display duration

# Network
RADIO_GROUP = 42                 # Must match all devices
```

## Display Icons

### Wearable Device

| Icon | Meaning |
|------|---------|
| ❤ (small heart) | Normal operation, hub connected |
| 😕 (confused) | Hub connection lost |
| ! | Impact detected, monitoring stillness |
| ☹ (sad) | Fall confirmed, alert sent |
| 1-9 | Device ID (shown on startup) |

### Central Hub

| Icon | Meaning |
|------|---------|
| 1-9 | Number of connected devices |
| - | No devices connected |
| ! | Pending unacknowledged alert |
| 💀 (skull) | Active fall alert (flashing) |
| ✓ | Alert acknowledged |

## Button Functions

### Wearable (Normal Mode)
- No button functions (automatic operation)

### Wearable (Test Mode - hold A on startup)
- **Button A**: Simulate fall alert
- **Button B**: Show current acceleration
- **A + B**: Exit test mode

### Central Hub
- **Button A**: Acknowledge current alert
- **Button B**: Print system status to serial

## Extending the System

### Adding Real GPS

Replace the simulated GPS function in `wearable_device.py`:

```python
from microbit import uart, pin1, pin2

def setup_gps():
    uart.init(baudrate=9600, tx=pin1, rx=pin2)

def get_real_gps():
    """Parse NMEA sentences from GPS module"""
    if uart.any():
        line = uart.readline()
        if line and line.startswith(b'$GPGGA'):
            # Parse GPGGA sentence
            parts = line.decode().split(',')
            lat = convert_nmea_to_decimal(parts[2], parts[3])
            lon = convert_nmea_to_decimal(parts[4], parts[5])
            return (lat, lon)
    return None
```

### Adding Real Battery Monitoring

Connect battery to ADC pin and modify:

```python
def get_real_battery_level():
    """Read actual battery voltage via ADC"""
    raw_value = pin1.read_analog()  # 0-1023
    voltage = (raw_value / 1023) * 3.3  # Convert to voltage
    
    # Map voltage to percentage (adjust for your battery)
    # Example: 3.0V = 0%, 4.2V = 100% for LiPo
    percentage = ((voltage - 3.0) / 1.2) * 100
    return max(0, min(100, percentage))
```

### Integration with External Systems

The hub outputs alerts via serial. Connect to:
- Raspberry Pi for SMS/email notifications
- Home automation systems
- Emergency dispatch systems

```python
# Example external monitoring (on Raspberry Pi)
import serial

ser = serial.Serial('/dev/ttyACM0', 115200)
while True:
    line = ser.readline().decode()
    if 'FALL ALERT' in line:
        send_sms_alert(line)
        notify_emergency_services(line)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Devices not communicating | Check RADIO_GROUP matches on all devices |
| Too many false alerts | Increase IMPACT_THRESHOLD (try 3000-3500) |
| Missing real falls | Decrease IMPACT_THRESHOLD (try 2000) |
| Relay not working | Ensure intermediate device is in range of both endpoints |
| Hub shows wrong device count | Wait for heartbeat cycle (5 seconds) |

## File Structure

```
microbit_fall_detection/
├── README.md              # This file
├── wearable_device.py     # Wearable MicroBit code
├── central_hub.py         # Central hub MicroBit code
└── TEST_SCENARIOS.md      # Comprehensive testing guide
```

## License

MIT License

## Safety Disclaimer

This is a prototype/educational project. For actual elderly care applications:
- Conduct thorough testing with target users
- Implement redundant alert mechanisms
- Consider professional medical alert systems
- Ensure backup communication methods
- Follow local regulations for medical devices
