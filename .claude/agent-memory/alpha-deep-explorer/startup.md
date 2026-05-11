---
name: deep_explorer_startup
description: Alpha deep-explorer agent initialized for Sharpe boost optimization
type: project
---

Alpha Deep-Explorer agent started on 2026-04-25.

**Current Status:**
- API: Normal
- Best Alpha: `ts_mean(winsorize(actual_eps_value_quarterly), 10)` with Sharpe=1.01, Fitness=1.40
- Target: Sharpe >= 1.58

**Optimization Plan:**
1. Generate 8 variants with signed_power, decay, neutralization, truncation variations
2. Focus on: signed_power(1.3), decay=2-5, industry/crowding neutralization, truncation=0.01
3. Track progress in /tmp/multi_agent/results.json