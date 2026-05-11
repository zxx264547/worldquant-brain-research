# WorldQuant BRAIN 数据集目录

> AI研究Alpha时首先查阅此文件，了解可用数据集

## 数据集分类速查

### 分析师数据 (Analyst)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| analyst4 | Analyst Estimate Data for Equity | MATRIX/VECTOR | EPS等共识数据，**当前最佳Alpha来源** |
| analyst10 | Performance-Weighted Analyst Estimates | VECTOR | SmartEstimate加权预测 |
| analyst14 | Estimations of Key Fundamentals | VECTOR | 关键基本面预测(营收/EBITDA/EPS) |
| analyst16 | Real Time Estimates | VECTOR | 实时预测数据 |
| analyst27 | USA Analyst Estimate Daily Data | VECTOR | 美国分析师历史表现 |
| analyst44 | Integrated Broker Estimates | VECTOR | 整合券商预测(WQ SmartData) |
| analyst45 | Analyst Trade Ideas | VECTOR | 分析师交易建议 |
| analyst83 | Smart Conference call transcript | VECTOR | 财报电话会情感分析 |

### 基本面数据 (Fundamental)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| fundamental6 | Company Fundamental Data for Equity | MATRIX(48)/VECTOR(2) | 全球公司基本面数据 |
| fundamental1 | Management and Executive Data | VECTOR | 高管和董事会成员信息 |
| fundamental13 | Comprehensive Fundamentals Dataset | MATRIX | 资产负债表/利润表/现金流 |
| fundamental14 | Audit Analytics Directors Data | VECTOR | 董事和高管变动追踪 |
| fundamental72 | Comprehensive Fundamental Data | VECTOR | 综合基本面数据 |

### 模型数据 (Model)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| model109 | Fundamentals and Technical Indicators | VECTOR | 274个量化字段(技术/基本面) |
| model135 | Alternative technical factor models | VECTOR | 替代技术因子模型 |
| model136 | ETF Based Equity Factors | MATRIX | ETF衍生的股票因子 |
| model138 | Stock Selection from Accounting-based Factors | VECTOR | 会计因子PDI模型 |
| model216 | Country/Sector Risk Model | VECTOR | 国家/行业风险模型 |
| model243 | Country/Industry Rank | VECTOR | 国家/行业排名 |
| model354 | Group Fundamental Model | VECTOR | 群体基本面模型 |

### 新闻/情感数据 (News/Sentiment)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| news5 | News Article Sentiment | VECTOR | 新闻文章情感 |
| news23 | News Transaction Data | VECTOR | 新闻交易数据 |
| news31 | News Analytics | VECTOR | 新闻分析指标 |
| news38 | Long-form News Analysis | VECTOR | 长文本新闻分析 |
| news79 | Corporate News Sentiment | VECTOR | 企业新闻情感 |
| news94 | Price-moving News | VECTOR | 价格驱动新闻 |
| sentiment1 | Social Media Sentiment | VECTOR | 社交媒体情感 |
| earningscall_sentiment | Earnings Call Sentiment | VECTOR | 财报电话会情感 |

### 财报数据 (Earnings)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| earnings6 | International Findings Data | VECTOR | 国际企业事件(财报/分红) |
| earnings7 | Earnings Calendar North America | VECTOR | 北美财报日历 |
| earnings27 | Earnings Update Emails | VECTOR | 财报更新邮件 |
| earnings_risk | Earnings Event Risk Model | VECTOR | 财报事件风险模型 |

### 期权数据 (Option)
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| option3 | US Equity Options Data | VECTOR | 美国股票期权数据 |
| option23 | Options Market Analytics | VECTOR | 期权市场分析 |
| expected_move | Equity Expected Move | VECTOR | 股票预期波动 |

### 风控/其他
| ID | 名称 | 类型 | 说明 |
|----|------|------|------|
| forward_beta_risk | Forward Beta Risk Model | VECTOR(14)/MATRIX(14) | 前瞻贝塔风险 |
| risk60 | Risk Model Data | VECTOR | 风险模型数据 |
| order_book_imbalance | Order Book Imbalance | VECTOR | 订单簿不平衡 |

---

## 字段类型说明

### VECTOR类型
- **可用算子**: `vec_sum`, `vec_min`, `vec_max`, `vec_avg`, `vec_count`, `vec_rank`
- **不可用算子**: `ts_mean`, `ts_sum`, `ts_rank`, `rank`, `ts_delta` ⚠️
- **特点**: 通常是时间序列数组，如每日情感得分

### MATRIX类型
- **可用算子**: `ts_mean`, `ts_sum`, `ts_rank`, `rank`, `ts_delta`, `signed_power` 等全部
- **不可用算子**: 无
- **特点**: 通常是横截面数据，如EPS季度值
- **代表字段**: `actual_eps_value_quarterly` (analyst4)

---

## 按信号类型分类

### 盈利预测类 (推荐尝试)
- `analyst4` - EPS/营收/现金流预测 (已知有效)
- `analyst14` - 关键基本面预测
- `analyst16` - 实时预测
- `analyst27` - 美国分析师数据

### 技术/市场结构类
- `model136` - ETF流向
- `model135` - 技术因子模型
- `order_book_imbalance` - 订单簿不平衡

### 情感/新闻类
- `news5`, `news79` - 新闻情感
- `earningscall_sentiment` - 电话会情感
- `sentiment1` - 社交媒体情感

### 基本面类
- `fundamental6` - 公司财务数据
- `fundamental1` - 高管数据
- `model109` - 综合因子

---

## 数据集完整列表

### A开头
- `analyst10` - Performance-Weighted Analyst Estimates
- `analyst11` - ESG scores
- `analyst12` - Social Media Relation Dataset
- `analyst14` - Estimations of Key Fundamentals
- `analyst15` - Earnings forecasts
- `analyst16` - Real Time Estimates
- `analyst27` - USA Analyst Estimate Daily Data
- `analyst4` - Analyst Estimate Data for Equity ⭐
- `analyst44` - Integrated Broker Estimates
- `analyst45` - Analyst Trade Ideas
- `analyst47` - Alternative Analyst Investment Insight
- `analyst49` - Analyst Estimation Data
- `analyst55` - Earning Quality Analyst Estimates
- `analyst69` - Fundamental Analyst Estimates
- `analyst7` - Broker Estimates
- `analyst82` - Analyst estimate prediction data
- `analyst83` - Smart Conference call transcript data
- `analyst9` - Analyst Estimate Daily Data
- `analyst_chart_cnn` - Deep Learning Analyst Chart Signals

### B开头
- `biasfree_analyst` - Bias Adjusted Analyst Forecasts
- `board_network` - Board Member Network Analysis

### C开头
- `chart_model_alpha` - Deep Learning Chart Returns Predictor
- `chart_return_model` - Deep Learning Chart Return Prediction
- `cre_exposure_model` - Commercial Real Estate Exposure Model
- `creator_signal_perf` - Finance Creator Prediction Performance

### D开头
- `dl_volume_pred` - Deep Learning Volume Prediction

### E开头
- `earnings27` - Earnings Update Emails Data
- `earnings6` - International Findings Data
- `earnings7` - Horizon Earnings and Calendar North America
- `earnings_chart_dl` - Deep Learning Earnings Chart Predictions
- `earnings_risk` - Earnings Event Risk Model
- `earningscall_sentiment` - Multi Aspect Earnings Call Sentiment
- `equity_kpi_forecast` - US Equity KPI Forecasts
- `event_return_model` - Deep Learning Event Return Prediction
- `expected_move` - Equity Expected Move Metrics

### F开头
- `filing_sentiment` - Regulatory Filing Sentiment Analytics
- `forward_beta_risk` - Forward Beta Risk Prediction Model
- `fundamental1` - Management and Executive Data
- `fundamental110` - Press Release Data
- `fundamental13` - Comprehensive Fundamentals Dataset
- `fundamental14` - Audit Analytics Directors Data
- `fundamental17` - Direct Fundamental Data
- `fundamental2` - Report Footnotes
- `fundamental22` - Environmental and Social Governance Data
- `fundamental23` - Fundamental Point in Time Data
- `fundamental25` - Company Operating Metrics
- `fundamental28` - Global Fundamental Data
- `fundamental3` - Fundamentals Data for US Equities
- `fundamental31` - Additional Factor Model
- `fundamental38` - Energy Fundamental Data
- `fundamental6` - Company Fundamental Data for Equity
- `fundamental65` - Factor Ratios and its Rank Model
- `fundamental69` - Quarterly Fundamental Data
- `fundamental7` - Comprehensive Fundamentals Data
- `fundamental72` - Comprehensive Fundamental Data
- `fundamental85` - Fundamental Indicators
- `fundamental86` - Stock Reports Plus

### I开头
- `imbalance5` - Oil Price Resilience Scores
- `insiders3` - SEC Report Data
- `institutions18` - Ownership Model Data
- `institutions20` - Short Sale Volume Data
- `institutions6` - Institutions and Beneficial Stake Ownership
- `institutions8` - Insider Model Data

### M开头
- `macro63` - Index Reconstitution Data
- `mfm_model_output` - Multi Factor Model Universal Output
- `model109` - Fundamentals and Technical Indicators Model ⭐
- `model127` - Corporate Patent Innovation Activity Dataset
- `model133` - Risk Parity Method Model
- `model135` - Alternative technical factor models
- `model136` - ETF Based Equity Factors
- `model138` - Stock Selection from Accounting-based Factors
- `model140` - Sensitivity to the Inflation Change
- `model144` - Stock Selection DL model
- `model16` - Fundamental Scores
- `model162` - Return prediction from conference call
- `model163` - [其他模型数据集...]
- `model216` - Country/Sector Risk Model
- `model243` - Country/Industry Rank
- `model244` - Transaction Signal Model
- `model30` - [其他模型...]
- `model307` - [其他模型...]
- `model354` - Group Fundamental Model
- `model46` - Average Recommendation Revision Model
- `model68` - [其他模型...]
- `model77` - [其他模型...]

### N开头
- `news12` - News Article Data
- `news17`, `news18`, `news19`, `news21`, `news23` - 各类新闻数据
- `news31` - News Analytics
- `news36`, `news38` - 新闻分析
- `news5` - News Article Sentiment
- `news46`, `news48`, `news50` - 新闻数据
- `news52`, `news54`, `news59` - 新闻数据
- `news66`, `news7` - 新闻数据
- `news73`, `news76`, `news79` - 新闻情感
- `news84`, `news85` - 新闻情感
- `news87`, `news94` - 新闻数据
- `news97` - News Transformer Scores
- `news_transformer_scores` - NLP News Scores
- `nlp_news_scores` - NLP News Scores

### O开头
- `option3` - US Equity Options Data
- `option23` - Options Market Analytics
- `option4`, `option6`, `option8`, `option9` - 其他期权数据
- `option40` - [期权数据集...]
- `option_horizon_decomp` - Options Horizon Decomposition
- `order_book_imbalance` - Order Book Imbalance
- `order_flow_imb` - Order Flow Imbalance
- `other128`, `other131` - [其他数据集...]
- `other250`, `other296`, `other315` - [其他...]
- `other327`, `other335`, `other359` - [其他...]
- `other384` - [其他...]
- `other407`, `other424`, `other432` - [其他...]
- `other434`, `other436`, `other455` - [其他...]
- `other460`, `other545`, `other546` - [其他...]
- `other551`, `other553`, `other566` - [其他...]
- `other567` - [其他...]
- `other571`, `other580`, `other596` - [其他...]
- `other623`, `other635`, `other685` - [其他...]
- `other699`, `other83` - [其他...]

### P开头
- `pv1` - [价格/价值数据集...]
- `pv103`, `pv104`, `pv106` - [价格数据...]
- `pv109` - [价格数据...]
- `pv13` - [价格数据...]
- `pv141` - [价格数据...]
- `pv17`, `pv173` - [价格数据...]
- `pv20`, `pv29`, `pv30` - [价格数据...]
- `pv47` - [价格数据...]
- `pv48` - [价格数据...]
- `pv52` - [价格数据...]
- `pv63`, `pv64`, `pv68` - [价格数据...]
- `pv87` - [价格数据...]
- `pv_tech_indicators` - Price Volume Technical Indicators

### R开头
- `risk60` - Risk Model Data
- `risk62`, `risk65`, `risk70`, `risk72` - [风险数据...]

### S开头
- `search_interest` - Search Interest Data
- `sentiment1` - Social Media Sentiment
- `sentiment18`, `sentiment21`, `sentiment22` - [情感数据...]
- `sentiment23`, `sentiment26`, `sentiment27` - [情感数据...]
- `sentiment7` - [情感数据...]
- `short_interest_pred` - Short Interest Prediction
- `shortinterest2`, `shortinterest3` - [做空数据...]
- `shortinterest10`, `shortinterest24`, `shortinterest29` - [做空数据...]
- `shortinterest36`, `shortinterest43` - [做空数据...]
- `social_sent_score` - Social Sentiment Score
- `socialmedia12` - Social Media Data
- `socialmedia8` - Social Media Data
- `stock_cluster_dl` - Deep Learning Stock Clustering
- `stock_search_trends` - Stock Search Trends

### T开头
- `tech_chart_model` - Technical Chart Model
- `techindi_model` - Technical Indicators Model
- `twitter_sentiment_l2` - Twitter Sentiment

### U开头
- `univ1`, `univ2` - [通用数据集...]
- `us_equity_news` - US Equity News

---

*最后更新：2026-05-03*