# PLAYBOOK — 量化研究操作手册

> 本文件是 WorldQuant BRAIN 量化研究系统的标准操作流程。
> 任何 AI 模型在开始工作前必须完整阅读本文件。

---

## 0. 启动检查清单

收到量化研究任务后，按以下顺序执行：

1. **读取进度** — `worldquant_brain/knowledge_base/memory/CURRENT_STATE.md`
2. **感知状态** — `python worldquant_brain/cli.py perceive`
3. **检查成果** — `worldquant_brain/state/alphas.json`（已有多少 Alpha、最佳 Sharpe）
4. **检查反模式** — `worldquant_brain/state/knowledge_events.json`（避免重复踩坑）
5. **决定行动** — 根据上述信息，参照下方决策树选择下一步

---

## 1. 认知循环标准流程

```
PERCEIVE → PLAN → DISPATCH → REFLECT → REMEMBER → EVOLVE
```

### Step 1: PERCEIVE（感知）

```bash
python worldquant_brain/cli.py perceive
```

返回：当前 Alpha 总数、最佳 Sharpe、可提交数、反模式数、策略效果排名。

### Step 2: PLAN（决策）

根据 perceive 返回的数据，选择动作：

| 条件 | 动作 |
|------|------|
| submittable_count > 0 且未提交 | 执行提交流程 |
| 无进行中任务 | 生成新 idea batch |
| 有待分析结果 | 执行 reflect |
| 策略效果持续低迷 | 执行 evolve 审视规则 |

### Step 3: DISPATCH（执行）

```bash
python worldquant_brain/cli.py dispatch '{"action": "mine", "expressions": [...], "settings": {...}}'
```

**必须遵守**：
- 每次恰好 8 个表达式
- 时间窗口只用：5, 22, 66, 120, 252, 504
- Fundamental/Volume 数据必须 rank() 包裹
- VECTOR 字段必须用 vec_min/vec_max（非 vec_avg/vec_sum）

### Step 4: REFLECT（反思）

```bash
python worldquant_brain/cli.py reflect <results_file>
```

返回：avg_sharpe、best_sharpe、PPA 通过数、方向建议。

**反思后必须执行信号灯判断**：

```bash
python worldquant_brain/scripts/direction_radar.py <results_file>
```

根据信号灯行动：
- 🟢 GREEN → 加大回测预算，继续当前方向
- 🟡 YELLOW → 谨慎继续 1-2 轮，尝试变体
- 🔴 RED → 结构性改动（换算子族、换中性化）
- ⚫ DEAD → 记录 anti_pattern，彻底换方向

### Step 5: REMEMBER（记忆）

```bash
python worldquant_brain/cli.py remember "发现insight内容" -c 0.8
```

值得记录的内容：
- 新发现的有效模式（哪个算子+字段组合效果好）
- 确认的死胡同（某方向彻底不行的证据）
- 参数敏感性（如 truncation=0.05 比 0.01 好 +0.27）

### Step 6: EVOLVE（进化）

```bash
python worldquant_brain/cli.py evolve
```

触发条件：24小时内完成 10+ 实验 且 距上次进化 > 6小时。

---

## 2. 决策树

### 继续当前方向 vs 换方向？

```
if 最近3批 avg_sharpe > 0.8 且 best > 1.2:
    → 继续深挖（加变体：换窗口、加嵌套）
elif 最近3批 avg_sharpe 0.3~0.8:
    → 拓宽算子族（检查 direction_radar 的多样性分数）
    → 如果只用了 1-2 个算子族 → 拓宽再试
    → 如果已用 4+ 个族还差 → 数据没信号，换方向
elif 最近3批 avg_sharpe < 0.3:
    → 立即止损，记录 anti_pattern，换数据集
```

### 选什么策略？

优先级按 `worldquant_brain/strategies/strategy_config.yaml` 中的 effectiveness 排序。当前：
1. shortinterest3_vecmax (0.9)
2. biasfree_analyst_vecmax (0.7)
3. analyst44_vecmax (0.6)
4. analyst4_eps (0.6)

### 探索新数据集前？

**必须先执行 brain-data-scope 预判**：

```bash
python worldquant_brain/scripts/brain_data_scope.py star <dataset>   # 数据集评级
python worldquant_brain/scripts/brain_data_scope.py badge <dataset>  # OS/IS Sharpe
python worldquant_brain/scripts/brain_data_scope.py report <field> [dataset]  # 字段报告
```

只投入 ★★ 以上的数据集。

---

## 3. 状态文件说明

所有状态存储在 `worldquant_brain/state/`（git 跟踪）：

| 文件 | 用途 | 查看时机 |
|------|------|---------|
| `alphas.json` | 所有回测结果 | 了解已有成果 |
| `experiments.json` | 实验批次 | 了解已试过的策略 |
| `knowledge_events.json` | 知识日志 | 查看洞察和反模式 |
| `research_ledger.json` | 研究总账 | 了解每轮决策历史 |
| `failure_log.json` | 失败记录 | 分析失败模式 |
| `rule_changes.json` | 规则变更 | 检查待审批的进化提议 |

---

## 4. 交接协议

完成一轮工作后，必须执行：

1. **更新进度** — 编辑 `knowledge_base/memory/CURRENT_STATE.md`
   - 当前阶段
   - 最佳成果
   - 下一步建议
2. **提交状态** — `git add worldquant_brain/state/ && git commit -m "research: <做了什么>"`
3. **推送** — `git push origin master`

Commit message 模板：
```
research: <方向> <结果>

- 最佳Sharpe: X.XX
- 测试了: <什么>
- 下一步: <建议>
```

---

## 5. 工具使用指南

### brain_data_scope（探索前必用）

| 命令 | 触发条件 |
|------|---------|
| `star <dataset>` | 决定是否投入新数据集前 |
| `badge <dataset>` | 需要 OS/IS 比率判断数据集质量 |
| `neut <field>` | 选择中性化方式前 |
| `report <field>` | 深入了解某字段潜力 |
| `ingest-all` | 每批回测完成后 |

### direction_radar（每批必用）

```bash
python worldquant_brain/scripts/direction_radar.py <results.json>
```

核心指标：**算子多样性分数**（6大族覆盖度）

### seed_alpha_generator（论文驱动）

探索新数据集时，先用论文指导生成 idea，而不是凭空想象：

```bash
# 修改脚本顶部的 DATASET_ID 和 API_KEY
python worldquant_brain/scripts/seed_alpha_generator.py
```

---

## 6. 故障排查

| 症状 | 解决方案 |
|------|---------|
| Fitness < 1.0 | Decay=2, Neut=Industry, Trunc=0.01 |
| Turnover > 70% | trade_when, Decay=3-5, ts_mean 平滑 |
| Weight Concentration | rank() 包裹, Trunc=0.01 |
| Correlation Fail | 改窗口/换字段/换算子 |
| in_progress > 15min | 重新认证 → 重启 |
| API 限流 | Retry-After 可能 30min+，等待即可 |

---

## 7. 禁止事项

- **不要** 重复测试已知的反模式（先查 knowledge_events.json）
- **不要** 忽略信号灯判断（DEAD 必须换方向）
- **不要** 在一个方向连续失败 > 3 批而不切换
- **不要** 修改 CLAUDE.md 核心法则（除非通过 L2 进化审批）
- **不要** 用 http://127.0.0.1:7897 代理调用 API（会断 SSL）
- **不要** 每次 batch 少于或多于 8 个表达式
- **不要** 忘记 git commit 状态文件
