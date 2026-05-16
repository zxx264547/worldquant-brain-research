# WorldQuant BRAIN 量化研究项目

> AI主导的量化Alpha研究系统 — 首个已提交Alpha：EUR Sharpe 1.84

---

## 最新里程碑 (2026-05-16)

**首个 Alpha 成功提交**: `omnKPLX5` (A18)
- 表达式: `zscore(-ts_max(vec_max(mean_loan_rate), 66)) * (group_rank(ts_mean(volume, 20), sector) > 0.03)`
- 区域: EUR / TOPCS1600 / SECTOR / decay=6
- IS Sharpe: **1.84**, Status: **ACTIVE/OS**

**EUR 策略验证**: mean_loan_rate w66 在 EUR 达到 1.81-1.84，高于 USA 同公式。EUR 新区竞争少，prod_corr 更容易通过。

---

## 快速开始

### 首次使用
```bash
# 1. 创建 Python 环境
python3.12 -m venv wq_env && source wq_env/bin/activate
pip install requests pandas

# 2. 配置 BRAIN 账号
cp worldquant_brain/config/user_config.json.example worldquant_brain/config/user_config.json
# 编辑填入邮箱密码

# 3. 验证
wq_env/bin/python -c "
from worldquant_brain.scripts.core.api_client import RetryableBrainClient
import asyncio
asyncio.run(RetryableBrainClient().ensure_authenticated())
print('OK')
"
```

详见 [onboarding skill](worldquant_brain/knowledge_base/skills/onboarding.md)

### 日常使用
```bash
# Python环境
/home/zxx/wq_env/bin/python

# Alpha提交（必须用curl -L跟踪303）
python worldquant_brain/scripts/submit_alpha.py <alpha_id>

# 离线数据分析
python worldquant_brain/scripts/brain_data_scope.py star <dataset>
python worldquant_brain/scripts/brain_data_scope.py badge <dataset>

# 信号灯系统
python worldquant_brain/scripts/direction_radar.py <results.json>

# 论文驱动Alpha生成
python worldquant_brain/scripts/seed_alpha_generator.py
```

---

## 认知循环

```
PERCEIVE → PLAN → DISPATCH → REFLECT → REMEMBER → EVOLVE
```

| 阶段 | 工具 | 作用 |
|------|------|------|
| PERCEIVE | `brain_data_scope.py` | 离线查历史数据 |
| PERCEIVE | `CURRENT_STATE.md` | 当前进展 |
| DECIDE | `direction_radar.py` | 信号灯判断方向 |
| EXECUTE | `backtest_runner.py` | 批量回测 |
| SUBMIT | `submit_alpha.py` | curl -L 提交 |
| REMEMBER | `ingest-all` | 导入结果到数据库 |

---

## 工具集

| 工具 | 来源 | 作用 |
|------|------|------|
| `brain_data_scope.py` | 帖子 #40091088861591 | 离线 SQLite 数据分析 |
| `direction_radar.py` | 帖子 #2009 | 信号灯系统 + 算子多样性 |
| `seed_alpha_generator.py` | 帖子 #39870945020183 | arXiv 论文驱动 Alpha 生成 |
| `submit_alpha.py` | 项目自研 | curl -L 正确提交 Alpha |

---

## 核心法则

### VECTOR数据 + vec_min/vec_max同向极值匹配
- 外层 ts_max → 内层 vec_max；外层 ts_min → 内层 vec_min
- zscore 包装成倍提升 Sharpe
- 优先 SECTOR 中性化

### 增量复杂度
- 0-op: rank/zscore（裸信号）
- 1-op: ts_mean/ts_decay/ts_delta
- 2-op+: 嵌套组合

### EUR 特殊经验
- 窗口偏长（66 优于 22）
- decay 有帮助（4-6）
- trade_when 过滤成交量低的股票
- mean_loan_rate 优于 min_loan_rate
- prod_corr 门槛比 USA 低

---

## 数据集状态

| 数据集 | 区域 | 最佳 Sharpe | 状态 |
|--------|------|-----------|------|
| **shortinterest3** | USA | 2.45 | ❌ prod_corr 0.95 |
| **shortinterest3** | EUR | **1.84** | ✅ 已提交 |
| shortinterest3 | ASI | 1.20 | 未达标 |
| risk60 | USA | 2.37 | ❌ prod_corr > 0.9 |
| analyst4 | USA | 1.17 | 未达标 |
| 15+ 其他数据集 | USA | < 1.0 | 信号太弱 |

---

## 已提交 Alpha

| 编号 | Alpha ID | 区域 | Sharpe | 状态 |
|------|----------|------|--------|------|
| A18 | omnKPLX5 | EUR | 1.84 | ACTIVE/OS |
| A19 | 0mAEmWL1 | EUR | 1.84 | ❌ SELF_CORR |
| A20 | kqn3AA6O | EUR | 1.64 | ❌ SELF_CORR |
| A21 | YPNpRl2w | EUR | 1.62 | ❌ SELF_CORR |

---

## 架构

```
worldquant_brain/
├── engine/                  # 核心引擎
│   ├── backtest_runner.py   # 回测执行器
│   └── settings_manager.py  # 设置管理器
├── scripts/
│   ├── core/api_client.py   # API客户端
│   ├── submit_alpha.py      # Alpha提交 (curl -L)
│   ├── brain_data_scope.py  # 离线数据分析
│   ├── direction_radar.py   # 信号灯系统
│   └── seed_alpha_generator.py # 论文驱动生成
├── knowledge_base/
│   ├── memory/              # AI记忆
│   └── skills/              # 技能文档
│       ├── onboarding.md    # 首次启动指南
│       ├── alpha-submit.md  # 提交方法
│       └── skills-index.md  # 技能索引
├── data/
│   ├── field_analysis.db    # 离线分析数据库
│   └── forum.sqlite3        # 论坛知识库 (2173篇)
└── config/
    └── user_config.json     # BRAIN账号 (不提交Git)
```

---

## PPA 提交标准

| 指标 | 要求 |
|------|------|
| Sharpe | >= 1.58 |
| Fitness | > 0.5 |
| PPC | < 0.5 |
| Margin | > Turnover |
| Turnover | > 0.01 且 < 0.7 |
| ProdCorr | < 0.7 |
| Weight Conc. | < 0.1 |

---

## 论坛知识集成

项目已集成三篇核心论坛帖子：
- #40091088861591 — brain-data-scope 离线分析工具
- #2009 — 信号灯系统 + 算子多样性理论
- #39870945020183 — seed_alpha_generator 论文驱动

---

*最后更新：2026-05-16*
