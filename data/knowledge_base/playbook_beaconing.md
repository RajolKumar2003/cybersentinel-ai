# Playbook: C2 Beaconing Response

## Detection indicators
- Small, regular, low-variance connections at a fixed interval to the same
  external destination — a strong indicator of command-and-control beaconing
  rather than normal user-driven traffic.

## Investigation steps
1. Measure the regularity of the interval (low variance = more suspicious).
2. Check the destination IP/domain against threat intelligence indicators.
3. Review what process/service on the source host is responsible if endpoint
   telemetry is available (out of scope for this system's current version).

## Recommended response
- High severity — beaconing usually indicates an already-compromised host.
- Simulated action: isolate simulated host, block destination IP, escalate.

## MITRE ATT&CK mapping
- T1071 (Application Layer Protocol) / T1105/T1102-style C2 patterns
