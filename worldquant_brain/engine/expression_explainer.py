#!/usr/bin/env python3
"""表达式解释器 — 将Alpha表达式翻译成人可读的描述"""

import re

# 字段中英文映射
FIELD_NAMES = {
    "actual_eps_value_quarterly": "实际EPS(季度)",
    "actual_dividend_value_quarterly": "实际股息(季度)",
    "actual_cashflow_per_share_value_quarterly": "每股现金流(季度)",
    "actual_sales_value_quarterly": "实际销售额(季度)",
    "anl4_afv4_eps_mean": "分析师EPS均值",
    "anl4_afv4_cfps_mean": "分析师CFPS均值",
    "anl4_afv4_div_mean": "分析师股息均值",
    "close": "收盘价", "open": "开盘价",
    "returns": "收益率", "volume": "成交量", "amount": "成交额",
}

# 算子中英文 (不含模板变量, 简洁描述)
OP_NAMES = {
    "rank": ("截面排名", "将所有股票按信号值排序,消除量纲差异"),
    "zscore": ("Z-score标准化", "使信号均值为0标准差为1"),
    "ts_mean": ("时间序列均值", "过去N个交易日取平均,平滑短期波动"),
    "ts_sum": ("时间序列求和", "过去N个交易日累计值"),
    "ts_delta": ("时间序列差值", "当前值与N天前的差值,衡量变化趋势"),
    "ts_delay": ("时间序列滞后", "取N天前的值,用于构建对比基准"),
    "ts_std_dev": ("时间序列标准差", "过去N日波动程度,衡量风险"),
    "ts_corr": ("时间序列相关性", "两个序列的皮尔逊相关系数,衡量联动程度"),
    "signed_power": ("有符号幂运算", "保留正负号的幂变换,增强信号区分度"),
    "ts_backfill": ("回填缺失值", "用最近的有效值填充缺失,保证数据连续"),
    "ts_decay_linear": ("线性衰减加权", "越近的数据权重越大"),
    "group_neutralize": ("按组中性化", "去除行业/板块的系统性偏差"),
    "trade_when": ("条件触发", "仅在满足条件时交易,减少噪音交易"),
}


def explain_expression(expr: str) -> dict:
    """解析表达式，返回结构化解释"""
    parts = _parse_parts(expr)
    return {
        "original": expr,
        "fields_used": parts["fields"],
        "operators_used": parts["operators"],
        "structure_type": parts["structure_type"],
        "summary_zh": parts["summary_zh"],
        "details": parts["details"],
    }


def _parse_parts(expr: str) -> dict:
    fields = []
    operators = []
    details = []

    # 提取字段
    for fname, fzh in FIELD_NAMES.items():
        if fname in expr:
            fields.append({"name": fname, "zh_name": fzh})

    # 提取算子
    op_matches = re.findall(r'([a-z_]+)\s*\(', expr)
    seen = set()
    for op in op_matches:
        if op in OP_NAMES and op not in seen:
            seen.add(op)
            zh_name, zh_desc = OP_NAMES[op]
            operators.append({"name": op, "zh_name": zh_name, "description": zh_desc})

    # 提取窗口
    windows = []
    for m in re.finditer(r'(?:ts_mean|ts_sum|ts_delta|ts_std_dev|ts_corr|ts_backfill|ts_decay_linear)\s*\([^,]*,\s*(\d+)', expr):
        w = int(m.group(1))
        if w not in windows:
            windows.append(w)
    for m in re.finditer(r'ts_corr\s*\([^,]*,\s*[^,]*,\s*(\d+)', expr):
        w = int(m.group(1))
        if w not in windows:
            windows.append(w)

    # 提取指数
    power_match = re.search(r'signed_power\s*\([^,]*,\s*([0-9.]+)', expr)
    power = float(power_match.group(1)) if power_match else None

    # 检测组合结构
    structure_type = "单信号"
    if " * (1 + " in expr or "* (1+(" in expr:
        structure_type = "乘法组合 (EPS × 技术信号)"
    elif " + " in expr and "rank(" in expr:
        structure_type = "加法组合"
    elif " - " in expr:
        structure_type = "减法组合"
    elif "*" in expr:
        structure_type = "乘积结构"

    # 生成中文摘要
    summary_parts = []
    field_zh = ", ".join(f["zh_name"] for f in fields[:3]) or "未知字段"
    summary_parts.append(f"使用数据: {field_zh}")

    op_zh = ", ".join(o["zh_name"] for o in operators[:4]) or "原始信号"
    summary_parts.append(f"核心算子: {op_zh}")

    if windows:
        summary_parts.append(f"关键窗口: {', '.join(str(w) for w in windows[:3])}日")
    if power:
        summary_parts.append(f"幂指数: {power}")
    summary_parts.append(f"结构类型: {structure_type}")

    return {
        "fields": fields,
        "operators": operators,
        "windows": windows,
        "power": power,
        "structure_type": structure_type,
        "summary_zh": " | ".join(summary_parts),
        "details": details,
    }


def analyze_result(result: dict) -> dict:
    """分析单个Alpha的回测结果"""
    sharpe = result.get('sharpe', 0)
    fitness = result.get('fitness', 0)
    ppc = result.get('ppc', 0)
    margin = result.get('margin', 0)
    turnover = result.get('turnover', 0)

    # PPA检查
    ppa = {
        "sharpe": {"value": sharpe, "threshold": 1.58, "pass": sharpe >= 1.58},
        "fitness": {"value": fitness, "threshold": 0.5, "pass": fitness > 0.5},
        "ppc": {"value": ppc, "threshold": 0.5, "pass": ppc < 0.5},
        "margin": {"value": margin, "threshold": turnover, "pass": margin > turnover},
    }
    ppa_pass = sum(1 for v in ppa.values() if v['pass'])

    # 评级
    if sharpe >= 1.58 and ppa_pass >= 4:
        grade, grade_zh = "A+", "可提交"
    elif sharpe >= 1.0:
        grade, grade_zh = "A", "有潜力"
    elif sharpe >= 0.5:
        grade, grade_zh = "B", "待优化"
    elif sharpe >= 0:
        grade, grade_zh = "C", "信号弱"
    else:
        grade, grade_zh = "D", "无效"

    # 问题诊断
    issues = []
    if ppc >= 0.5:
        issues.append("PPC过高, 建议rank()包裹或降低truncation")
    if fitness < 0.5:
        issues.append("Fitness低, 建议增加decay或换industry中性化")
    if turnover > 0.10:
        issues.append("换手率过高, 建议用trade_when或加大decay")
    if margin <= turnover:
        issues.append("Margin不抵Turnover, 盈利能力不足")

    # 优化建议
    suggestions = []
    if sharpe < 1.0:
        suggestions.append("尝试不同技术信号组合或换市场")
        suggestions.append("检查算子多样性是否>=3族")
    if 1.0 <= sharpe < 1.58:
        suggestions.append("接近可提交, 微调weight参数或试试多信号叠加")

    return {
        "grade": grade,
        "grade_zh": grade_zh,
        "ppa": {k: {"value": v["value"], "threshold": v["threshold"],
                     "pass": v["pass"]} for k, v in ppa.items()},
        "ppa_pass_count": ppa_pass,
        "issues": issues,
        "suggestions": suggestions,
    }
