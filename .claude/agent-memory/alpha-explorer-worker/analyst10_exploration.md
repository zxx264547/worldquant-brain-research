---
name: analyst10_dataset_exploration
description: Results of exploring analyst10 (Performance-Weighted Analyst Estimates) dataset
type: reference
---

# analyst10 Dataset Exploration Results

## Dataset Overview
- **Name:** Performance-Weighted Analyst Estimates
- **Total MATRIX fields:** 1943
- **Working field pattern:** `anl10_{metric}{stat}_{period}` 
  (e.g., `anl10_epsrevise_ratio_to_close_fy2`)
- **Dataset fields use SMART estimates** — analyst estimates weighted by past performance

## Working vs Non-Working Field Names

### Working fields (verified in expressions):
- `anl10_epsrevise_ratio_to_close_fy2` — Best performer
- `anl10_epsrevise_ratio_to_close_fy1`
- `anl10_epsrevise_ratio_to_close_fq1`
- `anl10_epsrevise_ratio_to_close_fq2`
- `anl10_epsrevise_ratio_to_consensus_fy2`
- `anl10_epsrevise_ratio_to_consensus_fy1`
- `anl10_epsrevise_ratio_to_consensus_fq2`
- `anl10_epsrevise_ratio_to_consensus_fq1`
- `anl10_epsnormal_increase_fy2/fy1/fq2/fq1`
- `anl10_epsnormal_decrease_fy2/fy1/fq2/fq1`
- `anl10_epsinnovation_score_fy2/fy1/fq2/fq1`

### Non-working (API returns them but expression engine doesn't recognize):
- `year1_eps_consensus_estimate` — Unknown variable
- `year2_eps_consensus_estimate` — Unknown variable
- `year1_eps_estimate_analyst_count` — Unknown variable
- `year2_eps_estimate_analyst_count` — Unknown variable
- `anl10_analyst_innovation_*` — Unknown variable
- `quarter1_eps_consensus_estimate` — Unknown variable
- `quarter2_eps_consensus_estimate` — Unknown variable

## Performance Results (Universe=TOP3000, Delay=1, Neut=NONE, Decay=0, Trunc=0.01)

### 0-op: rank(field)
| Expression | Sharpe | Fitness | Turnover |
|---|---|---|---|
| `rank(anl10_epsrevise_ratio_to_close_fy2)` | 0.74 | 0.32 | 1.51 |
| `rank(anl10_epsrevise_ratio_to_consensus_fy2)` | 0.72 | 0.31 | 1.52 |
| `rank(anl10_epsrevise_ratio_to_close_fy1)` | 0.69 | 0.29 | 1.49 |
| `rank(anl10_epsrevise_ratio_to_consensus_fq2)` | 0.63 | 0.26 | 1.57 |

### 1-op: rank(ts_mean(field, W)) on best field
| Expression | Sharpe | Fitness | Turnover |
|---|---|---|---|
| `rank(ts_mean(anl10_epsrevise_ratio_to_close_fy2, 5))` | 0.73 | 0.68 | 0.33 |
| `rank(ts_mean(anl10_epsrevise_ratio_to_close_fy2, 22))` | 0.69 | 1.01 | 0.08 |

## Key Observations
1. EPS revision ratios (to close or to consensus) produce positive Sharpe (0.56-0.74)
2. FY1/FY2 signals stronger than FQ1/FQ2 signals
3. High turnover (~1.5) on 0-op — ts_mean(w=22) reduces turnover to 0.08
4. Fitness improves with smoothing (0.32 -> 1.01) but Sharpe doesn't increase beyond 0.74
5. analyst10 revision ratios are analog to analyst4 actual_eps signals but performance-weighted

## Comparison to analyst4
- analyst4 actual_eps_value signals: In 0-op typically S=0.3-0.8, analyst10 revision ratios: S=0.56-0.74 — comparable range
- analyst10 has more fields but slower simulations (2-4 min vs 1-2 min for analyst4)
- analyst10's unique value is the performance-weighting of analyst estimates

## Recommendations
- analyst10 fields are viable for alpha construction but need deeper optimization to reach S>1.58
- Try: decay>0 to reduce turnover, neutralization by INDUSTRY, different truncation values
- Focus on `anl10_epsrevise_ratio_to_close_fy2` as primary candidate
- EPS normal increase/decrease count fields (breadth signals) are worth further testing

## Known Issues
- SSL errors with `requests` library on this WSL setup — must unset proxy env vars
- Simulation API rate limit: 5 calls/minute, need 65s wait after every 5th call
- Small jitter (1-2s) between calls to avoid 429s
