# Multi-Agent Alpha科研系统

> 基于OB53521 + 世坤经验 + Claude Code Agents

## 已创建的Agents

| Agent | 描述 |
|-------|------|
| `alpha-idea-generator` | 产生Alpha ideas |
| `alpha-deep-explorer` | 深度优化有潜力的Alpha |
| `alpha-explorer-worker` | 并行探索Alpha |

## 目录结构

```
worldquant_brain/multi_agent/
├── configs/                     # Agent配置
│   ├── team_lead.json
│   ├── worker.json
│   └── troubleshooting.json
├── skills/                      # 技能模块
│   ├── handle_fitness_low.json
│   └── handle_turnover_high.json
├── memory/                     # 记忆模块
│   └── research_memory.py
├── README.md
└── init_system.py

/tmp/multi_agent/               # 共享存储
├── ideas.json                  # Idea队列
├── results.json                # 结果队列
├── memory.json                 # 探索记忆
├── configs/                    # 运行时配置
├── skills/                     # 运行时技能
├── prompts/                    # 运行时提示词
└── logs/                       # 日志
```

## Agent职责

### alpha-idea-generator
- 基于数据集产生Alpha ideas
- 遵循0-op→1-op→2-op增量复杂度
- 时间窗口: 5, 22, 66, 120, 252, 504
- Fundamental/Volume必须rank()包裹

### alpha-explorer-worker (可创建多个)
- 从ideas.json读取分配的ideas
- 0-op裸信号: rank/zscore
- 1-op演化: ts_mean/ts_decay/ts_delta
- 批量8个法则
- 15分钟熔断

### alpha-deep-explorer
- 读取Sharpe>1.0的Alpha
- Fitness<1.0: Decay=2, Neut=Industry, Trunc=0.01
- Turnover>70%: trade_when, Decay=3-5
- 目标: Sharpe>=1.58

## 启动流程

```bash
# Step 1: 初始化共享存储
python3 /home/zxx/worldQuant/worldquant_brain/multi_agent/init_system.py

# Step 2: 使用/agent命令确认Agents已创建
# alpha-idea-generator
# alpha-deep-explorer
# alpha-explorer-worker

# Step 3: 通过SendMessage与TeamLead协调
```

## 故障排查

| 症状 | 方案 |
|------|------|
| Fitness<1.0 | Decay=2, Neut=Industry, Trunc=0.01 |
| Turnover>70% | trade_when, Decay=3-5, ts_mean |
| Weight Concentration | rank()包裹, Trunc=0.01 |
| Correlation Fail | 改窗口, 换字段, 换算子 |
