---
name: industry_valid_finding
description: INDUSTRY neutralization may actually be valid - simulations created but timed out
type: project
---

# Industry Neutralization Discovery

## 2026-04-26 01:03

### Key Observation
When testing INDUSTRY (uppercase), the simulation was CREATED successfully:
- 2026-04-26 00:57:29 - Simulation created: https://api.worldquantbrain.com/simulations/1p0EnR
- 2026-04-26 00:58:35 - Timeout after 60s (too short)
- Retried with 00:58:44 - Created simulation 4tK0WW
- 00:59:49 - Timeout again
- 01:00:17 - Created simulation RiCOJ3
- 01:01:23 - Timeout after 60s

NO "not a valid choice" error for INDUSTRY!

### Contrast with lower-case
Earlier tests with "industry" (lowercase) got immediate "not a valid choice" error.

### Hypothesis
The API is case-sensitive. INDUSTRY (uppercase) might be valid, while industry (lowercase) is not.

### Next Action
Test INDUSTRY with longer timeout (600s) to confirm it works.