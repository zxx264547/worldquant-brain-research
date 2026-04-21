# WorldQuant BRAIN 量化研究项目

> 基于WorldQuant BRAIN平台的量化研究知识管理与自动化系统

## 功能特性

- **知识库管理**：264封论坛帖子分类整理
- **AI工具集成**：Codex、Gemini CLI、OpenCode配置指南
- **Alpha挖掘**：批量挖掘、多轮筛选、相关性去重
- **因子库**：SQLite因子库，追踪管理所有Alpha
- **自动化**：TARE+OCR无人值守配置

## 快速开始

### 1. 初始化项目

```bash
cd worldquant_brain
python3 factor_library/init_db.py
```

### 2. 配置AI工具

参考 `docs/TOOLS/AI_TOOLS_GUIDE.md`

### 3. 开始研究

```bash
# 挖掘Alpha
python3 scripts/alpha_mining/batch_mining.py

# 筛选
python3 scripts/alpha_mining/screening_pipeline.py
```

## 核心标准

### PPA因子
- PPC < 0.5
- Sharpe >= 1.0
- Fitness > 0.5
- Margin > Turnover

### OS策略
- OS < 0.5: 稳收益
- OS >= 0.5: 交Theme加成

## 目录结构

| 目录 | 用途 |
|------|------|
| `docs/KNOWLEDGE/` | 核心知识文档 |
| `docs/TOOLS/` | 工具使用指南 |
| `knowledge_base/` | AI记忆系统 |
| `factor_library/` | 因子数据库 |
| `scripts/` | Python脚本 |
| `workflows/` | 工作流文档 |

## 文档

- [知识库索引](knowledge_base/index.md)
- [PPA因子标准](docs/KNOWLEDGE/PPA_FACTOR_STANDARDS.md)
- [VF攻略](docs/KNOWLEDGE/VALUE_FACTOR_GUIDE.md)
- [Alpha挖掘方法](docs/KNOWLEDGE/ALPHA_MINING_METHODS.md)
- [AI工具指南](docs/TOOLS/AI_TOOLS_GUIDE.md)

---

*整理时间：2026年4月*
