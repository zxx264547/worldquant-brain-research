# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展
> 最后更新：2026-06-14 12:52

## 研究进度

- 当前阶段：**API提交检查进行中** - 模拟引擎仍卡35%，提交API部分恢复
- 最佳成绩：**Sharpe 2.53** - qMgEkAbj (本地测试)
- **待提交Alpha**: 19个本地已测Alpha，Sharpe 1.98-2.53
- **测试日期**: 2026-06-14

## API状态

### 模拟引擎（故障持续）
- 新模拟创建成功，但卡在35%进度不完成
- 服务器端问题，无法完成回测

### 提交API（部分恢复）
- **submit_alpha API工作正常** - 返回完整检查结果
- **HTTP 400** = Alpha不存在（未提交过）
- **HTTP 429** = 速率限制（需等待）
- **关键阻塞1**: CONCENTRATED_WEIGHT - 3个最佳Alpha失败（双窗口组合）
- **关键阻塞2**: LOW_SUB_UNIVERSE_SHARPE - 单窗口Alpha失败

## 提交检查结果（2026-06-14）

| Alpha ID | Sharpe | CW | SUS | Prod | 状态 |
|----------|--------|-----|-----|------|------|
| qMgEkAbj | 2.53 | FAIL | PASS | PENDING | CW失败 |
| VkOdOMLb | 2.49 | FAIL | PASS | PENDING | CW失败 |
| Grk2o7wP | 2.34 | FAIL | PASS | PENDING | CW失败 |
| A1nqO7mQ | 2.46 | PASS | FAIL | PENDING | SUS失败 |
| 1Yo6nJXz | 1.91 | PASS | FAIL | PENDING | SUS失败 |
| 78dWLxe8 | 1.84 | PASS | FAIL | PENDING | SUS失败 |
| rKWYd0m8 | 2.01 | PASS | FAIL | PENDING | SUS失败 |

**模式发现**:
- CW-FAIL = 双窗口组合 (`zscore(...5) + zscore(...66)`)
- CW-PASS = 单窗口 (`zscore(-ts_max(vec_max(field), 22))`)
- CW-PASS的Alpha全部倒在LOW_SUB_UNIVERSE_SHARPE

## 下一步任务

1. **等待速率限制冷却** - 重试429限流的Alpha
2. **寻找通过SUS的模式** - CW-PASS Alpha为何失败SUS？
3. **尝试INDUSTRY/SECTOR中性化** - 可能修复SUS
4. **等待模拟引擎恢复** - 才能测试新表达式

## 已提交Alpha（29个）

| Alpha ID | 提交日期 | Sharpe | 数据集 |
|----------|----------|--------|--------|
| GrkYbRY3 | 2026-05-25 | 1.91 | - |
| omnKPLX5 | 2026-05-15 | 1.84 | - |
| NeZvvYq | 2025-04-12 | 2.21 | - |
| ... | ... | 1.58-2.21 | - |

## 核心问题

### 1. Prod Correlation过高
- 所有本地Alpha的Prod Correlation都>0.8
- 阈值是0.7，超过则被拒绝
- 解决方案：signed_power(zscore(...), 10)可以将Prod Corr降到0.682

### 2. 模拟引擎卡35%
- 服务器端问题，所有新模拟无法完成
- 只能等待服务器恢复

## 数据集状态

### analyst44
- 50个VECTOR字段，字段前缀：`anl44_2_*`
- 字段：bps, ebitda, eps, cfps, sales, ni, capex, fcfps等
- 未测试

### pv48
- VECTOR字段：current_industry_code_r3000e, growth_share_change_amt_dynamic等
- MATRIX字段：pv48_constituent_cap, pv48_constituent_sharesout等
- 未测试

## 下一步任务

1. **等待模拟引擎恢复**
2. **使用signed_power变换创建新Alpha**
3. **测试analyst44数据集** - 等引擎恢复后

## 已验证的解决方案

### signed_power降相关性
- `signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 10)` → Prod_Corr=0.682
- 功率参数10可将Prod Correlation从>0.9降到0.682
- 这是通过提交检查的关键

## API状态详情

### 模拟引擎（故障）
- 创建模拟成功，返回simulation ID
- 轮询时永远卡在35%进度，无法完成

### 提交API（严重故障）
- **根因**: 服务器发送303重定向到 `http://api.worldquantbrain.com:443/...`（HTTP scheme + HTTPS port = 无效URL）
- **现象**: 客户端修复URL后再次POST，服务器仍返回303，形成无限重定向循环
- **错误码**: 400 "The plain HTTP request was sent to HTTPS port"
- **影响**: 所有Alpha无法通过API提交，只能通过Web控制台手动提交

## API状态详情

### 模拟引擎（故障）
- 创建模拟成功，返回simulation ID
- 轮询时永远卡住不返回alpha_id
- 尝试等待15分钟仍无结果

### 提交API（故障）
- **O0oJvZn1**: POST返回303 → Location: `http://api.worldquantbrain.com:443/...` (http scheme + HTTPS port 443 = 格式错误)
- **blvPL7Yp**: POST返回429 THROTTLED
- **xAeGmO8m**: 首次POST返回201，后续重试返回429
- 根因：服务器配置问题，WSL2下无客户端解决方案

## 通过PPA的Alpha（9个）

| Alpha ID | Sharpe | Margin | Turnover | 数据集 |
|----------|--------|--------|----------|--------|
| O0oJvZn1 | 2.50 | 0.0354 | 0.0326 | shortinterest3 |
| XgkA6oeX | 2.49 | 0.0403 | 0.0305 | shortinterest3 |
| xAeGmO8m | 2.48 | 0.0419 | 0.0257 | shortinterest3 |
| blNzWNQR | 2.36 | 0.0363 | 0.0246 | shortinterest3 |
| MPk0mNM8 | 2.18 | 0.0449 | 0.0198 | shortinterest3 |
| blvPL7Yp | 1.98 | 0.0285 | 0.0228 | risk60 |
| kqQmORNd | 1.97 | 0.0280 | 0.0230 | risk60 |
| 9qJ6d5Yr | 1.94 | 0.0280 | 0.0230 | risk60 |
| omVzkzAE | 1.91 | 0.0280 | 0.0230 | risk60 |

**注意**: shortinterest3系列有自相关性anti-pattern，risk60系列无此问题

## 关键发现

### API问题 (严重)
1. **模拟引擎卡35%**: 所有模拟在35%进度时卡住，无法完成
2. **提交API返回400错误**: POST请求被拒绝，原因是服务器redirect到http://api.worldquantbrain.com:443/... (HTTP URL带HTTPS端口)，这是服务器配置问题
3. **WSL2网络问题**: POST请求被拦截并被当作HTTP请求处理

### CONCENTRATED_WEIGHT是主要阻塞原因
- **window 5 导致CONCENTRATED_WEIGHT FAIL**：任何包含window 5的表达式都会失败
- **单窗口66最安全**: `zscore(-ts_max(vec_max(field), 66))`

### 验证有效的Alpha (本地测试)
| Alpha ID | Sharpe | 表达式 |
|----------|--------|--------|
| qMgEkAbj | 2.53 | zscore(-ts_max(vec_max(min_loan_rate), 5)) + zscore(-ts_max(vec_max(min_loan_rate), 66)) |
| xAeGmO8m | 2.48 | zscore(-ts_max(vec_max(min_loan_rate), 66)) |
| A1nqO7mQ | 2.46 | zscore(-ts_max(vec_max(min_loan_rate), 22)) |
| QPEYPVJX | 2.42 | zscore(-ts_max(vec_max(mean_loan_rate), 22)) + zscore(-ts_max(vec_max(min_loan_rate), 22)) |

## 关键发现

### CONCENTRATED_WEIGHT是主要阻塞原因
- **window 5 导致CONCENTRATED_WEIGHT FAIL**：任何包含window 5的表达式都会失败
- **window 22+66 组合成功**：O0oJvZn1通过，但qMgEkAbj/VkOdOMLb失败（都是22+66，奇怪）

### API问题
- 模拟引擎：持续卡在35%，无法完成新模拟
- 429限流：连续提交后触发，需等待2-3分钟

### 成功模式
- **ts_mean smoothing**: `ts_mean(zscore(-ts_max(vec_max(field), window)), smoothing)` 可通过CONCENTRATED_WEIGHT
- **单窗口表达式**: `zscore(-ts_max(vec_max(field), 66))` 容易提交
- **多窗口组合**: `zscore(...22) + zscore(...66)` 分散权重

## 候选方向

1. **ts_mean smoothing variations** - 继续探索不同field和window组合
2. **cross-dataset组合** - mean_loan_rate + shrt3_bar 等
3. **等待模拟引擎恢复** - 当前无法进行新的回测

1. **多窗口组合** - 参考O0oJvZn1模式，创建更多多窗口表达式
2. **signed_power降相关性** - 模拟引擎恢复后可尝试
3. **analyst47** - 评级★的数据集，尚未充分探索

## 最佳Alpha (按类别)

### 纯s3 (s3_sector_decay — 16条)
| Alpha ID | 表达式 | Sharpe | 配置 |
|----------|--------|--------|------|
| N1nk8wLe | min_loan_rate w22 | **2.45** | truncation=0.05 |
| N1nkL69E | min_loan_rate w22 | 2.23 | SECTOR中性化 |
| akNXwAW9 | min_loan_rate w22 | 2.18 | decay=2 |
| A1nqeQWW | mean_loan_rate w22 | 2.07 | SECTOR中性化 |
| N1nW00Pe | max_loan_rate w5 | 1.98 | decay=8 |

### 跨数据集 (s3x — 9条)
| Alpha ID | 表达式 | Sharpe |
|----------|--------|--------|
| MPb9zdMo | min22 + close22 | 2.26 |
| 78xg2pa2 | mean22 + close22 | 2.11 |
| 0mAn6v7r | min22 + vol22 | 1.99 |
| XgkXMXp0 | max5 + close22 | 1.89 |

### 产品相关性测试 (spc — 多条)
| Alpha ID | 表达式 | Sharpe | 备注 |
|----------|--------|--------|------|
| e7neMpoN | signed_power(zscore(min22), 10) | 1.61 | fitness=6.89, ppc=0.016, turnover=0.125, **Concentrated Weight待修复** |
| P0njKg2J | min22 + CROWDING | 2.19 | |
| 1YoVY9WW | min22 + vec_avg(min) | 1.91 | turnover 0.23过高 |

## 提交检查状态

**已有成功提交的 Alpha** ✅

| Alpha ID | Sharpe | Prod Corr | Self Corr | CW | 状态 |
|----------|--------|-----------|-----------|-----|------|
| e7neMpoN | 1.61 | **0.682** ✅ | 0.347 | 0.99 ❌ | ⚠️ 待修复CW |

> 表达式: `signed_power(zscore(-ts_max(vec_max(min_loan_rate), 22)), 10)`
> 通过检查: Sharpe、Fitness、Turnover、Prod Corr、Self Corr、Sub-Universe、2Y Sharpe、Pyramid

## 已确认的结论

### 有效策略
- **truncation=0.05** → 比SECTOR中性化更有效提升Sharpe
- **close/volume 加法组合** → 保留信号 (EPS/lowvol无效)
- **CROWDING中性化** → 可行，min_loan_rate达2.19
- **decay=2~8** → 小幅提升，最佳值因字段而异

### 无效策略
- `rank()`包裹 → Sharpe暴跌 (2.18→0.65)
- `ts_rank()` → Sharpe 0.58 (全灭)
- `signed_power×0.3` → 破坏信号 (2.18→0.89)
- `ts_min+vec_min` → 方向反了 (Sharpe负)
- EPS作为附加信号 → 始终<1.0
- 外层zscore → 零增益

## 数据集状态

### shortinterest3 — ⚠️ 不提交（自相关性太高）
- 26个Alpha Sharpe≥1.58，但**自相关性(Self Corr)过高**
- 决定：不提交shortinterest3衍生Alpha，换方向探索新数据集

### 数据集探索结果
| 数据集 | 测试数 | 最佳Sharpe | 状态 |
|--------|--------|------------|------|
| **shortinterest3** | 26个可提交 | **2.53** | ⚠️ 不提交（自相关性高） |
| **earnings27** | 2个 | 0.24 | ❌ DEAD |
| **ai_equity_alpha** | 8个 | 运行中 | ⏳ |

## 最佳Alpha Top 5
1. **qMgEkAbj** — Sharpe 2.53 (shortinterest3) — 不提交
2. **O0oJvZn1** — Sharpe 2.50 (shortinterest3) — 不提交
3. **VkOdOMLb** — Sharpe 2.49 (shortinterest3) — 不提交
4. **xAeGmO8m** — Sharpe 2.48 (shortinterest3) — 不提交
5. **e7L6w5NO** — Sharpe 2.47 (shortinterest3) — 不提交

## 下一步任务

1. **等待 ai_equity_alpha 结果** — 探索新的VECTOR数据集
2. **探索其他数据集** — analyst4/10/14, mdl136, pv48 等

## API状态

- TOP3000 Universe正常
- VECTOR字段需 vec_min/vec_max 包裹
- 429限流存在，模拟轮询需要轮询等待
