# General Remediation Guide

## Severity scoring (transparent, rule-based)
Severity is computed from: anomaly_score, whether authentication_failures > 0
with an eventual SUCCESS, whether the destination/source IP matches a known
threat-intel indicator, and byte_count relative to baseline. See
docs/agents.md for the exact scoring rules implemented in this system.

## General principles
- Never take an irreversible action without human approval.
- Always attach evidence (which logs, which indicators, which documents)
  to a recommendation — a recommendation without evidence should be treated
  as low-confidence regardless of stated severity.
- Prefer isolation over blocking when the affected host's ongoing legitimate
  traffic is unknown, since isolation is easier to safely reverse.
