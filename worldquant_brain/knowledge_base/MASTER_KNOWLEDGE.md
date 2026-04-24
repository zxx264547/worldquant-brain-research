# WorldQuant BRAIN 知识库

> 自动生成于 2026-04-23 18:05:44

数据来源: 2231 封邮件 + 264 篇帖子

---

## 目录

1. [数据集速查](#数据集速查)
2. [模板函数](#模板函数)
3. [指标标准](#指标标准)
4. [实战经验](#实战经验)

---

## 数据集速查

| 数据集 | 频次 | 说明 |
|--------|------|------|
| `pv1` | 5 | 价格/成交量 |
| `pv87` | 3 | 综合技术面数据 |
| `fundamental6` | 2 | 基本面数据 |
| `analyst10` | 1 | 分析师数据 |
| `wds` | 1 | 全球市场数据 |

## 模板函数

| 函数 | 频次 | 用途 |
|------|------|------|
| `rank()` | 19 | 横截面排名 |
| `ts_mean()` | 17 | 时间序列均值 |
| `winsorize()` | 12 | 去极值 |
| `ts_rank()` | 11 | 时间序列排名 |
| `decay_linear()` | 10 | 线性衰减 |
| `signed_power()` | 9 | 符号幂变换 |
| `ts_delta()` | 8 | 时间序列变化 |
| `correlation()` | 3 | 待补充 |
| `ts_corr()` | 2 | 滚动相关性 |

## 指标标准

### PPA因子标准

| 指标 | 标准 | 说明 |
|------|------|------|
| PPC | < 0.5 | 核心门槛 |
| Sharpe | >= 1.0 | 建议 >= 1.05 |
| Fitness | > 0.5 | 必须 |
| Margin | > Turnover | 必须 |

### 常见指标模式

- OS (来源: email)
- Sharpe (来源: email)
- Sharpe (来源: email)
- OS (来源: email)
- Sharpe (来源: email)
- Sharpe (来源: email)
- Sharpe (来源: email)
- Margin (来源: email)
- Margin (来源: email)
- Sharpe (来源: email)
- Fitness (来源: email)
- Sharpe (来源: email)
- Fitness (来源: email)
- Fitness (来源: email)
- OS (来源: email)
- Sharpe (来源: email)
- Turnover (来源: email)
- Fitness (来源: email)
- OS (来源: email)
- Sharpe (来源: email)

## 实战经验

- 等学生优惠快到期时再通过此方法“续命” (来源: email)
- 建议在竞赛期间多次提交Notebook，以便从研究顾问处获得反馈并持续改进 (来源: email)
- 为充分利用这些优势，我建议：- 在设计因子时将任务拆分，将AI生成的构思视为规划输出，由“门下省”补充风险控管步骤；- 利用看板实时监控多步骤任务执行，一旦出现偏差（如模型跑偏），可人工干预停止或修正 (来源: email)
- 用户阶段能多提交alpha就尽量多提交，只要累计交够100个（包含用户阶段提交的数量），就可以提交super alpha了，而且super alpha会单独计入一个专属池子计算，对后续排名有一定帮助 (来源: email)
- 写 `MEMORY.md`  - 新当天进展：写当天 `memory`  - 新启动规则或目录治理：写 `AI_CONTEXT_LITE`  - 新脚本、模板、提示词索引：写 `skills\skil (来源: forum)
- 模型越强，裸信号质量通常越高 (来源: forum)
- 解决Robust universe Sharpe / Sub-universe Sharpe / Weight concentration 问题 by XW90844 (来源: forum)
- 不要迷信AI一定能出结果 (来源: forum)
- 用户阶段能多提交alpha就尽量多提交，只要累计交够100个（包含用户阶段提交的数量），就可以提交super alpha了，而且super alpha会单独计入一个专属池子计算，对后续排名有一定帮助 (来源: forum)
- 1.不同风险中性化：我经常跑的中性化通常是crowding，这个中性化首先跑的比较快，整体上找到pc低的alpha概率大一些，主要快速测试信号，找到有信号的alpha再来试试其他中性化比如这个alph (来源: forum)
- 为充分利用这些优势，我建议：- 在设计因子时将任务拆分，将AI生成的构思视为规划输出，由“门下省”补充风险控管步骤；- 利用看板实时监控多步骤任务执行，一旦出现偏差（如模型跑偏），可人工干预停止或修正 (来源: forum)
- 建议在竞赛期间多次提交Notebook，以便从研究顾问处获得反馈并持续改进 (来源: forum)
- <0.6，就放弃，>0.6,就尝试用group_op，优先使用group_rank和signed_power，大部分都能得到有效提升 (来源: forum)
- 优先调整 (来源: forum)
- 等学生优惠快到期时再通过此方法“续命” (来源: forum)
- 最开始接触的时候没有代码，拿着24年的培训课程(几乎马赛克的视频，一帧一帧去看代码怎么编写，中间问过很多ai没有解决办法.) (来源: forum)
- 1. 不能只重复在一个category中做因子，尤其是一些容易过拟合的category，例如pv，model等，因子尽量分散在不同category中 (来源: forum)
