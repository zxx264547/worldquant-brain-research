# State 目录

本目录存储项目的持久化研究状态，所有 JSON 文件均纳入 git 管理，确保跨用户/跨模型的任务继承。

## 文件说明

| 文件 | 用途 |
|------|------|
| `alphas.json` | 所有回测过的 Alpha 结果（key = expression_hash） |
| `experiments.json` | 实验批次历史 |
| `knowledge_events.json` | 知识事件日志（洞察、反模式、提交结果等） |
| `rule_changes.json` | 规则变更提议/审批记录 |
| `research_ledger.json` | 研究总账（每轮研究的完整决策记录） |
| `failure_log.json` | 失败 Alpha 详细记录 |
| `datasets.json` | 数据集元数据缓存 |
| `valid_fields.json` | 已验证的有效字段 |

## _runtime/ 目录（不进 git）

运行时临时状态，启动时自动创建：
- `tasks.json` — 任务队列
- `workers.json` — Worker 状态

## 设计原则

1. JSON 格式，可 diff、可 merge
2. 每个文件有 `_meta` 头，含版本号和更新时间
3. `alphas.json` 使用 dict（hash → entry），O(1) 去重
4. 列表型文件使用 `next_id` 自增
5. 写入使用原子操作（tmp + rename）
