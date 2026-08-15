---
name: wq-skills-index
description: "WorldQuant BRAIN 项目可用技能索引：列出所有 alpha-* 角色技能与 wq-* 工具技能及其用途。需要了解项目有哪些技能模块、选择合适技能执行任务时使用。"
whenToUse: "不确定项目有哪些技能可用，或需要按用途挑选技能（角色委派/提交/启动配置）时使用。"
---

# Skills 索引

> 可用的AI技能模块（DSH 框架自动发现于 `.agents/skills/`）

## 角色技能（Alpha 研究 Agent，来自原 Claude Code Agents）

| Skill名称 | 用途 | 使用场景 |
|-----------|------|----------|
| `alpha-research-team-lead` | AI研究主管 — 认知循环协调 | 驱动整个研究流程：感知→决策→执行→反思→记忆→进化 |
| `alpha-idea-generator` | Alpha想法生成 | 基于数据集和字段生成新Alpha ideas（增量复杂度 0-op→1-op→2-op） |
| `alpha-explorer-worker` | Alpha探索执行 | 系统化测试 idea 队列，运行模拟并记录结果 |
| `alpha-deep-explorer` | Alpha深度优化 | 把 Sharpe>1.0 的 Alpha 优化到提交标准（>=1.58） |
| `alpha-research-assistant` | 论坛/邮件调研 | 搜索论坛和QQ邮件，将有用内容沉淀到知识库 |

## 工具技能（项目操作）

| Skill名称 | 用途 | 使用场景 |
|-----------|------|----------|
| `wq-onboarding` | 项目启动配置 | 克隆项目后首次使用、环境搭建、认证验证 |
| `wq-alpha-submit` | Alpha 提交 | 提交 Alpha、处理 303 重定向、验证提交状态 |
| `wq-skills-index` | 技能索引 | 本文件 |

## 内置Skills（Claude Code 时代遗留，未迁移）

以下技能在 Claude Code 的 skills 系统下存在，DSH 中暂无对应文件，需要时可按名称在知识库中检索实现方式：

| Skill名称 | 用途 |
|-----------|------|
| `brain-datafield-exploration-general` | 字段全面分析 |
| `alpha-pattern-detector` | Alpha模式检测 |
| `backtest-analyzer` | 回测结果分析 |
| `pnl-scoring` | PnL续航力评分 |
| `alpha-submission-checker` | 提交前检查 |
| `correlation-family-splitter` | 相关性分族工具 |
