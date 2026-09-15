# Past Incident Report: INC-0001 (Example)

**Type:** Brute force (SSH)
**Outcome:** Source IP blocked after 12 failed attempts; no successful login.
**Lesson learned:** Attempts to a single sacrificial low-privilege account are
a common precursor pattern before pivoting to more targeted accounts — flag
even "failed-only" brute force incidents at medium severity, not low.
