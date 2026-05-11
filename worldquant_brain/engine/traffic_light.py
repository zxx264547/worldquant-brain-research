#!/usr/bin/env python3
"""信号灯系统 — 基于JR57542文章, 统计学方向导航

核心问题: 低Sharpe是"池塘没鱼"(数据没信号)还是"鱼饵不对"(表达式不对)?
通过统计分析一批回测结果, 给出方向性判断。
"""

import math
import random
from collections import Counter
from typing import Literal

Light = Literal["green", "yellow", "red", "dead"]

# ─── 6大算子族 ───
OPERATOR_FAMILIES = {
    "time_series": ["ts_mean", "ts_sum", "ts_delta", "ts_delay", "ts_decay_linear",
                    "ts_arg_max", "ts_rank", "ts_std_dev", "ts_corr",
                    "ts_backfill", "ts_avg", "signed_power"],
    "cross_section": ["group_neutralize", "group_zscore", "group_rank",
                      "group_mean", "industry", "sector", "subindustry"],
    "math_transform": ["log", "abs", "sqrt", "sign", "inverse", "power",
                       "signed_power", "exp", "tanh"],
    "conditional": ["if_else", "trade_when", "filter", "purify"],
    "ranking": ["rank", "zscore", "percentile", "decay_linear", "normalize"],
    "lag_shift": ["ts_delay", "ts_delta", "delay", "delta"],
}

def count_operator_families(expression: str) -> int:
    """统计表达式中使用的算子族数量"""
    found = set()
    expr_lower = expression.lower()
    for family, ops in OPERATOR_FAMILIES.items():
        for op in ops:
            if op.lower() in expr_lower:
                found.add(family)
                break
    return len(found)

# ─── 统计检验 ───

def t_test_one_sample(values: list[float], null_hypothesis: float = 1.0) -> dict:
    """单样本t检验, H0: 均值 = null_hypothesis"""
    n = len(values)
    if n < 2:
        return {"statistic": 0, "p_value": 1.0, "significant": False}
    mean = sum(values) / n
    sd = max((sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5, 1e-10)
    t = (mean - null_hypothesis) / (sd / math.sqrt(n))
    # 简化p值计算 (Welch-Satterthwaite近似)
    p = 2 * (1 - _t_cdf(abs(t), n - 1))
    return {"statistic": t, "p_value": p, "significant": p < 0.05, "mean": mean, "n": n}


def bootstrap_p_value(values: list[float], null_hypothesis: float = 1.0,
                      n_bootstrap: int = 9999) -> float:
    """Bootstrap BCa p值 (小样本用)"""
    n = len(values)
    if n < 2:
        return 1.0
    count = 0
    for _ in range(n_bootstrap):
        sample = [random.choice(values) for _ in range(n)]
        if sum(sample) / n >= null_hypothesis:
            count += 1
    return 1 - count / n_bootstrap


def bimodality_coefficient(values: list[float]) -> float:
    """双峰系数 BC = (skew^2 + 1) / (kurt + 3*(n-1)^2/((n-2)*(n-3)))
    BC > 0.556 提示双峰分布
    """
    n = len(values)
    if n < 4:
        return 0
    mean = sum(values) / n
    sd = max((sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5, 1e-10)
    skew = sum(((v - mean) / sd) ** 3 for v in values) / n
    kurt = sum(((v - mean) / sd) ** 4 for v in values) / n
    bc = (skew ** 2 + 1) / (kurt + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
    return bc


def _t_cdf(t: float, df: float) -> float:
    """t分布累积分布函数 (近似)"""
    if df <= 0:
        return 0.5
    x = df / (df + t * t)
    prob = 1 - 0.5 * _beta_inc(df / 2, 0.5, x)
    return prob


def _beta_inc(a: float, b: float, x: float) -> float:
    """不完全Beta函数 (简化近似)"""
    if x <= 0:
        return 0
    if x >= 1:
        return 1
    # Simpson法则数值积分
    n = 100
    h = x / n
    result = 0
    for i in range(n + 1):
        t_val = i * h
        if t_val > 0:
            term = (t_val ** (a - 1)) * ((1 - t_val) ** (b - 1))
        else:
            term = 0
        if i == 0 or i == n:
            result += term
        elif i % 2 == 0:
            result += 2 * term
        else:
            result += 4 * term
    result *= h / 3
    # 归一化因子 (粗略)
    from math import gamma
    return result * gamma(a + b) / (gamma(a) * gamma(b))


# ─── DSI 方向强度指数 ───

def compute_direction_strength_index(results: list[dict]) -> dict:
    """计算DSI方向强度指数"""
    n = len(results)
    if n == 0:
        return {"dsi": 0, "light": "red", "components": {}}

    sharpe_values = [r.get('sharpe', 0) for r in results]

    # S_ttest: t检验显著性得分
    if n >= 8:
        ttest = t_test_one_sample(sharpe_values, 0.5)
        s_ttest = max(0, min(1, 1 - ttest['p_value']))
    else:
        p = bootstrap_p_value(sharpe_values, 0.5, min(n * 500, 9999))
        s_ttest = max(0, min(1, 1 - p))

    # S_ceiling: 天花板高度得分
    best_sharpe = max(sharpe_values)
    s_ceiling = min(1, best_sharpe / 1.58)

    # S_passrate: PPA通过率
    ppa_pass = sum(1 for r in results
                   if r.get('ppc', 1) < 0.5
                   and r.get('fitness', 0) > 0.5
                   and r.get('margin', 0) > r.get('turnover', 0))
    s_passrate = ppa_pass / n

    # S_consist: 稳定性得分 (变异系数)
    mean_s = sum(sharpe_values) / n
    sd = max((sum((v - mean_s) ** 2 for v in sharpe_values) / (n - 1)) ** 0.5 if n > 1 else 0, 1e-10)
    cv = sd / abs(mean_s) if abs(mean_s) > 1e-10 else 10
    s_consist = 1 / (1 + cv)

    # DSI综合得分
    dsi = 0.30 * s_ttest + 0.25 * s_ceiling + 0.25 * s_passrate + 0.20 * s_consist

    # 算子多样性
    op_diversity_scores = []
    for r in results:
        expr = r.get('expression', '')
        if expr:
            op_diversity_scores.append(count_operator_families(expr))
    avg_op_diversity = sum(op_diversity_scores) / max(len(op_diversity_scores), 1)

    return {
        "dsi": dsi,
        "n": n,
        "mean_sharpe": mean_s,
        "best_sharpe": best_sharpe,
        "avg_op_diversity": avg_op_diversity,
        "bimodality": bimodality_coefficient(sharpe_values),
        "components": {
            "s_ttest": s_ttest, "s_ceiling": s_ceiling,
            "s_passrate": s_passrate, "s_consist": s_consist
        }
    }

# ─── 信号灯判定 ───

def evaluate_direction(results: list[dict]) -> dict:
    """评估方向: 返回信号灯 + 行动建议"""
    n = len(results)
    dsi_data = compute_direction_strength_index(results)
    dsi = dsi_data['dsi']
    best = dsi_data['best_sharpe']
    mean_s = dsi_data['mean_sharpe']
    bimodality = dsi_data['bimodality']
    op_div = dsi_data['avg_op_diversity']

    # 5条防误杀护栏
    # 1. 小样本保护
    if n < 5:
        return {"light": "yellow", "reason": "样本不足5个", "action": "继续回测至少5个", "dsi": dsi}

    # 2. 天花板保护
    if best >= 1.0:
        # 有一个好的就说明有潜力
        return {"light": "green", "reason": f"存在Sharpe={best:.2f}的Alpha, 方向有潜力",
                "action": "加大预算, 细化参数", "dsi": dsi}

    # 3. 双峰保护
    if bimodality > 0.556:
        return {"light": "yellow", "reason": "双峰分布: 存在高分子群体",
                "action": "提取高分子群体的共同特征", "dsi": dsi}

    # 4. 三重证据门槛(判DEAD)
    if n >= 10 and best < 0.5 and mean_s < 0:
        # 检查算子多样性
        if op_div >= 4:
            # 用了4种以上算子还不行 → 数据没鱼
            return {"light": "dead",
                    "reason": f"n={n}, best={best:.2f}, mean={mean_s:.2f}, 算子族={op_div}≥4: 数据可能无信号",
                    "action": "记录anti_pattern, 换数据字段", "dsi": dsi}
        else:
            return {"light": "red",
                    "reason": f"算子族仅{op_div:.0f}种, 可能鱼饵问题",
                    "action": "拓宽算子探索范围", "dsi": dsi}

    # DSI阈值判定
    if dsi >= 0.55:
        return {"light": "green", "reason": f"DSI={dsi:.2f}: 方向有统计显著信号",
                "action": "加码深挖", "dsi": dsi}
    elif dsi >= 0.35:
        return {"light": "yellow", "reason": f"DSI={dsi:.2f}: 有潜力但证据不足",
                "action": "谨慎继续1-2轮结构性变体", "dsi": dsi}
    elif dsi >= 0.15:
        return {"light": "red", "reason": f"DSI={dsi:.2f}: 信号弱",
                "action": "换字段组合或算子类型, 再做评估", "dsi": dsi}
    else:
        if op_div < 3:
            return {"light": "red", "reason": f"DSI={dsi:.2f}: 多样性不足",
                    "action": "拓宽算子范围再试", "dsi": dsi}
        return {"light": "dead", "reason": f"DSI={dsi:.2f}: 多方向无信号",
                "action": "记录anti_pattern, 及时止损", "dsi": dsi}


# ─── 工具函数 ───

def evaluate_from_db(conn, limit: int = 50) -> dict:
    """从数据库评估最新一批结果"""
    rows = conn.execute(
        "SELECT * FROM alphas WHERE status='done' "
        "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    results = [dict(r) for r in rows]
    return evaluate_direction(results)


def get_light_emoji(light: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴", "dead": "⚫"}.get(light, "❓")


# ─── 自测 ───

if __name__ == "__main__":
    print("=== 信号灯系统测试 ===\n")

    # 模拟数据: 有信号的方向
    good_results = [
        {"sharpe": 1.17, "fitness": 1.95, "ppc": 0.15, "margin": 0.053, "turnover": 0.013,
         "expression": "((ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3))) * (1 + ((rank(ts_corr(returns, ts_mean(close, 120), 120)))) * 0.2)"},
        {"sharpe": 1.15, "fitness": 1.89, "ppc": 0.11, "margin": 0.038, "turnover": 0.018,
         "expression": "eps * (1 + momentum_20 * 0.2)"},
        {"sharpe": 1.10, "fitness": 1.70, "ppc": 0.20, "margin": 0.08, "turnover": 0.010,
         "expression": "rank(eps) * 0.6 + rank(beta) * 0.4"},
        {"sharpe": 0.95, "fitness": 1.40, "ppc": 0.30, "margin": 0.07, "turnover": 0.012,
         "expression": "ts_mean(eps, 66) * 0.7 + ts_delta(close, 20) * 0.3"},
        {"sharpe": 0.88, "fitness": 1.19, "ppc": 0.55, "margin": 0.12, "turnover": 0.004,
         "expression": "((eps_base)) + ((rank(momentum)) * 0.5)"},
    ]
    # 模拟数据: 无信号的方向
    bad_results = [
        {"sharpe": 0.5, "fitness": 0.5, "ppc": 0.6, "margin": 0.02, "turnover": 0.03},
        {"sharpe": 0.3, "fitness": 0.3, "ppc": 0.7, "margin": -0.01, "turnover": 0.04},
        {"sharpe": -0.5, "fitness": -0.7, "ppc": 0.8, "margin": -0.05, "turnover": 0.05},
        {"sharpe": -1.0, "fitness": -1.5, "ppc": 0.9, "margin": -0.10, "turnover": 0.06},
        {"sharpe": -0.3, "fitness": -0.4, "ppc": 0.7, "margin": -0.03, "turnover": 0.04},
    ]

    print("【有信号方向】")
    result = evaluate_direction(good_results)
    print(f"  {get_light_emoji(result['light'])} {result['light'].upper()}")
    print(f"  理由: {result['reason']}")
    print(f"  行动: {result['action']}")
    print(f"  DSI: {result['dsi']:.3f}")
    print()

    print("【无信号方向】")
    result = evaluate_direction(bad_results)
    print(f"  {get_light_emoji(result['light'])} {result['light'].upper()}")
    print(f"  理由: {result['reason']}")
    print(f"  行动: {result['action']}")
    print(f"  DSI: {result['dsi']:.3f}")
    print()

    # 测试算子多样性
    print("=== 算子多样性测试 ===")
    eps_beta = "((ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3))) * (1 + ((rank(ts_corr(returns, ts_mean(close, 120), 120)))) * 0.2)"
    simple = "rank(ts_mean(close, 20))"
    complex_expr = "ts_rank(ts_delta(ts_mean(group_neutralize(log(abs(returns)), industry), 66), 22), 120)"

    for name, expr in [("EPS+Beta", eps_beta), ("简单rank", simple), ("复杂嵌套", complex_expr)]:
        print(f"  {name}: {count_operator_families(expr)} 个算子族")
