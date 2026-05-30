# EUR Cross-Dataset Combinations Test (2026-05-20)

## Status: API_BLOCKED

### API Issue
- Simulations created (201) but stuck at 0% computation progress
- Not a rate limit issue (simulations accepted but not processing)
- Likely systemic queue/compute issue

### Configuration Confirmed Working
```json
{
  "region": "EUR",
  "universe": "TOPCS1600",
  "neutralization": "SECTOR",
  "instrumentType": "EQUITY"
}
```

### Known EUR Fields (from previous sessions)
| Field | Sharpe | Expression |
|-------|--------|------------|
| si3_min_loan_rate | 2.46 | zscore(-ts_max(vec_max(si3_min_loan_rate), 22)) |
| rsk60_offer | 2.36 | zscore(-ts_max(vec_max(rsk60_offer), 22)) |

### Planned Cross-Dataset Tests
1. **eur_baseline_si3**: zscore(-ts_max(vec_max(si3_min_loan_rate), 22)) - Expected Sharpe 2.46
2. **eur_baseline_rsk60**: zscore(-ts_max(vec_max(rsk60_offer), 22)) - Expected Sharpe 2.36
3. **eur_add_combo**: zscore(-ts_max(vec_max(si3_min_loan_rate), 22)) + zscore(-ts_max(vec_max(rsk60_offer), 22))
4. **eur_add_long**: zscore(-ts_max(vec_max(si3_min_loan_rate), 66)) + zscore(-ts_max(vec_max(rsk60_offer), 66))

### Hypothesis
- Both fields are from different datasets (shortinterest3 vs risk60)
- Both use vec_max for VECTOR processing
- If signals are uncorrelated, addition may improve or maintain Sharpe
- Long window (66) may smooth out noise

### Next Steps
1. Wait for API to recover
2. Run planned cross-dataset tests
3. Test production correlation to avoid duplicate submissions
