---
name: mdl136_invalid
description: mdl136 field is only available in EUR/ETF region, not USA
type: reference
---

# mdl136 Field Discovery

## Key Finding (2026-04-30)
The field `mdl136_qes_etf_us_flow_gross_pctvol_1` is only available in **EUR region with ETF instruments**, NOT in USA region with EQUITY instruments.

## Error Messages
1. For EUR region: `Universe TOP3000 is not available for instrument type EQUITY and region EUR.`
2. For USA region: `Simulation error: Attempted to use unknown variable "mdl136_qes_etf_us_flow_gross_pctvol_1"`

## Implications
1. mdl136 cannot be used in USA/EQUITY/TOP3000 combinations
2. The high Sharpe (1.62-1.77) reported from mdl136 was from EUR/ETF region
3. Need to find new approaches valid for USA/EQUITY

## Valid Fields in USA/EQUITY
- actual_eps_value_quarterly (analyst4) - best at Sharpe ~1.04
- actual_dividend_value_quarterly
- actual_cashflow_per_share_value
- volume, returns, adv21
- anl69_best_eps_stddev (vector field)
- anl10_bpsff_5551 (vector field)
- pv87 fields

## Gap to Target
Sharpe ~1.04 -> 1.58 (52% gap)