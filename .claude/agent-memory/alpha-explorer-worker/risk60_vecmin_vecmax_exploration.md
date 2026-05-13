---
name: risk60_vecmin_vecmax_exploration
description: Results of exploring risk60 VECTOR fields with vec_min/vec_max patterns - major breakthrough with Sharpe 2.36
type: reference
---

# risk60 Dataset Vec_min/Vec_max Exploration Results

## Dataset Overview
- **Name:** risk60 - Securities Lending Insight Data (VECTOR type)
- **Total VECTOR fields:** 5 (but only 4 usable via expression):
  - `rsk60_offer` - Composite borrow fee (annualized) paid by the short seller
  - `rsk60_last` - Most recent borrow/lend rate observed at the snapshot time
  - `rsk60_crowding` - Signed daily indicator of shorting activity (positive = increased shorting/crowding)
  - `rsk60_datatime` - Vendor timestamp (not useful for alpha)
  - `lending_fee_bid_rate` - Does not work as variable name in expressions

## BREAKTHROUGH RESULT
**Best expression:** `zscore(-ts_max(vec_max(rsk60_offer), 22))`
- **Sharpe: 2.360** (well above 1.58 target)
- **Fitness: 5.170** (well above 0.5 target)
- **PPC: 0.070** (well below 0.5 target)
- **Turnover: 0.0286** (very low)
- **Margin: 0.0420** (Margin > Turnover: YES)
- **Status: SUBMITTABLE**
- **alpha_id: RRNLNY6z**

## Key Findings

### 1. Securities Lending Fee Fields Have Strong Signals
Both `rsk60_offer` and `rsk60_last` produce strong Sharpe with negated vecmax patterns:
- rsk60_offer consistently outperforms rsk60_last
- The natural direction is NEGATIVE: `-ts_max(vec_max(field))` gives positive Sharpe
- Economic logic: When borrow fees are high (expensive to short), going long generates alpha

### 2. Best Window Analysis (rsk60_offer with -ts_max(vec_max))
| Window | Sharpe | Fitness |
|--------|--------|---------|
| 5      | 1.110  | 2.510   |
| 22     | 1.130  | 2.600   |
| 66     | 1.010  | 2.190   |
| 120    | 0.850  | 1.690   |
| 252    | 0.610  | 1.020   |

Best window: 22

### 3. Zscore Wrapper Transforms Performance
Base expression `-ts_max(vec_max(rsk60_offer), 22)`: Sharpe=1.130
With zscore: Sharpe=2.360 (2x improvement!)
Rank wrapper was NOT helpful (dropped to 0.680)

### 4. Same-Direction Matching Validation
- `-ts_max(vec_max(rsk60_offer), 22)`: Sharpe=1.130 (max+max direction)
- `-ts_min(vec_min(rsk60_offer), 22)`: Sharpe=0.830 (min+min, weaker)

The vec_max+max direction clearly outperforms vec_min+min for this field.

### 5. Vec_avg Baseline Comparison
- `-ts_max(vec_avg(rsk60_offer), 22)`: Sharpe=1.150 - comparable to vec_max!
- vec_max (1.130) and vec_avg (1.150) are very close for this field

### 6. Other Fields
- **rsk60_last**: zscore gives expected similar performance (~1.04-1.05)
- **rsk60_crowding**: Weaker signal (Sharpe 0.49 max direction, -0.49 negated)
- **lending_fee_bid_rate**: Doesn't work as expression variable

## Recommendations
- Submit `zscore(-ts_max(vec_max(rsk60_offer), 22))` - exceeds all PPA thresholds
- Create variants with different windows for more submission candidates
- Explore zscore on rsk60_last as secondary candidate
- The combination of two rsk60 fields needs careful sign handling
