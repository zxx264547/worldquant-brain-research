# BRAIN 算子定义
**rank(x)**: 排名函数
**zscore(x)**: z-score标准化
**percentile(x)**: 百分位排名
**normalize(x)**: 归一化
**ts_mean(x, d)**: 时间序列均值,d为窗口
**ts_sum(x, d)**: 时间序列求和,d为窗口
**ts_delta(x, d)**: 时间序列差值,d为窗口
**ts_delay(x, d)**: 时间序列滞后,d为窗口
**ts_std_dev(x, d)**: 时间序列标准差,d为窗口
**ts_corr(x, y, d)**: 时间序列相关性,x和y为两个序列,d为窗口
**ts_covariance(x, y, d)**: 时间序列协方差,d为窗口
**ts_rank(x, d)**: 时间序列排名,d为窗口
**ts_arg_max(x, d)**: 时间序列最大值的索引,d为窗口
**ts_arg_min(x, d)**: 时间序列最小值的索引,d为窗口
**ts_max(x, d)**: 时间序列最大值,d为窗口
**ts_min(x, d)**: 时间序列最小值,d为窗口
**ts_median(x, d)**: 时间序列中位数,d为窗口
**ts_product(x, d)**: 时间序列乘积,d为窗口
**ts_skewness(x, d)**: 时间序列偏度,d为窗口
**ts_kurtosis(x, d)**: 时间序列峰度,d为窗口
**ts_backfill(x, d)**: 时间序列回填,d为天数上限
**ts_decay_linear(x, d)**: 线性衰减,d为窗口
**ts_decay_exp_window(x, d, factor = 1.0)**: 指数衰减窗口,d为窗口
**ts_target_tvr_decay(x, lambda_min, lambda_max = 0.0, target_tvr = 0.1)**: 目标tvr衰减
**group_neutralize(x, group)**: 按组中性化
**group_zscore(x, group)**: 按组z-score
**group_rank(x, group)**: 按组排名
**group_mean(x, group)**: 按组均值
**group_std_dev(x, group)**: 按组标准差
**signed_power(x, a)**: 有符号幂运算,a为指数
**log(x)**: 自然对数
**abs(x)**: 绝对值
**sqrt(x)**: 平方根
**sign(x)**: 符号函数
**inverse(x)**: 倒数
**power(x, a)**: 幂运算
**exp(x)**: 指数函数
**tanh(x)**: 双曲正切
**if_else(condition, x, y)**: 条件选择
**trade_when(condition, x, y)**: 条件交易
**filter(x, condition)**: 条件过滤
**purify(x)**: 纯化
**vec_avg(x)**: 向量平均
**vec_sum(x)**: 向量求和
**vec_min(x)**: 向量最小值
**vec_max(x)**: 向量最大值
**inst_tvr(x, d)**: 即时tvr,d为窗口
**days_from_last_change(x)**: 最近一次变化的天数
**hump(x, hump = 0.01)**: 驼峰函数
**decay_linear(x, d)**: 线性衰减
**delay(x, d)**: 延迟函数
**returns**: BRAIN内置returns字段
**close**: 收盘价
**volume**: 成交量
**open**: 开盘价
**amount**: 成交额
**industry**: 行业
**sector**: 板块
**subindustry**: 子行业
**market_cap**: 市值
**actual_eps_value_quarterly**: 实际EPS值(季度)
**actual_dividend_value_quarterly**: 实际股息值(季度)
**actual_cashflow_per_share_value_quarterly**: 实际每股现金流(季度)
**actual_sales_value_quarterly**: 实际销售额(季度)
**anl4_afv4_eps_mean**: 分析师EPS均值
**anl4_afv4_cfps_mean**: 分析师每股现金流均值
**anl4_afv4_div_mean**: 分析师股息均值
