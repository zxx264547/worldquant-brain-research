# WorldQuant Alpha挖掘项目总结

## 一、项目概述

**目标**: 挖掘满足PPA标准的Alpha
- Sharpe >= 1.58
- Fitness > 0.5
- PPC < 0.5
- Margin > Turnover
- Turnover > 0.01

## 二、核心发现

### 2.1 数据集特性对比

| 数据集 | Sharpe | M/T比 | 特点 |
|--------|--------|-------|------|
| mdl136 | 1.58-1.77 | ~0.02 | 高Sharpe但M/T极低 |
| pv87 | 0.64-0.66 | 3-35 | M/T高但Sharpe低 |
| analyst4 | **1.00** | **2.90+** | 首次同时突破Sharpe>1和M/T>1 |

### 2.2 最佳Alpha发现

**analyst4数据集 - actual_eps_value_quarterly字段**

| 窗口 | Sharpe | Fitness | M/T |
|------|--------|---------|-----|
| 23 | 1.00 | 1.42 | 2.90 |
| 25 | 1.00 | 1.43 | 2.96 |
| 26 | 1.00 | 1.43 | 2.98 |

**表达式**: `ts_mean(winsorize(actual_eps_value_quarterly), 23-26)`

### 2.3 模板有效性

| 模板 | 效果 |
|------|------|
| `ts_mean(winsorize({data}), 20-30)` | 最佳区间 |
| `winsorize({data})` | 可用但一般 |
| `ts_mean({data}, N)` 无预处理 | 失败率高 |
| `ts_zscore({data}, 20)` | 失败 |
| `rank({data})` | M/T变为0 |
| `ts_backfill()` | 不稳定 |

## 三、关键问题

### Sharpe与M/T的矛盾
- 高Sharpe策略依赖频繁信号变化 → 高换手 → 低Margin
- 低换手策略信号稳定 → 低Sharpe
- **analyst4首次突破这个矛盾**

### 回溯期敏感性
- 偶数窗口(24,26,28,30)容易失败
- 奇数窗口(23,25,27,29)更容易成功
- 最优区间: 23-26

## 四、项目目录整理

### 清理后的结构
```
worldquant_brain/
├── scripts/
│   ├── core/                    # 核心模块
│   ├── alpha_mining/           # 挖掘模块
│   ├── research_agent/         # 研究智能体(完整)
│   ├── mine.py                  # 统一入口
│   ├── mine_high_sharpe_margin.py
│   ├── mine_high_margin.py
│   └── 工具脚本...
├── archive/legacy_scripts/      # 备份的冗余脚本
├── data/outputs/                # 输出结果
├── knowledge_base/              # AI记忆系统
└── docs/KNOWLEDGE/             # 知识文档
```

### 保留的脚本(7个)
- mine.py - 统一入口
- mine_high_sharpe_margin.py - 高Sharpe+Margin
- mine_high_margin.py - 高Margin
- test_pv87.py, check_submittable.py, check_field_format.py, test_api.py

### 已删除的冗余脚本(8个)
real_mining.py, real_mining_v2.py, find_submittable.py, improve_alphas.py, parallel_miner.py, api_test.py, debug_api.py, aggressive_miner.py

## 五、当前最佳候选

### Alpha #1
- 数据集: analyst4
- 字段: actual_eps_value_quarterly
- 表达式: `ts_mean(winsorize(actual_eps_value_quarterly), 25)`
- Sharpe: 1.00, Fitness: 1.43, M/T: 2.96

### Alpha #2
- 数据集: analyst4
- 字段: actual_dividend_value_quarterly
- 表达式: `ts_mean(winsorize(actual_dividend_value_quarterly), 15)`
- Sharpe: 0.82, Fitness: 1.20, M/T: 4.11

## 六、下一步方向

### 短期优化
1. 测试analyst4其他字段 + 窗口23-26
2. 尝试analyst4字段组合(如eps + dividend)
3. 探索analyst4更深窗口(如25-30区间更多值)

### 中期探索
1. 寻找其他analyst数据集看能否突破1.58
2. 测试不同地区(region)的analyst数据
3. 尝试组合多个analyst4字段

### 长期策略
1. 研究为何analyst4能同时实现Sharpe>1和M/T>1
2. 寻找类似特性的其他数据集
3. 建立回测验证流程

## 七、API限制与问题

- 429限流频繁
- 偶数窗口回溯期容易失败(原因未知)
- 部分数据集字段获取失败
- 多字段同时测试耗时较长

## 八、验证清单

- [x] 项目框架整理完成
- [x] 删除8个冗余脚本
- [x] 输出文件移至data/outputs/
- [x] analyst4发现Sharpe>1候选
- [x] 最佳表达式验证
- [ ] 更大窗口测试(>30)
- [ ] 其他analyst数据集对比
- [ ] 字段组合测试
