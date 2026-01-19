# MicroBit Elderly Fall Detection System

Prototype fall detection system using BBC micro:bit v2 devices. Wearables detect a fall-like acceleration pattern and send alerts to a central hub over the micro:bit radio.

## Scripts
- `central_hub.py`: hub with ACKs, hop-aware relay handling, and status display.
- `wearable_device.py`: primary wearable/node script with heartbeat, relay handling, and fall detection.
- `data_capture_node.py`: capture accelerometer data over serial for tuning.

## Status
- Prototype/educational project; not a medical device.
- GPS and battery reporting are simulated.
- Mesh relay and heartbeat logic are experimental (see docs/LIMITATIONS.md).

## Quick start
1. Set a unique DEVICE_ID in `wearable_device.py` for each wearable/node.
2. Flash `wearable_device.py` to each wearable and `central_hub.py` to the hub.
3. Connect the hub to USB and open a serial monitor at 115200.
4. Optional test mode: hold button A on a wearable at boot, then press A to simulate a fall.

Detailed setup and flashing instructions: docs/SETUP.md.

## Documentation
- docs/SETUP.md - prerequisites and flashing steps.
- docs/ARCHITECTURE.md - component and data flow overview.
- docs/PROTOCOL.md - radio message format and size notes.
- docs/CONFIGURATION.md - tunable parameters.
- docs/DATA_CAPTURE.md - collecting accelerometer traces for tuning.
- docs/TEST_SCENARIOS.md - manual test checklist (draft).
- docs/SAFETY.md - safety and use limitations.
- docs/LIMITATIONS.md - known gaps in the current prototype.

## Repository layout
```
microbit_project/
├── README.md
├── central_hub.py
├── wearable_device.py
├── data_capture_node.py
└── docs/
    ├── ARCHITECTURE.md
    ├── CONFIGURATION.md
    ├── DATA_CAPTURE.md
    ├── LIMITATIONS.md
    ├── PROTOCOL.md
    ├── SAFETY.md
    ├── SETUP.md
    └── TEST_SCENARIOS.md
```

## License
No license specified.
