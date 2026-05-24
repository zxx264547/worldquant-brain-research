# Alpha Research Team Lead - Memory Index

## Current Status (2026-05-21)
- **候选Alpha**: zq5l8b2V — signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 5)
- **Sharpe**: 1.75, Fitness: 7.11, PPC: 0.0176, Turnover: 0.1137
- **父Alpha**: e7neMpoN — signed_power(..., 10), Sharpe=1.61, Prod_Corr=0.682, CW=0.99
- **关键**: zq5l8b2V期望CW更低(功率5<10)，但需完整PPA验证
- **API状态**: 所有simulation卡在35%，需等待恢复
- **关键发现**: signed_power(参数=10) 是唯一有效降Prod Corr的方法
- **已测试**: 300+ 表达式

## Key Files
- [CURRENT_STATE.md](CURRENT_STATE.md) — 完整状态 (2026-05-14) ⭐
- [dataset_discovery_20260513.md](dataset_discovery_20260513.md) — 343数据集扫描
- [alpha_research_status_20260512.md](alpha_research_status_20260512.md) — 5月12日状态
- [alpha_research_status_20260501.md](alpha_research_status_20260501.md) — 5月1日天花板分析
- [user_role.md](user_role.md) — 用户角色

## Alpha Explorer Worker Memory
- [risk60_vecmin_vecmax_exploration.md](../alpha-explorer-worker/risk60_vecmin_vecmax_exploration.md) — risk60 VECTOR突破
- [risk60_comprehensive_results.md](../alpha-explorer-worker/risk60_comprehensive_results.md) — risk60综合结果
- [rsk60_prod_correlation_20260513.md](../alpha-explorer-worker/rsk60_prod_correlation_20260513.md) — rsk60 Prod Corr问题
- [rsk60_cross_dataset_20260513.md](../alpha-explorer-worker/rsk60_cross_dataset_20260513.md) — 跨数据集组合结果
- [vector_fields_exploration.md](../alpha-explorer-worker/vector_fields_exploration.md) — 多数据集VECTOR探索

## Learnings
1. alphaCount=0 ≠ 低Prod Corr — 平台相关性跨字段检测
2. 证券借贷数据域整体饱和 — vec_max+ts_max模式 Prod Corr恒>0.8
3. signed_power(大参数) 改变统计指纹, 是降PC唯一有效方法
4. 加法跨域组合最多降PC 0.15 (不够)
5. 缓存去重必须考虑settings
