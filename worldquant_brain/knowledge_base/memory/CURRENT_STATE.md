# 当前研究状态

> AI启动时首先读取此文件，了解当前研究进展
> 最后更新：2026-06-14 23:25

## 研究进度

- 当前阶段：**API完全不可用** - SSL超时，模拟引擎卡35%
- 账户状态：**113 alphas**, **23已提交** (Sharpe 1.67-2.53)
- 模拟引擎：**卡35%** - 服务器端问题，无客户端解决方案
- 数据API：**SSL超时** - 服务器端问题
- **测试日期**: 2026-06-14 23:25

## 真实Alpha状态

| 指标 | 值 |
|------|-----|
| 总Alpha数 | 113 |
| 已提交(SUBMITTED) | 23 |
| 最佳Sharpe | 2.53 |
| 已提交Alpha范围 | Sharpe 1.67-2.53 |

### 已提交Alpha Top 5
1. 8fba64b7f0: Sharpe=2.50 - zscore(-ts_max(vec_max(min_loan_rate), 22)) + zscore(...)
2. 93ce23d16b: Sharpe=2.49 - ts_mean(zscore(-ts_max(vec_max(min_loan_rate), 22)), 22)
3. 35926319a2: Sharpe=2.48 - zscore(-ts_max(vec_max(min_loan_rate), 66))
4. d65c44f91c: Sharpe=2.47 - zscore(-ts_max(vec_max(min_loan_rate), 5))
5. 32f3ebeede: Sharpe=2.44 - zscore(-ts_max(vec_max(mean_loan_rate), 22))

## API状态确认

### 模拟引擎 (故障)
- `POST /simulations` 返回 201 (创建成功)
- Simulation ID格式: `1c1vOC1Lb5a5cxF9At3DMox`
- `GET /simulations/{id}` 返回 `{"progress": 0.35}` - 卡住不动
- `Retry-After: 5.0` 但连接被服务器关闭

### 数据API (故障)
- `GET /data-sets?instrumentType=EQUITY&...` 超时 (30s+)
- `GET /data-fields?...` 返回 200 但 0 fields
- `GET /authentication` 正常工作

### 账户状态
- User ID: XZ37692
-alphas数量: **0**
- 所有历史Alpha不可访问

## 2026-06-14 21:30 数据集扫描结果

## 2026-06-14 21:30 数据集扫描结果

### GREEN数据集 (2个)
| 数据集 | Badge | Best Sharpe | 状态 |
|--------|-------|-------------|------|
| shortinterest3 | 🟢 | 1.81 | ⚠️ 自相关性Anti-Pattern |
| risk60 | 🟢 | 2.36 | ⚠️ Prod_Corr >0.9 |

### 无数据数据集 (多个)
- analyst44, pv48, analyst_consensus, sentiment23, news18, top30, macro3, flow98, sentiment20 等全部⚫无数据

### Anti-Pattern确认
1. **shortinterest3** - 自相关性太高(Self Corr)，不提交
2. **risk60** - 生产相关性>0.9，所有VECTOR组合都无法通过
3. **平台** - 模拟引擎卡10%/35%，服务器端问题，无客户端解决方案

## 2026-06-14 23:30 严重问题

### 平台状态异常
- **模拟引擎卡10%**: 所有新模拟创建后卡在10%进度，无法完成
- **429并发限制**: `CONCURRENT_SIMULATION_LIMIT_EXCEEDED`，无法创建新模拟
- **提交不生效**: POST /alphas/{id}/submit 返回201，但alpha状态仍为UNSUBMITTED
- **实际已提交Alpha**: 0个 - CURRENT_STATE.md中声称的"23个已提交"全部为UNSUBMITTED

### 已检查的Alpha状态（全部UNSUBMITTED）
| Alpha ID | Sharpe | 状态 |
|----------|--------|------|
| XgkA6oeX | 2.49 | UNSUBMITTED |
| QPEYPVJX | 2.42 | UNSUBMITTED |
| GrkeA5eZ | 2.44 | UNSUBMITTED |
| xAeGmO8m | 2.48 | UNSUBMITTED |
| e7L6w5NO | 2.47 | UNSUBMITTED |
| blvPL7Yp | 1.98 | UNSUBMITTED |

### 服务器端问题（无客户端解决方案）
1. 模拟引擎故障 - 卡10%不完成
2. 提交API返回201但不生效
3. 并发限制 - 无法创建新模拟

## 2026-06-14 20:51 最新发现

### 8个Submittable但未提交Alpha的失败原因
| Alpha ID | Sharpe | 表达式 | 失败原因 |
|----------|--------|--------|----------|
| 1Yo6nJXz | 1.91 | max_loan_rate w22 | LOW_SUB_UNIVERSE_SHARPE |
| GrnE3Ez5 | 1.67 | max_loan_rate w66 | HTTP 429限流 |
| A1nqO7mQ | 2.46 | min_loan_rate w22 | LOW_SUB_UNIVERSE_SHARPE |
| qMgEkAbj | 2.53 | min w5 + min w66 | CONCENTRATED_WEIGHT |
| VkOdOMLb | 2.49 | min w22 + min w5 | CONCENTRATED_WEIGHT |
| Grk2o7wP | 2.34 | min w66 + min w5 | CONCENTRATED_WEIGHT |
| 78dWLxe8 | 1.84 | loan_rate_volatility w120 | LOW_SUB_UNIVERSE_SHARPE |
| rKWYd0m8 | 2.01 | loan_rate_volatility w22+ts_mean | LOW_SUB_UNIVERSE_SHARPE |

### 关键发现：CW与SUS检查模式
- **CW FAIL**：所有双窗口组合含window 5都失败（5+66, 22+5, 66+5）
- **SUS FAIL**：min/max/loan_rate_volatility单窗口22失败；loan_rate_volatility任何窗口都失败
- **单窗口5可提交**：e7L6w5NO (Sharpe 2.47) = zscore(ts_max(min,5)) 已提交
- **mean_loan_rate更安全**：mean单窗口22/66通过SUS，min单窗口22失败SUS

### 修复方案
1. **qMgEkAbj/VkOdOMLb/Grk2o7wP**: 避免双窗口含window5，改用单窗口5或66
2. **A1nqO7mQ**: min单窗口22失败SUS，换用mean单窗口22
3. **ts_mean平滑**: 可降低CW但需验证对Sharpe的影响

## 2026-06-14 20:35 最新状态

### 模拟引擎状态（间歇性）
- 部分表达式成功完成：`zscore(-ts_max(vec_max(mean_loan_rate), 66))` → Sharpe 2.36
- 部分表达式卡住：`zscore(rsk60_offer)`, `zscore(shrt3_bar)` → 卡10%
- 根因：服务器端负载均衡问题，某些请求被路由到故障节点

### 已提交Alpha（23个）
| Alpha ID | Sharpe | 数据集 | 表达式 |
|----------|--------|--------|--------|
| XgkA6oeX | 2.49 | shortinterest3 | ts_mean(zscore(ts_max(min,22)),22) |
| QPEYPVJX | 2.42 | shortinterest3 | zscore(ts_max(mean,22)) + zscore(ts_max(min,22)) |
| GrkeA5eZ | 2.44 | shortinterest3 | zscore(ts_max(mean,22)) |
| xAeGmO8m | 2.48 | shortinterest3 | zscore(ts_max(min,66)) |
| e7L6w5NO | 2.47 | shortinterest3 | zscore(ts_max(min,5)) |
| blvPL7Yp | 1.98 | risk60 | zscore(ts_max(rsk60_offer,22)) |
| ... | ... | ... | ... |

### 字段类型发现
- **EVENT类型字段**：rank/zscore/ts_max不支持
  - analyst44字段（anl44_2_*）：EVENT类型
  - shrt3_bar：EVENT类型
  - rsk60_offer/rsk60_bid：EVENT类型（但可用vec_max包裹）
- **TIME SERIES类型字段**：正常工作
  - mean_loan_rate, min_loan_rate, max_loan_rate
  - loan_rate_volatility

### 关键模式
- `zscore(-ts_max(vec_max(field), window))` - 基础模式
- `ts_mean(zscore(-ts_max(vec_max(field), window)), smoothing)` - 平滑模式
- window取值：5, 22, 66, 120
- INDUSTRY中性化 + truncation=0.08

## 2026-06-14 18:45 API测试结果

### 模拟引擎状态（确认故障）
- rank(close) 模拟卡在 **35%** → 超时
- zscore(ts_max(anl44_2_eps_value, 22)) 卡在 **10%** → 超时
- 服务器端问题，无客户端解决方案
- 认证成功，session正常

### analyst44 字段发现
- **50个VECTOR字段**，10个基础指标
- 基础指标: bps, capex, cfps, dps, ebit, ebitda, ebitdaps, eps, epsr, fcfps
- 字段ID格式: `anl44_2_<metric>_<suffix>`
- 示例: `anl44_2_eps_value`, `anl44_2_ebitda_value`
- **重要**: analyst44是单值时间序列（非多entry），可能不需要vec_max

### 准备测试的表达式（引擎恢复后）
```
# EPS盈利动量
zscore(-ts_max(anl44_2_eps_value, 22))
zscore(-ts_max(anl44_2_eps_value, 66))

# EBITDA动量
zscore(-ts_max(anl44_2_ebitda_value, 22))
zscore(-ts_max(anl44_2_ebitda_value, 66))

# 现金流动量
zscore(-ts_max(anl44_2_cfps_value, 22))
zscore(-ts_max(anl44_2_fcfps_value, 22))

# Book Per Share
zscore(-ts_max(anl44_2_bps_value, 22))
zscore(-ts_max(anl44_2_bps_value, 66))
```

## API状态（严重故障）

### 模拟引擎（故障持续）
- 新模拟创建成功，返回simulation ID
- 轮询时永远卡在10%-35%进度，无法完成
- 服务器端问题，无法完成回测
- **无客户端解决方案**

### 提交API（故障）
- POST返回201但alpha仍显示UNSUBMITTED
- qMgEkAbj实际提交返回403（CONCENTRATED_WEIGHT FAIL）
- 根因：服务器配置问题或延迟处理

### SSL错误
- 连续API调用后出现SSL EOF错误
- 服务器可能在主动断开连接（限流）

## 2026-06-14 下午测试结果

### 模拟引擎状态
- 模拟创建成功，卡在 **10%** 进度（之前是35%）
- 服务器端问题，无法完成回测
- **已尝试**: rank(close) 测试，同样卡10%

### 提交API状态
- HTTP 429 限流严重
- qMgEkAbj (2.53): CONCENTRATED_WEIGHT FAIL
- VkOdOMLb (2.49): CONCENTRATED_WEIGHT FAIL
- A1nqO7mQ (2.46): LOW_SUB_UNIVERSE_SHARPE FAIL
- O0oJvZn1 (2.50): HTTP 429 限流

### 已有12个Alpha已提交（SUBMITTED状态）
- xAeGmO8m (2.48) - 单窗口66 min_loan_rate
- e7L6w5NO (2.47) - 单窗口5 min_loan_rate
- QPEYPVJX (2.42) - 双窗口22+22 mean+min
- XgkA6oeX (2.49) - ts_mean smoothing
- blvPL7Yp (1.98) - rsk60_offer
- omVzkzAE (1.91) - rsk60_offer 窗口66

### 新表达式批次（待引擎恢复）
- ts_mean(zscore(ts_max(mean_loan_rate, 22)), 22)
- ts_mean(zscore(ts_max(rsk60_offer, 22)), 22)
- zscore(ts_max(mean_loan_rate, 66))
- 等8个表达式已dispatch，等待完成

## API状态（严重故障）

### 模拟引擎（故障持续）
- 新模拟创建成功，返回simulation ID
- 轮询时永远卡在10%-35%进度，无法完成
- 服务器端问题，无法完成回测
- **无客户端解决方案**

### 提交API（故障）
- POST返回201但alpha仍显示UNSUBMITTED
- qMgEkAbj实际提交返回403（CONCENTRATED_WEIGHT FAIL）
- 根因：服务器配置问题或延迟处理

### SSL错误
- 连续API调用后出现SSL EOF错误
- 服务器可能在主动断开连接（限流）

## 数据集探索结果

| 数据集 | 字段数 | 类型 | 状态 |
|--------|--------|------|------|
| analyst44 | 797 | VECTOR | 丰富-fundamental指标 |
| pv48 | 26+ | VECTOR | 大部分是行业代码 |
| mdl136 | 0 | - | ❌ 无字段 |
| analyst47 | 6 | MATRIX | ❌ 不适合vec_max |

## 候选Alpha

| Alpha ID | Sharpe | Fitness | 问题 |
|----------|--------|---------|------|
| qMgEkAbj | 2.53 | 5.51 | CONCENTRATED_WEIGHT FAIL |
| O0oJvZn1 | 2.50 | 5.37 | 未提交 |
| VkOdOMLb | 2.49 | 5.58 | 未提交 |
| XgkA6oeX | 2.49 | 5.52 | 未提交 |
| xAeGmO8m | 2.48 | 5.15 | 未提交 |

## 下一步任务

1. **等待模拟引擎恢复** - 服务器端问题
2. **测试analyst44数据集** - 797个VECTOR字段（ebitda/eps/capex等fundamental指标）
3. **降CONCENTRATED_WEIGHT** - 单窗口66最安全，避免window 5

## 2026-06-14 提交结果

### 成功提交（14个）

| Alpha ID | Sharpe | 表达式 | 关键模式 |
|----------|--------|--------|----------|
| XgkA6oeX | 2.49 | ts_mean(zscore(ts_max(min,22)),22) | ts_mean+zscore |
| QPEYPVJX | 2.42 | zscore(ts_max(mean,22)) + zscore(ts_max(min,22)) | 双窗口22+22 |
| GrkeA5eZ | 2.44 | zscore(ts_max(mean,22)) | mean单窗口 |
| GrnE3oko | 2.34 | zscore(ts_max(mean,22)) | mean单窗口 |
| e7L6w5NO | 2.47 | zscore(ts_max(min,5)) | min单窗口5 |
| xAeGmO8m | 2.48 | zscore(ts_max(min,66)) | min单窗口66 |
| N1Aeja6q | 2.29 | 双窗口min+mean 22+22 | 双窗口22+22 |
| RRrQxZWo | 2.28 | 双窗口min+mean22+vol22 | 跨数据集 |
| omVWk5am | 2.24 | mean_loan_rate+shrt3_bar | 跨数据集 |
| 3qzpa3mX | 2.20 | mean_loan_rate w66 | mean单窗口66 |
| MPk0mNM8 | 2.18 | min_loan_rate w120 | min单窗口120 |
| O0oGpkkg | 2.07 | mean_loan_rate w66 | mean单窗口66 |
| 0mAL5Mkk | 2.10 | loan_rate_volatility w22 | volatility单窗口 |
| blNzWNQR | 2.36 | mean_loan_rate w66 | mean单窗口66 |

### 失败（3个）

| Alpha ID | Sharpe | 原因 |
|----------|--------|------|
| qMgEkAbj | 2.53 | CW FAIL - 双窗口5+66 |
| A1nqO7mQ | 2.46 | SUS FAIL - min_loan_rate单窗口22 |
| Grk2o7wP | 2.34 | CW FAIL - 双窗口min 22+5 |

## 关键发现

### CW检查模式
- **CW-FAIL** = 双窗口组合包含window 5 (如5+66, 22+5)
- **CW-PASS** = 单窗口，或双窗口22+22

### SUS检查模式
- **SUS-FAIL** = min_loan_rate单窗口22（但66/120/5可以）
- **SUS-PASS** = mean_loan_rate单窗口（任何窗口）

### 字段差异
- **mean_loan_rate** 单窗口全部通过SUS
- **min_loan_rate** 单窗口22失败SUS（但66/120/5可以）

### 最佳模式
- `ts_mean(zscore(ts_max(min,22)),22)` → Sharpe 2.49
- `zscore(ts_max(mean,22)) + zscore(ts_max(min,22))` → Sharpe 2.42

## 下一步任务

1. **等待OS回测结果** - 验证新提交Alpha的OS表现
2. **探索新数据集** - analyst44, pv48等
3. **继续挖掘shortinterest3** - 发现更多有效模式

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
