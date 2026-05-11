---
name: high-sharpe-alpha-research
description: Research findings on high Sharpe >= 1.5 alpha patterns from forum and knowledge base
type: reference
---

# High Sharpe Alpha Patterns Research (2026-05-09)

## Key Findings

### 1. Best Alpha Expressions (Sharpe 1.15-1.25)

| Expression | Sharpe | Fitness | Turnover |
|------------|--------|---------|----------|
| ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3) | 1.17 | 2.06 | 0.006 |
| ts_sum(actual_eps_value_quarterly, 252) | 1.16 | 2.05 | 0.007 |
| rank(ts_mean(close, 20)) | 1.25 | 0.68 | 0.45 |

### 2. Successful Patterns

**Fundamental Data Pattern:**
- Field: actual_eps_value_quarterly
- Operators: ts_sum(ts_sum), signed_power, ts_backfill
- Windows: 252 (annual), 8 (smooth)
- Exponent range: 0.91-1.11 (optimal ~1.05)

**Technical Data Pattern:**
- Field: close (pv1)
- Operators: rank, ts_mean
- Window: 20
- Note: Turnover higher (0.45), need rank() to reduce concentration

### 3. Key Insights

1. **Fundamental > Technical**: EPS-based alphas have lower turnover (0.006 vs 0.45), higher fitness (2.0+ vs 0.68)
2. **signed_power exponent**: Around 1.0-1.1 works well, 1.05 is optimal
3. **VECTOR fields**: Need vec_min/max operators, not standard ts_* operators
4. **Neutralization**: crowding works faster, Industry more thorough
5. **Factor diversification**: Avoid over-concentration in single category (pv, model)

### 4. Common Operators

rank (19), ts_mean (17), winsorize (12), ts_rank (11), decay_linear (10), signed_power (9), ts_delta (8), correlation (3), ts_corr (2)

### 5. Recommended Windows

5, 20, 22, 66, 120, 252, 504 (standard time horizons)

---
Research completed: 2026-05-09