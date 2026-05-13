---
name: vector_fields_exploration
description: Results of exploring VECTOR fields across multiple datasets (analyst14, analyst27, analyst10, fundamental6) with vec_min/vec_max patterns - comprehensive results
type: reference
---

# VECTOR Field Exploration Results (Comprehensive)

## Dataset VECTOR Field Discovery
Used the BRAIN API `/data-fields` endpoint with `type=VECTOR` to discover fields.

### analyst14 - "Estimations of Key Fundamentals" (11 VECTOR fields)
- `anl14_estvalue_fp1` through `fp5` (Estimation values for various periods, coverage=0.5)
- `anl14_recvalue` (Recommendation value, coverage=0.5)
- Broker fields (not useful for alpha)

### analyst27 - Analyst Quality Metrics (100 VECTOR fields)
- `anl27_analyst_accuracy1/2` - Analyst accuracy scores (coverage ~0.85)
- `anl27_analyst_relative_accuracy1-4` - Peer-relative accuracy ranks
- `anl27_profitabilityprev_analyst_profitability1/2` - Analyst profitability (coverage ~0.89)
- `anl27_analyst_consistency` - Analyst consistency scores
- `anl27_analyst_relative_ratio1/2` - Revision ratio ranks
- Many estimator-level aggregations

### analyst10 - "Performance-Weighted Analyst Estimates" (119 VECTOR fields)
- `anl10_det_full_eps_past_det_estvalue` - Per-analyst EPS estimate value (coverage varies)
- `anl10_det_full_ebi_past_det_estvalue` - EBI estimates
- `anl10_det_full_fcf_past_det_estvalue` - FCF estimates
- Many more detailed estimate fields

### fundamental6 - "Fundamental Data" (100+ VECTOR fields)
- `fnd6_sales`, `fnd6_ibs`, `fnd6_xsgas` etc. (all coverage=0.5)
- These are fundamental data series, not per-analyst vectors

## Performance Results

### Pattern: `zscore(-ts_max(vec_max(field), 22))` (risk60's best pattern)

| Field | Dataset | Sharpe | Fitness | Turnover | Status |
|-------|---------|--------|---------|----------|--------|
| `rsk60_offer` | risk60 | 2.360 | 5.170 | 0.029 | SUBMITTABLE |
| `anl14_estvalue_fp2` | analyst14 | 0.580 | 0.510 | 0.042 | Promising |
| `anl14_estvalue_fp1` | analyst14 | 0.570 | 0.500 | 0.042 | Promising |
| `anl14_estvalue_fp4` | analyst14 | 0.510 | 0.420 | 0.043 | Promising |
| `anl10_det_full_eps_past_det_estvalue` | analyst10 | 0.500 | 0.570 | 0.006 | Promising |
| `anl14_recvalue` | analyst14 | -0.220 | -0.070 | 0.010 | Discarded |
| `anl27_profitabilityprev_analyst_profitability1` | analyst27 | -0.100 | -0.040 | 0.036 | Discarded |
| `anl27_analyst_relative_accuracy1` | analyst27 | -0.110 | -0.030 | 0.016 | Discarded |
| `fnd6_sales` | fundamental6 | -0.000 | -0.000 | 0.004 | Discarded |

### Optimization Results

#### Wrapper comparison on analyst14_estvalue_fp2:
| Wrapper | Sharpe | Fitness | Turnover |
|---------|--------|---------|----------|
| `zscore(-ts_max(vec_max(field), 22))` | 0.58 | 0.51 | 0.042 |
| `rank(-ts_max(vec_max(field), 22))` | **0.68** | **1.02** | 0.039 |

#### Neutralization effect on analyst14_estvalue_fp2:
| Neutralization | Sharpe | Fitness |
|---------------|--------|---------|
| NONE | 0.58 | 0.51 |
| INDUSTRY | 0.10 | 0.03 |

### Key Findings

1. **maxmax_neg pattern works across multiple datasets**: analyst14 and analyst10 show clean directional signals with the same `-ts_max(vec_max())` pattern as risk60, but with weaker magnitude (~0.5-0.7 vs 2.36).

2. **Best horizon for analyst14**: fp2 (2 quarters, Sharpe=0.58) > fp1 (1 quarter, 0.57) > fp4 (4 quarters, 0.51). Shorter horizons slightly stronger.

3. **Rank wrapper improves Sharpe**: For analyst14 fp2, `rank()` boosts Sharpe from 0.58 to 0.68. This contradicts the risk60 experience where `zscore` gave 2x improvement. Different datasets respond differently to wrappers.

4. **INDUSTRY neutralization KILLS the signal**: Sharpe drops from 0.58 to 0.10. The analyst14 signal is partly industry-driven (likely industry-wide estimation patterns).

5. **minmin pattern doesn't work for analyst fields**: Unlike risk60 where minmin gave Sharpe 0.83 (weaker but positive), analyst14 minmin gave near-zero Sharpe. This suggests analyst estimate vectors don't have the same asymmetric structure as securities lending data.

6. **Perfect sign mirror**: The maxmax_neg and maxmax_pos patterns give perfect opposite sign results (e.g., +0.51 vs -0.51), confirming clean directional signals.

7. **analyst27 doesn't respond**: Analyst quality metrics (accuracy, profitability, consistency) give near-zero or slightly negative Sharpe with vec_max patterns.

8. **fundamental6 doesn't respond**: Sales and other fundamental vectors are neutral.

9. **analyst10 EPS estimates**: Sharpe=0.50 with zscore, very low turnover (0.006). Clean signal but needs optimization to reach 1.58.

## Recommendations
- **Rank-based optimization**: `rank(-ts_max(vec_max(anl14_estvalue_fp2), 22))` at Sharpe 0.68 is the best non-risk60 result, but still far from 1.58.
- **Further exploration needed**: Try combining analyst14 estimation values with R$K60 fields (multiply/add) for boosting Sharpe.
- **Try decay parameters**: analyst14 has moderate turnover (0.04); decay=2-3 might improve fitness.
- **Test analyst10 with rank wrapper**: `rank(-ts_max(vec_max(anl10_eps_estvalue), 22))` might improve from 0.50 towards 0.60+.
- **Cross-dataset combinations**: Multiply analyst14 estvalue signals with close/volume-based signals might produce higher Sharpe.
