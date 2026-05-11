---
name: mdl136_field_naming_issue
description: Field mdl136_qes_etf_us_flow_gross_pctvol_1 with _1 suffix does not exist in BRAIN
type: reference
---

# BRAIN Field Naming Issue: mdl136_qes_etf_us_flow_gross_pctvol_1

## Problem
Ideas 701-708 specified field `mdl136_qes_etf_us_flow_gross_pctvol_1` (with `_1` suffix) which does NOT exist in the BRAIN API.

## Investigation Results
1. `mdl136_qes_etf_us_flow_gross_pctvol_1` (with _1) - **DOES NOT EXIST** - returns "Unknown variable" error
2. `mdl136_qes_etf_us_flow_gross_pctvol` (without _1) - EXISTS but causes simulation timeouts (>15 min)
3. The correct dataset is `model136` (not `mdl136` as an alias)
4. Field expressions like `ts_backfill(mdl136_qes_etf_us_flow_gross_pctvol, 60)` require a `lookback` parameter

## Key Learnings
- The `_1` suffix in forum posts is likely a version indicator, not the actual field name
- When using fields from model datasets, always verify the exact field name via `get_datafields()` API
- Some fields cause extreme simulation times (>15 min) making them unusable
- Even when simulation is created, the field `mdl136_qes_etf_us_flow_gross_pctvol` (without _1) produces negative Sharpe

## Recommendation
**DISCARD all ideas 701-708** - This field direction is not viable for submission.

---

**Why:** The field name specified in ideas is wrong (has _1 suffix that doesn't exist), and the correct field either times out or produces negative returns.

**How to apply:** When testing new fields from forum posts, always verify the exact field name via API before building expressions around it.
