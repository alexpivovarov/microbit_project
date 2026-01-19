# Known Limitations and Gaps

## Functional gaps
- ACKs are not relayed; if the direct hub link is down, a node may not receive ACK confirmation even if a relayed FALL reaches the hub.

## Simulation-only data
- GPS coordinates are simulated and do not reflect real location.
- Battery level is simulated and does not read actual voltage.

## Reliability and security
- micro:bit radio is best-effort and does not guarantee delivery.
- Messages are not authenticated or encrypted.

## Hardware assumptions
- Audio alerts require an external buzzer on P0; no audio is produced without it.
