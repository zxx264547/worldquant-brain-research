> **[MANDATORY]** 开始量化研究工作前，必须先完整阅读 `PLAYBOOK.md`。
> 该文件包含操作流程、决策树和交接协议。跳过阅读将导致操作错误。

# WorldQuant BRAIN 量化研究项目

## 项目概述

AI主导的量化研究项目，目标是挖掘Sharpe >= 1.58的可提交Alpha。

**架构理念**：AI是大脑（决策者），Python脚本是工具（执行者）。
AI通过认知循环持续 感知→决策→执行→反思→记忆→进化。

---

## 认知循环协议（Cognitive Loop）

AI Agent的核心工作流：

```
PERCEIVE → PLAN → DISPATCH → REFLECT → REMEMBER → EVOLVE
    ↑                                            │
    └──────── Unified Knowledge Store ───────────┘
```

### CLI命令

| 命令 | 作用 |
|------|------|
| `python worldquant_brain/cli.py perceive` | 感知全局状态 |
| `python worldquant_brain/cli.py dispatch '{...}'` | 下发批量任务 |
| `python worldquant_brain/cli.py reflect <file>` | 分析结果提取insights |
| `python worldquant_brain/cli.py remember "..." -c 0.8` | 沉淀知识 |
| `python worldquant_brain/cli.py evolve` | 提议规则进化 |

### brain-data-scope 离线分析（感知阶段必用）

在 PERCEIVE 阶段，启动后优先查询本地数据库，避免盲目回测：

| 命令 | 作用 |
|------|------|
| `python worldquant_brain/scripts/brain_data_scope.py star <dataset>` | 数据集评级（★~★★★） |
| `python worldquant_brain/scripts/brain_data_scope.py badge <dataset>` | OS/IS Sharpe 比率 + 颜色徽章 |
| `python worldquant_brain/scripts/brain_data_scope.py neut <field> [dataset]` | 中性化效果分布 |
| `python worldquant_brain/scripts/brain_data_scope.py report <field> [dataset]` | 字段综合报告 |
| `python worldquant_brain/scripts/brain_data_scope.py ingest <results.json>` | 导入回测结果 |
| `python worldquant_brain/scripts/brain_data_scope.py ingest-all` | 批量导入 /tmp/multi_agent/ 所有结果 |

数据库位置：`worldquant_brain/data/field_analysis.db`
每次 batch 完成后自动执行 `ingest-all` 积累数据。

### 信号灯系统（决策阶段必用）

每批回测完成后，用信号灯判断方向：继续深挖 vs 止损换方向。

| 命令 | 作用 |
|------|------|
| `python worldquant_brain/scripts/direction_radar.py <results.json>` | 分析批次方向 |
| `python worldquant_brain/scripts/direction_radar.py <results.json> --verbose` | 详细诊断 |

四盏灯 + 行动：
- 🟢 GREEN → 加大回测预算
- 🟡 YELLOW → 谨慎继续 1-2 轮
- 🔴 RED → 结构性改动再评估
- ⚫ DEAD → 记录 anti_pattern，换方向

核心指标：算子多样性分数（6 大族的覆盖度）用于区分"池塘没鱼"和"鱼饵不对"。只用了 1-2 个族结果还差 → 拓宽算子再试。用了 4+ 个族还差 → 数据真没信号，果断放弃。

详见帖子 #2009 (JR57542)。

### seed_alpha_generator（论文驱动 Alpha 生成）

在探索新数据集前，先让 AI 读论文再写表达式，而不是凭空想象。

| 命令 | 作用 |
|------|------|
| 修改 `seed_alpha_generator.py` 顶部配置区 | 填入数据集ID、AI API Key |
| `python worldquant_brain/scripts/seed_alpha_generator.py` | 运行全链路生成 |

全链路：数据集发现 → arXiv + Semantic Scholar 论文检索 → LLM 生成 idea → 模板展开 → 批量表达式。

详见帖子 #39870945020183（XC83126）。

---

## 自进化机制

| 级别 | 对象 | 审批 |
|------|------|------|
| L1 自动 | 策略效果分数、优先级 | 无需审批 |
| L2 提议 | PPA阈值、时间窗口、CLAUDE.md规则 | 用户审批 |
| L3 记录 | 代码架构改进 | 用户实施 |

策略配置位于：`worldquant_brain/strategies/strategy_config.yaml`

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

### 6. VECTOR数据 + vec_min/vec_max同向极值匹配
VECTOR类型字段必须使用vec_min/vec_max（非vec_avg/vec_sum），遵循同向原则：
- 外层ts_min/ts_arg_min/group_min → 内层vec_min
- 外层ts_max/ts_arg_max/group_max → 内层vec_max
- 外层zscore(…)包装可成倍提升Sharpe
- 优先测试SECTOR中性化（非INDUSTRY）
- **已验证**：`zscore(-ts_max(vec_max(rsk60_offer), 22))` → Sharpe 2.02, 已提交

### 7. 网络/代理
- API调用**不要**走http://127.0.0.1:7897代理（会断开SSL）
- 直连api.worldquantbrain.com
- 限流后Retry-After可能长达30分钟+

### 8. 获取数据集字段的正确方法
**端点**：`/data-fields`（有连字符）

**参数**：`dataset.id`（注意是点号，不是dataSet或dataset）

**示例**：
```python
resp = session.get(f'{base_url}/data-fields', params={
    'dataset.id': 'sentiment23',
    'instrumentType': 'EQUITY',
    'region': 'USA',
    'delay': 1,
    'universe': 'TOP3000',
    'limit': 50
})
```

**字段命名规律**：
- sentiment23 → `snt23_` 开头（如 `snt23_neg_mean`）
- pv48 → `pv48_` 开头（如 `pv48_constituent_cap`）
- shortinterest3 → 直接用字段名（如 `mean_loan_rate`）

**错误示例**（会返回 "Invalid query"）：
- `dataSet` → ❌
- `dataset` → ❌
- `/datafields` → ❌

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

## Alpha 提交规则

### 提交成功的判断
**返回 HTTP 201 = 真正提交成功，其他都是失败**

| HTTP Status | 含义 |
|-------------|------|
| 201 | 提交成功，触发 OS 回测 |
| 403 + checks | 提交检查失败（被拒绝） |
| 429 | 限流（需等待后重试） |
| 400 | 参数错误或认证失败 |

### 验证真正提交成功
```python
resp = session.post(f'{base_url}/alphas/{alpha_id}/submit')

if resp.status_code == 201:
    # 真正提交成功
    pass
elif resp.status_code == 403:
    # 检查失败
    checks = resp.json().get('is', {}).get('checks', [])
```

### 检查已提交Alpha状态
```python
# dateSubmitted 有值 = 已提交
# status = 'SUBMITTED' = 已提交
# stage = 'OS' = 已触发 OS 回测
```

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

## 状态存储

研究状态持久化在 `worldquant_brain/state/` 目录（git 跟踪，支持跨用户继承）：

```
worldquant_brain/state/
├── alphas.json          # Alpha结果（git tracked）
├── experiments.json     # 实验历史（git tracked）
├── knowledge_events.json # 知识事件（git tracked）
├── rule_changes.json    # 规则变更（git tracked）
├── research_ledger.json # 研究总账（git tracked）
├── failure_log.json     # 失败记录（git tracked）
├── datasets.json        # 数据集元数据（git tracked）
├── valid_fields.json    # 有效字段（git tracked）
└── _runtime/            # 运行时临时（NOT tracked）
    ├── tasks.json       # 任务队列
    └── workers.json     # Worker状态
```

---

*最后更新：2026年5月*
