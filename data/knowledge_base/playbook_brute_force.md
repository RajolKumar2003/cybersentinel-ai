# Playbook: Authentication Brute Force Response

## Detection indicators
- Repeated authentication_failures from one source IP against one service
  (commonly ssh/22 or rdp/3389) in a short time window.

## Investigation steps
1. Check whether any attempt eventually succeeded (status=SUCCESS) after many
   failures — this is the highest-priority signal, indicating possible compromise.
2. Check threat intelligence for the source IP.
3. Review account lockout policy status for the targeted account(s).

## Recommended response
- Medium severity if all attempts failed and account lockout engaged.
- Critical severity if any attempt succeeded.
- Simulated action: isolate simulated host if internal account was likely
  compromised; block source IP; force password reset (out of scope for
  automated simulated actions — requires human execution).

## MITRE ATT&CK mapping
- T1110 (Brute Force)
