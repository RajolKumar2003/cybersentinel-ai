# Playbook: Port Scan Response

## Detection indicators
- High connection_rate from a single source IP to many destination ports in a short window.
- Mostly REFUSED/TIMEOUT status, tiny packet sizes, sub-second durations.

## Investigation steps
1. Confirm the source IP against threat intelligence (known scanner / Tor exit node?).
2. Check whether any scanned port returned SUCCESS — that indicates a follow-up
   connection attempt worth investigating separately.
3. Correlate with firewall/IDS logs for the same time window.

## Recommended response
- Low/medium severity if fully blocked by firewall and no successful connections.
- Escalate to high if any destination port responded successfully, especially on
  privileged/management ports (22, 3389, 445).
- Simulated action: block source IP at perimeter firewall; create incident ticket.

## MITRE ATT&CK mapping
- T1595 (Active Scanning)
