# WorldQuant BRAIN 量化研究项目

## 项目概述

AI辅助量化研究项目，目标是挖掘Sharpe >= 1.58的可提交Alpha。

---

## 目录结构

```
/home/zxx/worldQuant/
├── CLAUDE.md                    # 项目主文档(本文件)
├── README.md                    # 项目readme
├── posts_categorized.json       # 论坛帖子(已分类)
├── posts_raw.json              # 论坛帖子(原始)
│
├── .claude/                    # Claude Code配置
│   ├── agents/                # Claude Code Agents
│   │   ├── alpha-idea-generator.md
│   │   ├── alpha-deep-explorer.md
│   │   ├── alpha-explorer-worker.md
│   │   └── alpha-research-team-lead.md
│   ├── plans/                 # 计划文件
│   └── settings.local.json
│
└── worldquant_brain/
    ├── config/                 # 配置文件
    │   ├── user_config.json    # 用户凭据
    │   ├── mcp_config.json    # MCP配置
    │   └── settings.json
    │
    ├── data/                   # 数据目录
    │   ├── raw/               # 原始数据
    │   └── outputs/           # 输出结果
    │
    ├── docs/                   # 文档
    │   ├── KNOWLEDGE/         # 知识文档
    │   └── TOOLS/             # 工具指南
    │
    ├── factor_library/        # 因子库SQLite
    │
    ├── knowledge_base/         # AI记忆系统
    │   ├── memory/            # 记忆文件
    │   │   ├── CURRENT_STATE.md
    │   │   ├── LONG_TERM_MEMORY.md
    │   │   ├── WORKSPACE_MAP.md
    │   │   └── daily/YYYY-MM-DD.md
    │   └── skills/            # 技能索引
    │
    ├── multi_agent/           # Multi-Agent系统
    │   ├── configs/            # Agent配置
    │   ├── skills/            # 技能模块
    │   ├── memory/            # 记忆模块
    │   ├── tools/             # 工具定义
    │   ├── init_system.py     # 初始化脚本
    │   └── README.md
    │
    └── scripts/               # Python脚本
        ├── alpha_mining/      # Alpha挖掘
        ├── core/              # 核心模块
        ├── research_agent/    # 研究Agent
        └── analysis/          # 分析工具
```

---

## AI记忆加载顺序

当用户激活量化研究模式时，按以下顺序读取：

1. `knowledge_base/memory/CURRENT_STATE.md` - 当前进度
2. `knowledge_base/memory/WORKSPACE_MAP.md` - 文件位置
3. `knowledge_base/memory/LONG_TERM_MEMORY.md` - 经验总结
4. `knowledge_base/memory/daily/YYYY-MM-DD.md` - 今日进展
5. `knowledge_base/skills/skills-index.md` - 技能模块

**激活关键词**：进入量化、继续量化研究、量化模式、继续量化

---

## Claude Code Agents

| Agent | 用途 |
|-------|------|
| `alpha-research-team-lead` | 主协调器 - 协调整个研究流程 |
| `alpha-idea-generator` | 产生Alpha ideas |
| `alpha-explorer-worker` | 探索Alpha |
| `alpha-deep-explorer` | 深度优化Alpha |

---

## 核心法则（OB53521工作流）

### 1. 增量复杂度
- **0-op**: rank/zscore（裸信号）
- **1-op**: ts_mean/ts_decay/ts_delta
- **2-op+**: ts_rank(ts_delta())等嵌套

### 2. 时间窗口
仅用: 5, 22, 66, 120, 252, 504

### 3. 归一化
Fundamental/Volume数据必须rank()包裹

### 4. 批量8个
每次create_multiSim必须8个Alpha

### 5. 15分钟熔断
in_progress>15分钟 → 重新认证 → 重启

---

## 故障排查表

| 症状 | 解决方案 |
|------|---------|
| Fitness < 1.0 | Decay=2, Neut=Industry, Trunc=0.01 |
| Turnover > 70% | trade_when, Decay=3-5, ts_mean |
| Weight Concentration | rank()包裹, Trunc=0.01 |
| Correlation Fail | 改窗口, 换字段, 换算子 |

---

## PPA因子标准

| 指标 | 要求 |
|------|------|
| PPC | < 0.5 |
| Sharpe | >= 1.58 (目标) |
| Fitness | > 0.5 |
| Margin | > Turnover |

---

## Python环境

```bash
/home/zxx/wq_env/bin/python
```

## 常用命令

```bash
# 初始化Multi-Agent系统
python3 worldquant_brain/multi_agent/init_system.py

# Alpha挖掘
/home/zxx/wq_env/bin/python worldquant_brain/scripts/alpha_mining/new_direction_mining.py

# 筛选Pipeline
/home/zxx/wq_env/bin/python worldquant_brain/scripts/alpha_mining/screening_pipeline.py
```

---

## 共享存储

```
/tmp/multi_agent/
├── ideas.json       # Idea队列
├── results.json      # 结果队列
├── memory.json      # 探索记忆
├── configs/         # 运行时配置
├── skills/          # 运行时技能
├── prompts/         # 运行时提示词
└── logs/            # 日志
```

---

*最后更新：2026年4月*
