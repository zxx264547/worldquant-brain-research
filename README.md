# WorldQuant BRAIN 量化研究项目

> AI主导的量化Alpha研究系统 — 目标 Sharpe >= 1.58

## 认知循环

```
PERCEIVE → PLAN → DISPATCH → REFLECT → REMEMBER → EVOLVE
```

## 当前进展

**2026-05-14 里程碑：shortinterest3 突破**

| Alpha | 表达式 | Sharpe | 状态 |
|-------|--------|--------|------|
| S3-0001 | zscore(-ts_max(vec_max(max_loan_rate), 5)) | 1.91 | ✅ 可提交 |
| S3-0002 | zscore(-ts_max(vec_max(max_loan_rate), 22)) | 1.76 | ✅ 可提交 |
| S3-0003 | zscore(-ts_max(vec_max(max_loan_rate), 66)) | 1.61 | ✅ 可提交 |
| S3-0004 | zscore(-ts_max(vec_max(min_loan_rate), 22)) | 2.18 | ✅ 可提交 |
| S3-0005 | zscore(-ts_max(vec_max(mean_loan_rate), 22)) | 2.10 | ✅ 可提交 |

**关键突破**：shortinterest3 证券借贷数据 — 29个VECTOR字段 alphaCount=0，完全未被使用。复制 risk60 的 `zscore(-ts_max(vec_max()))` 模式，5/8达到可提交水平。

## 快速开始

```bash
# Python环境
/home/zxx/wq_env/bin/python

# 运行回测
python worldquant_brain/engine/backtest_runner.py

# 批量测试
python /tmp/multi_agent/batch_*.py

# 知识库CLI
python worldquant_brain/cli.py perceive    # 感知状态
python worldquant_brain/cli.py reflect     # 分析结果
python worldquant_brain/cli.py remember    # 沉淀知识
python worldquant_brain/cli.py evolve      # 进化规则
```

## 架构

```
worldquant_brain/
├── engine/                  # 核心引擎
│   ├── backtest_runner.py   # 回测执行器 (含自动知识沉淀)
│   ├── expression_builder.py # 表达式构建器
│   ├── skill_executor.py    # 技能执行器
│   └── settings_manager.py  # 设置管理器
├── scripts/core/
│   └── api_client.py        # API客户端 (含Alpha属性自动设置)
├── multi_agent/skills/      # AI技能模块
│   ├── alpha_submission_cn_template.json  # 中文提交模板
│   ├── handle_fitness_low.json
│   └── handle_turnover_high.json
├── knowledge_base/          # AI记忆系统
├── docs/KNOWLEDGE/          # 知识文档
│   ├── ALPHA_SUBMISSION_CN_TEMPLATE.md
│   ├── VEC_MIN_MAX_BREAKTHROUGH.md
│   └── FORUM_INDEX_TOOLS.md
├── strategies/              # 策略配置
│   └── strategy_config.yaml
└── data/                    # 数据
    ├── brain.db             # SQLite回测结果
    └── forum.sqlite3        # 论坛知识库
```

## 核心法则

### VECTOR数据 + vec_min/vec_max同向极值匹配
- 外层ts_min → 内层vec_min；外层ts_max → 内层vec_max
- zscore包装成倍提升Sharpe
- 优先SECTOR中性化

### 增量复杂度
- 0-op: rank/zscore（裸信号）
- 1-op: ts_mean/ts_decay/ts_delta
- 2-op+: ts_rank(ts_delta())等嵌套

### 时间窗口
仅用: 5, 22, 66, 120, 252, 504

### Alpha属性规范
- name: `前缀-序号` (如 S3-0001)，方便网页搜索
- tags: `ds:数据集` `op:算子` `w:窗口` `grade:A/B/C/D` `submittable`
- color: 绿(>=1.58)/黄(>=1.0)/蓝(>0.5)/红(<=0)
- 中文描述(>=100字/段，仅Sharpe>=1.0): Idea / Rationale for data / Rationale for operators

## PPA因子标准

| 指标 | 要求 |
|------|------|
| PPC | < 0.5 |
| Sharpe | >= 1.58 |
| Fitness | > 0.5 |
| Margin | > Turnover |

## 已验证数据集

| 数据集 | 最佳Sharpe | 状态 |
|--------|-----------|------|
| **shortinterest3** | **2.18** | ✅ 5个可提交 |
| risk60 | 2.37 | ❌ ProdCorr > 0.9 |
| analyst4 | 1.17 | 天花板 |
| analyst10 | 0.74 | 待优化 |
| biasfree_analyst | 测试中 | — |

## 知识库更新流程

```
回测完成 (Sharpe >= 1.0)
    → BacktestRunner._auto_knowledge()
    → wq_forum_rag EvolutionService
    → forum.sqlite3 (可被 wq-forum-rag search 检索)
```

## 文档

- [知识库索引](knowledge_base/skills/skills-index.md)
- [中文提交模板](docs/KNOWLEDGE/ALPHA_SUBMISSION_CN_TEMPLATE.md)
- [VEC_MIN_MAX突破](docs/KNOWLEDGE/VEC_MIN_MAX_BREAKTHROUGH.md)
- [AI工具指南](docs/TOOLS/AI_TOOLS_GUIDE.md)
- [数据集目录](docs/datasets_catalog.md)

---

*最后更新：2026-05-14*
