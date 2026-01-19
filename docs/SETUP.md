# Setup

## Hardware
- BBC micro:bit v2 devices (minimum 2: 1 wearable + 1 hub)
- USB data cables
- Optional piezo buzzer on P0 and GND for audio alerts
- Optional battery pack for wearables

## Software
- micro:bit MicroPython runtime for v2 hardware
- Flashing tool: Mu editor or uflash CLI
- Serial monitor (Mu, screen, minicom, or your IDE)

## Flashing workflow

### Option A: Mu editor
1. Install Mu and download the MicroPython runtime for micro:bit v2.
2. Connect a micro:bit; it appears as a removable drive.
3. Open the appropriate .py file and click Flash.

### Option B: uflash CLI
1. Install uflash (pip install uflash).
2. Flash a wearable/node: `uflash wearable_device.py`
3. Flash the hub: `uflash central_hub.py`

## Device configuration
1. Set a unique DEVICE_ID in wearable_device.py for each wearable/node.
2. Keep RADIO_GROUP the same on all devices.
3. Keep HUB_ID at 0 unless you change it everywhere.

## Running and validation
1. Connect the hub to USB and open a serial monitor at 115200.
2. Power on wearables; they show their DEVICE_ID on boot.
3. The hub displays a count of active devices or a dash if none are seen.

## Test mode
- Hold button A on a wearable during startup to enter test mode.
- Button A simulates a fall; Button B shows acceleration.
- Press A+B to exit test mode.

## Notes
- Use `wearable_device.py` as the wearable/node script.
- The current code toggles pin0 for audio alerts; attach a buzzer if you want sound.
- GPS and battery readings are simulated unless you add hardware and code changes.
