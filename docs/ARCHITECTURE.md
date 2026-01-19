# Architecture

## Components
- Wearable nodes: detect falls, send alerts, show status on LEDs, optional buzzer on P0.
- Central hub: receives alerts, tracks device status, shows alerts on LEDs, prints to serial.
- Radio network: all devices share a RADIO_GROUP and communicate via micro:bit radio.

## Data flow (normal)
1. Wearable samples the accelerometer and detects an impact plus stillness pattern.
2. Wearable sends a FALL message with simulated GPS and acceleration.
3. Hub logs the alert, displays a warning, and prints to serial.
4. Hub sends an ACK back to the wearable.
5. Wearable sends periodic BATT messages (simulated).

## Mesh/relay (experimental)
- If the hub is unresponsive, wearables can attempt to relay messages through peers.
- Messages include a hop count to avoid infinite loops.
- See docs/LIMITATIONS.md for current gaps.

## High-level diagram

Wearables (N) <--- radio group ---> Central hub
     |                                    |
     |-- FALL/BATT/HBEAT -->              |-- ACK -->
     |                                    |-- Serial output --> external systems
