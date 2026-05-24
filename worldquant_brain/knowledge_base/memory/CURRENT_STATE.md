# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：shortinterest3 (s3) 深度优化阶段
- 最佳成绩：**Sharpe 2.45** (`min_loan_rate w22 + truncation=0.05`)
- 数据集：shortinterest3 (VECTOR, 31字段, 29个alphaCount=0)
- 核心模式：`zscore(-ts_max(vec_max(field), window))` + 调参

## 最佳Alpha (按类别)

### 纯s3 (s3_sector_decay — 16条)
| Alpha ID | 表达式 | Sharpe | 配置 |
|----------|--------|--------|------|
| N1nk8wLe | min_loan_rate w22 | **2.45** | truncation=0.05 |
| N1nkL69E | min_loan_rate w22 | 2.23 | SECTOR中性化 |
| akNXwAW9 | min_loan_rate w22 | 2.18 | decay=2 |
| A1nqeQWW | mean_loan_rate w22 | 2.07 | SECTOR中性化 |
| N1nW00Pe | max_loan_rate w5 | 1.98 | decay=8 |

### 跨数据集 (s3x — 9条)
| Alpha ID | 表达式 | Sharpe |
|----------|--------|--------|
| MPb9zdMo | min22 + close22 | 2.26 |
| 78xg2pa2 | mean22 + close22 | 2.11 |
| 0mAn6v7r | min22 + vol22 | 1.99 |
| XgkXMXp0 | max5 + close22 | 1.89 |

### 产品相关性测试 (spc — 多条)
| Alpha ID | 表达式 | Sharpe | 备注 |
|----------|--------|--------|------|
| e7neMpoN | signed_power(zscore(min22), 10) | 1.61 | fitness=6.89, ppc=0.016, turnover=0.125, **Concentrated Weight待修复** |
| P0njKg2J | min22 + CROWDING | 2.19 | |
| 1YoVY9WW | min22 + vec_avg(min) | 1.91 | turnover 0.23过高 |

## 提交检查状态

**已有成功提交的 Alpha** ✅

| Alpha ID | Sharpe | Prod Corr | Self Corr | CW | 状态 |
|----------|--------|-----------|-----------|-----|------|
| e7neMpoN | 1.61 | **0.682** ✅ | 0.347 | 0.99 ❌ | ⚠️ 待修复CW |

> 表达式: `signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 10)`
> 通过检查: Sharpe、Fitness、Turnover、Prod Corr、Self Corr、Sub-Universe、2Y Sharpe、Pyramid

## 已确认的结论

### 有效策略
- **truncation=0.05** → 比SECTOR中性化更有效提升Sharpe
- **close/volume 加法组合** → 保留信号 (EPS/lowvol无效)
- **CROWDING中性化** → 可行，min_loan_rate达2.19
- **decay=2~8** → 小幅提升，最佳值因字段而异

### 无效策略
- `rank()`包裹 → Sharpe暴跌 (2.18→0.65)
- `ts_rank()` → Sharpe 0.58 (全灭)
- `signed_power×0.3` → 破坏信号 (2.18→0.89)
- `ts_min+vec_min` → 方向反了 (Sharpe负)
- EPS作为附加信号 → 始终<1.0
- 外层zscore → 零增益

## 下一步任务

1. **修复 e7neMpoN 的 Concentrated Weight** — signed_power(zscore(min22), 10) 权重过度集中
2. **继续 signed_power 降 PPC 方向** — sp10 的 PPC 极低 (0.016)，需降低 turnover
3. **跑 sector_decay 最佳候选的提交检查** — min22+truncation=0.05 等未验证 sub_universe

## API状态

- TOP3000 Universe正常
- VECTOR字段需 vec_min/vec_max 包裹
- 429限流存在，模拟轮询需要轮询等待

## 关键文件

- /tmp/multi_agent/spc_results.json — 最全的产品相关性测试结果
- /tmp/multi_agent/s3x_results.json — 跨数据集组合结果
- /tmp/multi_agent/s3_sector_decay_results.json — sector/decay/truncation调参
- /tmp/multi_agent/s3_submission_checks.json — 提交检查 (pending)
