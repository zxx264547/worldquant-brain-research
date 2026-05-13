---
name: rsk60 Production Correlation Issue
description: All rsk60 VECTOR-based alphas fail production correlation check (>0.9) regardless of structural differences
type: feedback
---

All rsk60 VECTOR-based alphas show production correlation > 0.9, making them non-submittable regardless of structural differences.

**Why:** The rsk60 dataset (short interest/lending data) is widely used on the platform, and VECTOR operators (vec_min/vec_max) combined with ts_ operators are a common pattern. Any alpha using rsk60 + any VECTOR operator will likely have high production correlation with existing submissions.

**How to apply:** When exploring rsk60-based alphas, don't assume structural differences in operators alone will pass production correlation. Options include:
1. Combine with MATRIX data (close, volume, vwap) for cross-dataset alphas
2. Use less common fields like rsk60_crowding (though Sharpe is low at 0.28)
3. Consider non-rsk60 datasets entirely for truly novel alphas
4. For testing purposes, structural differences DO guarantee self-correlation < 0.7

Self-correlation (vs own alphas) is NOT the same as production correlation (vs ALL platform alphas).
