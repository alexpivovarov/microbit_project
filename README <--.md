This file mirrors `README.md` (it’s easy to accidentally open the wrong one).

---

# MicroBit Elderly Fall Detection System

A prototype fall-detection demo using BBC micro:bit v2 devices:
**wearables (sensors)** detect a fall-like acceleration spike and send it over **micro:bit radio** to a **hub**, which forwards it to your computer over **USB serial**.

> This is an educational/prototype project and **not a medical device**.

In this README, **flash** means “copy the program onto the micro:bit so it runs”.

## What you need (before you start)
1. **Hardware**
   - 2× BBC micro:bit v2 boards (minimum): **1 hub + 1 wearable**
   - USB **data** cables (some “charge-only” cables won’t work)
   - (Optional) small buzzer: connect to **P0** and **GND**
2. **Software**
   - A way to flash MicroPython to micro:bits: **Mu editor** *or* **Python + uflash**
   - A serial viewer: Mu, your IDE, `screen`/`minicom`, etc.
   - (Optional) for the live graphs: Python packages `pyserial` and `matplotlib`

## Setup (do these steps in order)
1. **Pick your “hub” micro:bit**
   - This is the one that stays plugged into your computer.
2. **Flash the hub code**
   - Flash `central_hub.py` onto the hub micro:bit.
   - Mu: open `central_hub.py` and click **Flash**
   - uflash: `python -m pip install uflash` then `uflash central_hub.py`
3. **Set up each wearable (important)**
   - Open `wearable_device.py`
   - Change `DEVICE_ID` so every wearable is unique (1, 2, 3…)
   - Keep `RADIO_GROUP` and `HUB_ID` the same across all devices
4. **Flash the wearable code**
   - Flash `wearable_device.py` onto each wearable micro:bit.
   - Mu: open `wearable_device.py` and click **Flash**
   - uflash: `uflash wearable_device.py`
5. **Plug in the hub and open serial**
   - Connect the hub to USB and open a serial monitor at **115200 baud**.
6. **Power on the wearables**
   - Each wearable shows its ID on the LED display.
   - The hub should start printing messages when it receives data.
7. **(Optional) Run the desktop live monitor (graphs)**
   - Install dependencies: `python -m pip install pyserial matplotlib`
   - Run: `python desktop_client.py`

## Quick test (no real falling required)
1. On a wearable: **hold button A while powering on / resetting** to enter test mode.
2. Press **A** to simulate a fall/impact event.
3. On the hub: press **B** to acknowledge alerts (press **A** to print status).

## What it looks like (example screenshots)
**Desktop client receiving events:**

![Desktop client output](Pasted%20image%2020260122162013.png)

**Live accelerometer graphs:**

![Live monitor plot](Pasted%20image%2020260122162033.png)

## Files you’ll use most
- `wearable_device.py` — put on each wearable (set `DEVICE_ID` first)
- `central_hub.py` — put on the hub
- `desktop_client.py` — optional live monitor on your computer
- `data_capture_node.py` — optional accelerometer capture for tuning (CSV over serial)

## More docs (if you get stuck)
- `docs/SETUP.md` — flashing + prerequisites
- `docs/TEST_SCENARIOS.md` — manual test checklist
- `docs/CONFIGURATION.md` — tunable parameters
- `docs/LIMITATIONS.md` — known gaps in the prototype

## License
No license specified.
