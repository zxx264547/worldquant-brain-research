# Best Practices

本目录存放 WorldQuant BRAIN 量化研究的最佳实践文档。

## 核心原则

### PPA因子标准

| 指标 | 要求 | 备注 |
|------|------|------|
| PPC | < 0.5 | 核心门槛，必须满足 |
| Sharpe | >= 1.58 | 建议 >= 1.05 更安全 |
| Fitness | > 0.5 | 必须满足 |
| Margin | > Turnover | 必须满足 |

### OS策略

| OS状态 | 建议策略 |
|--------|----------|
| OS < 0.5 | 交其他区域Alpha，不交Theme |
| OS >= 0.5 | 交Theme，加成翻倍 |

### 数据集选择

- **analyst4** 是目前最佳数据集，首次同时突破 Sharpe>1 和 M/T>1
- 最佳窗口区间：23-26（奇数窗口更稳定）
- 有效模板：ts_mean(winsorize({data}), N)

### 表达式规范

- 使用 winsorize() 预处理数据
- 使用 ts_mean() 进行平滑
- 避免使用 rank() 会导致 M/T 变为 0
- 避免使用 ts_zscore() 失败率高

## 工作流规范

1. 挖掘阶段：batch_mining.py
2. 筛选阶段：screening_pipeline.py
3. 去重阶段：correlation_analysis.py
4. 验证阶段：check_submittable.py

---

*最后更新：2026年4月*
