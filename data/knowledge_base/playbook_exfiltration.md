# Playbook: Suspected Data Exfiltration Response

## Detection indicators
- Unusually large byte_count relative to typical traffic for the source host,
  sustained over tens of seconds to minutes, often over HTTPS (443) to an
  external destination.

## Investigation steps
1. Identify the internal source host and its normal baseline traffic volume.
2. Check destination IP/domain against threat intelligence.
3. Determine what data the source host has access to (requires asset inventory
   lookup outside this system's scope in the current version).

## Recommended response
- High/critical severity by default given potential data-loss impact.
- Simulated action: isolate simulated host, escalate incident, create ticket.
- Rollback: none applicable — isolation should be reviewed by a human before
  the host is reconnected.

## MITRE ATT&CK mapping
- T1041 (Exfiltration Over C2 Channel)
