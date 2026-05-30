---
name: session_20260521_api_test
description: 2026-05-21 API verification - s3 dataset working with Sharpe 1.26-1.38
metadata:
  type: project
---

## API测试结果 (2026-05-21)

### API状态
- **状态**: 正常 (之前S3X阻塞已恢复)
- **认证**: 成功
- **EUR区域**: TOPCS1600可用

### 配置参数
- region: EUR
- universe: TOPCS1600  
- neutralization: SECTOR
- delay: 1, decay: 0

### s3数据集测试结果

| Alpha | Expression | Sharpe | Fitness | 状态 |
|-------|------------|--------|---------|------|
| s3_min_loan_basic | `-ts_max(vec_max(min_loan_rate), 22)` | 1.37 | 1.47 | ok |
| s3_min_loan_zscore | `zscore(-ts_max(vec_max(min_loan_rate), 22))` | 1.37 | 1.47 | ok |
| s3_max_loan_basic | `-ts_max(vec_max(max_loan_rate), 22)` | 1.26 | 1.33 | ok |
| s3_util_zscore | `zscore(-ts_max(vec_max(loan_utilization_ratio), 22))` | 1.38 | 1.27 | ok |

### 基准测试结果

| Alpha | Expression | Sharpe | Fitness | 状态 |
|-------|------------|--------|---------|------|
| basic_rank | `rank(close)` | 0.74 | 0.46 | ok |
| ts_mean | `ts_mean(close, 20)` | 0.43 | 0.24 | ok |

### 关键发现
1. s3数据集字段表现优异，Sharpe 1.26-1.38
2. zscore包装对s3字段无额外增益
3. 基础价格表达式表现一般（符合预期）
4. SECTOR中性化+TOPCS1600组合有效
5. 需要优化以达到1.58提交标准

### 注意事项
- USA区域仍然超时（35%卡住）
- EUR区域可以正常运行
- 某些simulation需要重试（10分钟超时）