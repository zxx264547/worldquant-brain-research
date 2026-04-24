# 模板函数速查

> 生成时间: 2026-04-23 18:05:44

## 频次排名

- **rank()**: 19次
- **ts_mean()**: 17次
- **winsorize()**: 12次
- **ts_rank()**: 11次
- **decay_linear()**: 10次
- **signed_power()**: 9次
- **ts_delta()**: 8次
- **correlation()**: 3次
- **ts_corr()**: 2次

## 函数说明

| 函数 | 语法 | 说明 |
|------|------|------|
| ts_mean | `ts_mean(x, N)` | 计算x的N日均值 |
| ts_delta | `ts_delta(x, N)` | 计算x的N日变化 |
| ts_rank | `ts_rank(x, N)` | 计算x的N日排名 |
| winsorize | `winsorize(x)` | 去除极端值 |
| rank | `rank(x)` | 横截面排名 |
| industry_relative | `industry_relative(x)` | 行业相对化 |
| decay_linear | `decay_linear(x, N)` | N日线性衰减 |
| signed_power | `signed_power(x, a)` | 符号幂变换 |