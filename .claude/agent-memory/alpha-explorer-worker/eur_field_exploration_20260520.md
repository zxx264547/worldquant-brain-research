# EUR Region Field Exploration (2026-05-20)

## Key Findings

### EUR Region Configuration
- Default universe is TOP3000 (not TOP1000 or TOPCS1600)
- EUR region mapping is implicit in CLI commands
- Explicit region settings cause field availability issues

### Working Fields in EUR (Sharpe >= 1.0)
| Field | Sharpe | Expression |
|-------|--------|------------|
| si3_min_loan_rate | 2.46 | zscore(-ts_max(vec_max(min_loan_rate), 22)) |
| rsk60_offer | 2.36 | zscore(-ts_max(vec_max(rsk60_offer), 22)) |
| close | 0.67 | rank(close) |

### Not Available in EUR
- si3_loan_utilization_ratio
- rsk60_bid, rsk60_mid
- vol, market_cap
- br1_recommendation
- anl10_pe_ratio

### Key Insight
Many vector fields from USA region (like analyst10, brokerrecommendation1, various risk60 fields) are NOT available in EUR. The successful EUR alphas are from shortinterest3 and risk60_offer.

### Additional Field Tests (2026-05-20 continued)
| Field | Status | Notes |
|-------|--------|-------|
| mean_loan_rate | API_BLOCKED | Stuck at 35% |
| max_loan_rate | API_BLOCKED | Rate limit |
| rsk60_crowding | NOT_AVAILABLE | Unknown variable |
| rsk60_beta | NOT_AVAILABLE | Unknown variable |
| rsk60_volatility | NOT_AVAILABLE | Unknown variable |
| utilization_rate | NOT_AVAILABLE | Unknown variable |

### Key Insight
EUR region has very limited field availability. Only two strong fields confirmed:
1. min_loan_rate (Sharpe 2.46)
2. rsk60_offer (Sharpe 2.36)

Other risk60 fields (crowding, beta, volatility) are NOT available in EUR region.

### Next Steps
1. Test cross-dataset combinations: min_loan_rate + rsk60_offer
2. Wait for API to recover, then test mean_loan_rate/max_loan_rate
3. Try other EUR-specific datasets (market_overview, industry)