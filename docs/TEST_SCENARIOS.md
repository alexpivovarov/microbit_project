# Test Scenarios (Draft)

These are manual tests for the prototype. None have been formally validated yet.

## Scenario 1: Basic bring-up
Purpose: Confirm devices boot and join the radio group.
Setup: 1 hub, 1 wearable.
Steps:
1. Flash central_hub.py to the hub and wearable_device.py to the wearable.
2. Power both devices.
Expected:
- Wearable shows its DEVICE_ID on boot.
- Hub shows a device count or a dash if no devices are seen.

## Scenario 2: Test mode fall simulation
Purpose: Validate end-to-end alert flow without real movement.
Setup: 1 hub, 1 wearable.
Steps:
1. Boot the wearable while holding button A to enter test mode.
2. Press button A to simulate a fall.
Expected:
- Wearable shows a fall indication and triggers the buzzer if connected.
- Hub prints a FALL ALERT block to serial and flashes the display.
- Hub sends ACK.

## Scenario 3: False-positive avoidance
Purpose: Ensure normal movement does not trigger an alert.
Setup: 1 hub, 1 wearable.
Steps:
1. Wear the device or move it around gently for 1-2 minutes.
Expected:
- No FALL alerts on the hub.

## Scenario 4: Battery reporting (simulated)
Purpose: Verify periodic battery updates.
Setup: 1 hub, 1 wearable.
Steps:
1. Leave both devices running for 1-2 minutes.
Expected:
- Hub prints battery updates at the configured interval.

## Scenario 5: Alert acknowledgment
Purpose: Verify operator acknowledgement.
Setup: 1 hub, 1 wearable.
Steps:
1. Trigger a fall alert (Scenario 2).
2. Press button A on the hub.
Expected:
- Hub prints an acknowledgment message.
- Hub display returns to normal status.

## Scenario 6: Serial output parsing
Purpose: Confirm external systems can detect alerts.
Setup: Hub connected to a computer.
Steps:
1. Trigger a fall alert.
2. Capture serial output.
Expected:
- Output contains the text "FALL ALERT" and device details.

## Scenario 7: Hub offline detection (blocked)
Purpose: Ensure wearables detect hub unresponsiveness.
Setup: 1 hub, 1 wearable.
Steps:
1. Power on both devices.
2. Power off the hub and wait for the timeout.
Expected:
- Wearable should indicate hub connection lost.
Status: blocked (heartbeat sender is not implemented).

## Scenario 8: Relay path (blocked)
Purpose: Validate mesh relay when hub is out of range.
Setup: 1 hub, 2 wearables in a line topology.
Steps:
1. Place wearable A out of hub range but in range of wearable B.
2. Trigger a fall alert on wearable A.
Expected:
- Hub receives the alert via wearable B.
Status: blocked (relay message format needs updates).
