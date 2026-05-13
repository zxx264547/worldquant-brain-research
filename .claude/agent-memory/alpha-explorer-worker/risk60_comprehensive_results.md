---
name: risk60_comprehensive_results
description: Comprehensive risk60 exploration results - 10+ submittable alphas found
type: reference
---

# risk60 Dataset Comprehensive Results (2026-05-13)

## Dataset
**risk60** - Securities Lending Insight Data (VECTOR type)
Fields usable: `rsk60_offer` (borrow fee), `rsk60_last` (recent rate), `rsk60_crowding`

## Universal Pattern

The winning formula for ALL risk60 VECTOR fields:

```
zscore(-ts_max(vec_max(<field>), <window>))  # OR
zscore(-ts_max(vec_avg(<field>), <window>))  # vec_avg equally effective
```

**Key rules:**
- ALWAYS negate: `-ts_max()` (high borrow fee = positive return signal)
- ALWAYS use zscore (rank is far weaker: 0.68 vs 2.34-2.37)
- vec_max and vec_avg are equally effective (2.37 both)
- ts_min(vec_min) works when negated but is weaker (2.15 vs 2.37)
- Cross-field combinations with close/volume DESTROY the signal (near zero Sharpe)
- rank wrapper significantly reduces Sharpe

## All Submittable Candidates (Sharpe >= 1.58)

### rsk60_offer with ts_max(vec_max)
| Window | Sharpe | Fitness | Status |
|--------|--------|---------|--------|
| 5 | 2.34 | 5.08 | READY |
| 22 | 2.02 | 3.37 | READY (SECTOR neut) |
| 66 | 2.26 | 4.74 | READY |
| 120 | 2.08 | 4.11 | READY |
| 252 | 1.79 | 3.17 | READY |
| 504 | 1.55 | 2.46 | Near-threshold |

### rsk60_last with ts_max(vec_max)
| Window | Sharpe | Fitness | Status |
|--------|--------|---------|--------|
| 5 | 2.34 | 5.05 | READY |
| 22 | 2.37 | 5.11 | READY |
| 66 | 2.36 | 4.81 | READY |
| 120 | 2.17 | 4.11 | READY |
| 252 | 1.82 | 3.05 | READY |
| 504 | 1.47 | 2.16 | Near-threshold |

### vec_avg variant
- `zscore(-ts_max(vec_avg(rsk60_offer), 22))`: Sharpe=2.37, Fitness=5.21 - DIFFERENT CORRELATION

### ts_min(vec_min) variant
- `zscore(-ts_min(vec_min(rsk60_offer), 22))`: Sharpe=2.15, Fitness=4.33

## What Does NOT Work
- Cross-field multiplication (risk60 * close/volume) - kills signal
- rank wrapper (0.68 vs 2.37)
- Same-field multiplication (rsk60_offer * rsk60_last) - negative Sharpe
- ts_min(vec_min) without negation - negative Sharpe

## Key Insight
The risk60 dataset provides EXTREMELY strong standalone signals. These are likely due to the economic relationship: high securities lending fees indicate expensive shorting conditions, which predicts positive returns as stocks recover from high borrowing costs. The signal is strongest at short windows (5-66 days) and decays slowly.
