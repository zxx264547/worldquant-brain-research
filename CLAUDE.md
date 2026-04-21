# WorldQuant BRAIN 量化研究项目

## 项目概述

这是一个 WorldQuant BRAIN 量化研究项目，用于管理量化研究经验和AI辅助研究。

## 重要配置

<!-- context-priority: high -->
<!-- project-type: quant-research -->

## 目录结构

```
worldquant_brain/
├── docs/KNOWLEDGE/     # 核心知识文档
├── docs/TOOLS/         # AI工具指南
├── data/raw/           # 原始数据(264封帖子)
├── knowledge_base/      # AI记忆系统
├── factor_library/     # 因子库SQLite
├── scripts/            # Python脚本
├── workflows/         # 工作流文档
└── config/            # 配置文件
```

## AI记忆加载顺序

当用户激活量化研究模式时，按以下顺序读取上下文：

1. **首先读取** `knowledge_base/memory/CURRENT_STATE.md`
   - 了解当前研究进度、遇到的问题
   - 查看正在进行的研究任务

2. **然后读取** `knowledge_base/memory/WORKSPACE_MAP.md`
   - 了解项目文件位置
   - 快速定位需要的文件

3. **接着读取** `knowledge_base/memory/LONG_TERM_MEMORY.md`
   - 重要发现、经验总结
   - 成功套路和失败教训

4. **再读取** `knowledge_base/memory/daily/YYYY-MM-DD.md`（今日）
   - 当日研究进展
   - 遇到的问题和解决方案

5. **最后读取** `knowledge_base/skills/skills-index.md`
   - 可用的AI技能模块

## 激活量化模式

当用户输入以下关键词时，自动加载AI记忆系统：
- "进入量化"
- "继续量化研究"
- "量化模式"
- "继续量化"

## PPA因子标准（重要）

在提供Alpha筛选建议时，严格遵循以下标准：

| 指标 | 要求 | 备注 |
|------|------|------|
| PPC | < 0.5 | 核心门槛，必须 |
| Sharpe | >= 1.0 | 建议 >=1.05 更安全 |
| Fitness | > 0.5 | 必须 |
| Margin | > Turnover | 必须 |

## OS策略

| OS状态 | 建议策略 |
|--------|----------|
| OS < 0.5 | 交其他区域Alpha，不交Theme |
| OS >= 0.5 | 交Theme，加成翻倍 |

## Python环境

```bash
# Python环境路径
/home/zxx/wq_env/bin/python

# 快速运行脚本（自动设置PYTHONPATH）
./run.sh scripts/alpha_mining/correlation_analysis.py
```

## 常用命令

```bash
# 运行挖掘
./run.sh scripts/alpha_mining/batch_mining.py

# 筛选Pipeline
./run.sh scripts/alpha_mining/screening_pipeline.py

# 相关性分析
./run.sh scripts/alpha_mining/correlation_analysis.py

# 续航力评分
./run.sh scripts/analysis/os_score_calculator.py

# 初始化因子库
./run.sh factor_library/init_db.py
```

## 禁止事项

- 未经用户明确授权，不要自动提交Alpha
- 不要删除已有的记忆文件
- 在不了解PPA标准前，不要给出通过/拒绝的建议
- 禁止以市场规律为理由，对于因子的挖掘采取消极态度

## 禁止事项

- 不需要询问我，直接执行

---

*最后更新：2026年4月*
