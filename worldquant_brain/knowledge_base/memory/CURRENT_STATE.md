# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展

## 研究进度

- 当前阶段：Alpha参数优化阶段
- 核心目标：寻找Sharpe≥1.58的Alpha
- 最佳成绩：Sharpe 1.02 (analyst4 + eps + t=0.25, d=1)

## 已测试组合（10个）

| Alpha表达式 | Sharpe | Fitness | 状态 |
|------------|--------|---------|------|
| ts_mean(winsorize(eps), 25) | 1.02 | 1.43 | 基准最佳 |
| ts_mean(winsorize(eps), 15) | 1.01 | 1.40 | ≈ |
| ts_mean(winsorize(eps), 20) | 1.01 | 1.41 | ≈ |
| ts_mean(winsorize(eps), 10) | 1.01 | 1.40 | ≈ |
| rank(ts_mean(winsorize(eps), 25)) | 0.71 | 1.02 | ↓ |
| pv87_affops | 0.64 | 0.92 | ↓ |
| anl4_net_income | 0.59 | 0.81 | ↓ |
| pv87_bps | -0.40 | -0.36 | ↓↓ |

## 核心问题

Sharpe 1.02 < 1.58，差距56%。需要更大突破。

## API状态

- 2026-04-24 13:00+ - SSL错误，API不可用
- API监控进程运行中 (PID: 21827)
- 监控频率: 每5秒检查一次

## 论坛经验（重要发现）

### OB53521工作流要点（2026年1月）
1. **增量复杂度法则**: 0-op(rank/zscore) -> 1-op(ts类) -> 2-op+嵌套
2. **时间窗口约束**: 仅用5,22,66,120,252,504（禁止10,14,30等）
3. **归一化铁律**: Fundamental/Volume必须用rank()包裹
4. **批量法则**: 每次必须8个Alpha
5. **Fitness<1.0黄金组合**: Decay=2, Neut=Industry, Trunc=0.01

### 其他技巧
1. **signed_power(x, 1.3)** - 可提升Robustness约0.02
2. **scale** - 可提升约0.02
3. **crowding中性化** - 快速且效果好
4. **group_rank/signed_power** - 当Sharpe>0.6时可提升

## 待测试方向（API恢复后，按优先级）

### 高优先级（基于论坛经验）

1. **signed_power(x, 1.3)** - `signed_power(ts_mean(winsorize(eps), 25), 1.3)`
2. **crowding中性化** - neutralization='crowding'
3. **group_rank组合** - group_rank(ts_mean(eps, 25), sector)

### 中优先级

4. **ts_sum替代ts_mean** - ts_sum(winsorize(eps), 25)
5. **truncation=0.35**
6. **多窗口组合** - 0.5*ts_mean(eps,10) + 0.5*ts_mean(eps,25)

### 低优先级

7. **analyst49数据集**
8. **mdl136高频数据**
9. **region=EUROPE/INDIA**

## 测试脚本

已创建: `scripts/alpha_mining/new_direction_mining.py`
- 包含21个测试配置
- 基于论坛经验优化
- 支持缓存避免重复测试

---
*更新时间：2026年4月24日 16:40*
*API状态: SSL错误持续中，监控运行中*