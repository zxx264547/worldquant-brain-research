# 工作区地图

> 项目目录结构速查

```
worldquant_brain/
├── docs/                        # 文档中心
│   ├── KNOWLEDGE/              # 知识文档
│   └── TOOLS/                  # 工具文档
├── data/                        # 数据目录
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后数据
│   ├── datasets/               # 数据集缓存
│   └── outputs/               # 输出结果
├── knowledge_base/              # 知识库
│   ├── index.md                # 总入口
│   ├── memory/                 # AI记忆
│   │   ├── CURRENT_STATE.md    # 当前状态
│   │   ├── WORKSPACE_MAP.md   # 工作区地图
│   │   ├── LONG_TERM_MEMORY.md # 长期记忆
│   │   └── daily/             # 每日记录
│   └── skills/                # Skills索引
├── factor_library/             # 因子库
│   ├── factor_library.db      # SQLite数据库
│   └── factors/               # 因子代码
├── scripts/                    # 脚本工具
│   ├── alpha_mining/          # Alpha挖掘
│   ├── data_processing/        # 数据处理
│   ├── automation/            # 自动化
│   └── analysis/              # 分析
├── workflows/                  # 工作流
└── config/                    # 配置文件
```

## 关键文件

| 文件 | 用途 |
|------|------|
| `config/settings.json` | 全局设置 |
| `config/mcp_config.json` | MCP配置 |
| `factor_library/factor_library.db` | 因子数据库 |

## 快速命令

```bash
# 查看当前状态
cat knowledge_base/memory/CURRENT_STATE.md

# 更新今日记录
echo "# $(date +%Y-%m-%d)" > knowledge_base/memory/daily/$(date +%Y-%m-%d).md

# 检查因子库
sqlite3 factor_library/factor_library.db "SELECT * FROM factors LIMIT 5;"
```

---

*更新时间：2026年4月*
