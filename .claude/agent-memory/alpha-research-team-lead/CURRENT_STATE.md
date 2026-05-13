# 当前研究状态

> 最后更新: 2026-05-14

## 研究进度

- 当前阶段：S3降PC优化 — 已找到首个通过Prod Corr的Alpha
- 核心目标：Sharpe >= 1.58 + Prod Corr < 0.7 + 提交
- 已测试独立表达式: 300+

## 首个通过Prod Corr的Alpha ✅

| 指标 | 值 |
|------|-----|
| Alpha ID | e7neMpoN |
| Sharpe | 1.61 |
| Fitness | 6.89 |
| Turnover | 0.125 |
| Margin | 0.037 |
| Prod Corr | **0.682** ✅ |
| Self Corr | **0.347** ✅ |
| Sub-Universe Sharpe | 0.89 ✅ |
| 2Y Sharpe | 2.72 ✅ |

**表达式**:
```
signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 10)
```

**通过检查**：Sharpe、Fitness、Turnover、Prod Corr、Self Corr、Sub-Universe、2Y Sharpe、Pyramid(USA/D1/SHORTINTEREST x1.1)

**需修复**：Concentrated Weight = 0.99 (WARNING, limit=0.1)

## 降PC五板斧验证结果 (帖子1969)

| 板斧 | 方法 | 最优 | Prod Corr | 结论 |
|------|------|------|-----------|------|
| 1 | CROWDING中性化 | S=2.19 | 0.94 ❌ | 反而升高 |
| 2 | signed_power(10) | S=1.61 | **0.68 ✅** | **突破！** |
| 3 | 双zscore | S=2.18 | 0.80 ❌ | 不够 |
| 4 | +ts_decay_linear | S=2.26 | 0.88 ❌ | 不够 |
| 5 | decay=8 | S=2.19 | 0.79 ❌ | 不够 |

**关键发现**：`signed_power(参数=10)` 是唯一有效降低Prod Corr的方法，通过非线性变换改变信号统计指纹。

## shortinterest3 全部结果

### 第1批 (vec_max + zscore, 8个)
| Name | 字段 | 窗口 | Sharpe | Prod Corr |
|------|------|------|--------|-----------|
| S3-0001 | max_loan_rate | 5 | 1.91 | 0.85 ❌ |
| S3-0002 | max_loan_rate | 22 | 1.76 | 0.89 ❌ |
| S3-0003 | max_loan_rate | 66 | 1.61 | 0.92 ❌ |
| S3-0004 | min_loan_rate | 22 | 2.18 | — |
| S3-0005 | mean_loan_rate | 22 | 2.10 | — |

### 第2批 (算子变体)
- vec_avg 替代 vec_max: S=1.87-1.93 ✅
- 长窗口 252: S=1.59-1.72 ✅
- rank 变体: S=0.65-0.67 ❌
- minmin 模式: 方向相反，取正可用

### 第3批 (跨数据集组合)
- S3 + close_mean: S=2.26, Prod 0.88 ❌
- S3 + volume: S=1.99, Prod 0.76 ❌ (最接近)
- S3 + EPS: S<1.0 ❌

### 第4批 (降PC五板斧)
- **signed_power(10): Prod Corr 突破 0.7！**

## 下一步清单 (优先级排序)

### P0: 修复Concentrated Weight
- signed_power(..., 10) + truncation=0.05
- signed_power(..., 10) + SECTOR中性化
- signed_power(..., 10) + rank替代zscore (可能降Sharpe)

### P1: signed_power扩展
- max_loan_rate w5 + signed_power(10): S=1.25 (不够)
- 尝试 signed_power 参数 5/8/12/15
- 尝试 power (无符号) 大参数

### P2: 其他数据域
- analyst44 (整合经纪人估计): anl44_2_eps_value (cov=0.96, 仅1人用)
- analyst45 (分析师交易想法): 50 VECTOR字段
- analyst47 (复合Alpha指标): 6 MATRIX字段

### P3: Self/Prod Corr PENDING 等待
- S3-0004, S3-0005 的 Prod Corr 数据
- SECTOR/decay 变体批次的 Prod Corr

## 已验证数据源

| 数据集 | 最佳Sharpe | Prod Corr | 状态 |
|--------|-----------|-----------|------|
| shortinterest3 + signed_power(10) | 1.61 | **0.68** | ✅ 可提交(需修CW) |
| shortinterest3 Vec | 2.18 | 0.85-0.92 | ❌ Prod Corr |
| shortinterest3 + volume | 1.99 | 0.76 | ❌ Prod Corr |
| risk60 Vec | 2.37 | >0.90 | ❌ Prod Corr |
| analyst4 EPS | 1.17 | — | ❌ Sharpe |
| biasfree_analyst | 0.54 | — | ❌ 放弃 |

## 经验教训

1. **alphaCount=0 ≠ 低Prod Corr** — 平台相关性检测是跨字段的
2. **证券借贷数据域整体饱和** — 不管用什么字段，vec_max+ts_max模式Prod Corr都>0.8
3. **signed_power(大参数)是降PC神器** — 非线性变换改变统计指纹
4. **加法组合最多降PC 0.15** — 从0.9降到0.75，不够
5. **缓存去重必须考虑settings** — 否则不同中性化/decay被误判为重复
