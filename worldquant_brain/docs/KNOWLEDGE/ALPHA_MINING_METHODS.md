# Alpha挖掘方法论

## 相关性分族 + 组内排序法

### 核心思路

当一个字段数据集跑出成百上千条调优结果时，真正难的不是找到高分Alpha，而是找到彼此不同、又足够优秀的Alpha。

### 操作步骤

1. **读取PnL序列**：读取每个Alpha的PnL数据
2. **计算相关矩阵**：两两计算相关性，得到相关矩阵
3. **设定阈值**：如0.8，高于阈值归为同一族
4. **连通族群**：A和B高相关、B和C高相关，则A、B、C同族
5. **分族排序**：按family_id排序，族内按评分降序

### 筛选价值

- 避免筛选结果集中在同一类信号
- 每类相关性族挑1-2条代表
- 不同方向的表达才是真正的独立机会

## 智能Alpha挖掘流程

```
批量处理数据集
    ↓
多轮筛选：
  - 首轮 min_sharpe=0.7
  - 次轮 min_sharpe=1.0
    ↓
控制并发（10并发）
    ↓
提取特征压缩数据集
    ↓
多维度评估：Fitness、Turnover、相关性
    ↓
存储入库
```

## 批量挖掘参数参考

| 参数 | 建议值 |
|------|--------|
| min_sharpe_step1 | 0.7 |
| min_sharpe_step2 | 0.7 |
| min_sharpe_step3 | 1.0 |
| min_fitness | 0.5 |
| max_turnover | 0.7 |
| submit_sharpe | 1.00 |
| submit_fitness | 0.6 |
| submit_turnover | 0.65 |
| batch_size | 10 |
| max_variants | 20 |
| concurrent_workers | 10 |

---

*来源：WorldQuant BRAIN论坛帖子*
