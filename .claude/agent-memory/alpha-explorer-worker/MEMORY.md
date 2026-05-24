# Alpha Explorer Worker Memory Index

- [mdl136_field_naming_issue](mdl136_field_naming_issue.md) - Field naming issue: mdl136_qes_etf_us_flow_gross_pctvol_1 with _1 suffix does not exist
- [session_20260501](session_20260501.md) - Worker session 2026-05-01 - API rate limiting issues
- [analyst10_exploration](analyst10_exploration.md) - analyst10 dataset exploration - fields and performance
- [eur_field_exploration_20260520](eur_field_exploration_20260520.md) - EUR region field exploration - si3_min_loan_rate Sharpe 2.46, rsk60_offer 2.36, many fields not available in EUR
- [risk60_vecmin_vecmax_exploration](risk60_vecmin_vecmax_exploration.md) - risk60 VECTOR fields exploration - BREAKTHROUGH Sharpe 2.36 with vec_max+zscore
- [vector_fields_exploration](vector_fields_exploration.md) - Multi-dataset VECTOR field exploration - analyst14/27/10/fnd6 with vec_min/vec_max patterns
- [risk60_comprehensive_results](risk60_comprehensive_results.md) - COMPREHENSIVE: 10+ submittable alphas from risk60 dataset - rsk60_offer & rsk60_last
- [rsk60_prod_correlation_20260513](rsk60_prod_correlation_20260513.md) - All rsk60 VECTOR alphas fail prod corr check (>0.9) even if structurally different
- [rsk60_cross_dataset_20260513](rsk60_cross_dataset_20260513.md) - Cross-dataset rsk60 combinations: ADDITION preserves Sharpe (~2.0), MULTIPLICATION fails, prod corr still >0.7
- [session_20260520_s3x_blocked](session_20260520_s3x_blocked.md) - Worker session 2026-05-20 - API completely blocked, all simulations stuck at 35%
- [session_20260521_api_test](session_20260521_api_test.md) - 2026-05-21 API verification - s3 dataset working with Sharpe 1.26-1.38, EUR region restored
- [session_20260520_eur_exploration](session_20260520_eur_exploration.md) - 2026-05-20 EUR exploration - only 1 PPA-compliant alpha (eur_rsk60_offer), all others fail margin check
- [eur_cross_combo_20260520](eur_cross_combo_20260520.md) - EUR cross-dataset combo tests blocked - API stuck at 0% progress
- [api_stuck_35_percent](api_stuck_35_percent.md) - API simulations stuck at 35%, get_events returns empty, correct API usage documented