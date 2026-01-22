# MicroBit Elderly Fall Detection System

Prototype fall detection system using BBC micro:bit v2 devices. Wearables detect a fall-like acceleration pattern and send alerts to a central hub over the micro:bit radio.

## Scripts
- `central_hub.py`: central hub (ACKs, relay handling, status display, serial output).
- `wearable_device.py`: wearable/node (fall detection, heartbeat, optional relay, simulated GPS/battery).
- `data_capture_node.py`: capture accelerometer data over serial (CSV) for tuning.

## Status
- Prototype/educational project; not a medical device.
- GPS and battery reporting are simulated.
- Mesh relay and heartbeat logic are experimental (see docs/LIMITATIONS.md).

## Quick start
1. Set a unique DEVICE_ID in `wearable_device.py` for each wearable/node.
2. Flash `wearable_device.py` to each wearable and `central_hub.py` to the hub.
3. Connect the hub to USB and open a serial monitor at 115200.
4. Optional test mode: hold button A on a wearable at boot, then press A to simulate a fall.
5. Acknowledge alerts on the hub with button B (button A prints status).

Detailed setup and flashing instructions: docs/SETUP.md.

## Installation and flashing (Windows/macOS/Linux)
- Prereqs: BBC micro:bit v2 boards, USB data cables, Python 3 with pip (for `uflash`) or Mu editor installed.
- Configure each wearable first: set a unique `DEVICE_ID` in `wearable_device.py`; keep `RADIO_GROUP` and `HUB_ID` consistent across devices.
- Windows: install Python (enable "Add to PATH") ; connect the micro:bit (shows as a drive) and run `pip install uflash` followed by `uflash central_hub.py` (hub) or `uflash wearable_device.py` (wearables).
- macOS: install Python 3 (brew or python.org), `pip install uflash`, then `uflash central_hub.py` or `uflash wearable_device.py`; verify the board appears as `/dev/tty.usbmodem*` for serial monitoring (e.g., `screen /dev/tty.usbmodem* 115200`).
- Linux: `python3 -m pip install --user uflash`, ensure your user can access USB/serial devices (dialout/plugdev as needed), then `uflash central_hub.py` or `uflash wearable_device.py`; typical serial port is `/dev/ttyACM0` at 115200.
- Linux: 'pipx install uflash' or 'pip install uflash', then run 'pipx run uflash wearable_device.py' or 'uflash wearable_device.py'
- After flashing, connect the hub over USB, open a serial monitor at 115200, power on wearables, and trigger test mode (hold A on boot) to verify radio/alert behavior before field use.

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
time toplay marvel rivals
