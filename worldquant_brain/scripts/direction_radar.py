#!/usr/bin/env python3
"""
信号灯系统 (Direction Radar) — 基于帖子#2009 JR57542 的方法论
判断回测批次的方向性：继续深挖 vs 及时止损

四盏灯:
  🟢 GREEN  — 方向有统计显著的信号 → 加大回测预算
  🟡 YELLOW — 有潜力但证据不足 → 谨慎继续 1-2 轮
  🔴 RED    — 当前批次信号弱 → 结构性改动再评估
  ⚫ DEAD   — 高置信度死路 → 记录 anti_pattern，换方向

核心指标:
  1. 信号显著性 (t-test) — 权重最高
  2. 天花板高度 — 最佳个体的 Sharpe
  3. 提交通过率 — Wilson Score 置信区间
  4. 稳定性 — Sharpe 离散程度
  5. 算子多样性分数 — 6大族覆盖度
"""

import json, math, os
from collections import Counter
from pathlib import Path
from typing import List, Dict, Tuple


# 6大算子族
OPERATOR_FAMILIES = {
    "time_series": ["ts_mean", "ts_sum", "ts_delta", "ts_decay_linear", "ts_std_dev",
                    "ts_backfill", "ts_av_diff", "ts_arg_max", "ts_arg_min", "ts_quantile"],
    "cross_section": ["group_zscore", "group_rank", "group_backfill", "group_neutralize",
                      "group_cartesian_product", "group_min", "group_max"],
    "math_transform": ["signed_power", "power", "log", "abs", "sign", "winsorize"],
    "conditional": ["if_else", "trade_when"],
    "ranking": ["rank", "zscore", "percentile", "ts_rank"],
    "lag_shift": ["ts_delay", "ts_delta"],
}


def _classify_operators(expressions: List[str]) -> Dict:
    """分析一批表达式的算子族覆盖度"""
    used_families = set()
    family_counts = Counter()

    for expr in expressions:
        for family, ops in OPERATOR_FAMILIES.items():
            for op in ops:
                if op in expr:
                    used_families.add(family)
                    family_counts[family] += 1
                    break

    return {
        "families_used": len(used_families),
        "family_names": list(used_families),
        "family_counts": dict(family_counts),
        "diversity_score": len(used_families) / 6.0
    }


def _calc_signal_significance(sharpe_values: List[float]) -> Dict:
    """t-test: 这批 Sharpe 均值是否显著高于噪声线 (0.0)"""
    n = len(sharpe_values)
    if n < 3:
        return {"p_value": 1.0, "significant": False, "reason": "样本太少 (<3)"}

    mean = sum(sharpe_values) / n
    if n == 1:
        return {"p_value": 1.0, "significant": False}

    variance = sum((x - mean) ** 2 for x in sharpe_values) / (n - 1)
    std_err = math.sqrt(variance / n) if variance > 0 else 1e-10

    if std_err < 1e-10:
        t_stat = 0
    else:
        t_stat = mean / std_err

    # Simplified p-value approximation (one-tailed)
    p_value = 1.0
    if t_stat > 0:
        p_value = math.exp(-t_stat)  # rough approximation

    return {
        "mean": round(mean, 3),
        "t_statistic": round(t_stat, 3),
        "p_value": round(p_value, 4),
        "significant": p_value < 0.1,
        "sample_size": n
    }


def _calc_ceiling(sharpe_values: List[float]) -> Dict:
    """天花板高度 — 最佳个体表现"""
    if not sharpe_values:
        return {"max": 0, "top3_avg": 0}

    sorted_s = sorted(sharpe_values, reverse=True)
    top3 = sorted_s[:3]
    return {
        "max": round(sorted_s[0], 3),
        "top3_avg": round(sum(top3) / len(top3), 3),
        "above_1_58": sum(1 for s in sharpe_values if s >= 1.58),
        "above_1_0": sum(1 for s in sharpe_values if s >= 1.0),
    }


def _calc_pass_rate(results: List[Dict]) -> Dict:
    """提交通过率 — Wilson Score 置信区间"""
    n = len(results)
    if n == 0:
        return {"pass_rate": 0, "wilson_lower": 0}

    passes = sum(1 for r in results if r.get("sharpe", 0) >= 1.58)
    p = passes / n
    z = 1.96  # 95% confidence

    denominator = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)

    wilson_lower = max(0, (center - margin) / denominator)
    wilson_upper = min(1, (center + margin) / denominator)

    return {
        "pass_count": passes,
        "total": n,
        "pass_rate": round(p, 3),
        "wilson_ci": [round(wilson_lower, 3), round(wilson_upper, 3)]
    }


def _calc_stability(sharpe_values: List[float]) -> Dict:
    """稳定性 — Sharpe 离散程度"""
    n = len(sharpe_values)
    if n < 2:
        return {"std": 0, "cv": 0, "stable": False}

    mean = sum(sharpe_values) / n
    variance = sum((x - mean) ** 2 for x in sharpe_values) / (n - 1)
    std = math.sqrt(variance)
    cv = std / abs(mean) if abs(mean) > 1e-10 else 999

    return {
        "std": round(std, 3),
        "cv": round(cv, 3),  # coefficient of variation
        "stable": cv < 1.0  # CV < 1 means relatively stable
    }


def analyze_batch(results: List[Dict], expressions: List[str] = None) -> Dict:
    """
    分析一批回测结果，返回信号灯判定

    Args:
        results: 回测结果列表 (每个需有 'sharpe' 字段)
        expressions: 对应的表达式列表 (用于算子多样性分析)
    """
    if not results:
        return {"light": "⚫ DEAD", "reason": "无结果"}

    sharpe_values = [r.get("sharpe", 0) for r in results if r.get("sharpe") is not None]
    if not sharpe_values:
        return {"light": "⚫ DEAD", "reason": "无有效 Sharpe"}

    # 1. 信号显著性
    sig = _calc_signal_significance(sharpe_values)

    # 2. 天花板高度
    ceiling = _calc_ceiling(sharpe_values)

    # 3. 提交通过率
    pass_rate = _calc_pass_rate(results)

    # 4. 稳定性
    stability = _calc_stability(sharpe_values)

    # 5. 算子多样性
    diversity = _classify_operators(expressions or [])

    # === 综合评分 ===
    score = 0.0
    reasons = []

    # 信号显著性 (权重 35%)
    if sig["significant"] and sig["mean"] > 0.5:
        score += 0.35
    elif sig["mean"] > 0.3:
        score += 0.20
        reasons.append("信号偏弱但存在")
    else:
        reasons.append("信号不显著")

    # 天花板高度 (权重 25%)
    if ceiling["max"] >= 2.0:
        score += 0.25
    elif ceiling["max"] >= 1.58:
        score += 0.18
        reasons.append(f"天花板中等 ({ceiling['max']})")
    elif ceiling["max"] >= 1.0:
        score += 0.10
        reasons.append(f"天花板较低 ({ceiling['max']})")
    else:
        reasons.append("天花板过低")

    # 通过率 (权重 15%)
    if pass_rate["pass_count"] > 0:
        score += 0.15 * (pass_rate["pass_count"] / pass_rate["total"])
    else:
        reasons.append("无候选通过 1.58")

    # 稳定性 (权重 15%)
    if stability["stable"]:
        score += 0.15
    else:
        score += 0.05
        reasons.append("结果不稳定")

    # 算子多样性 (权重 10%)
    if diversity["families_used"] >= 4:
        score += 0.10
    elif diversity["families_used"] >= 2:
        score += 0.05
        reasons.append(f"算子族不足 ({diversity['families_used']}/6)，如果还要继续需拓宽算子类型")
    else:
        reasons.append(f"算子单一 ({diversity['families_used']}/6)，鱼饵问题可能大于池塘问题")

    # === 判定 ===
    if score >= 0.70:
        light = "🟢 GREEN"
        action = "加大回测预算，细化参数"
    elif score >= 0.45:
        light = "🟡 YELLOW"
        action = "谨慎继续，再跑 1-2 轮结构变体"
    elif score >= 0.25:
        light = "🔴 RED"
        action = "做一次结构性改动（换字段组合/换算子类型）再评估"
    else:
        light = "⚫ DEAD"
        action = "记录 anti_pattern，换方向"

    return {
        "light": light,
        "action": action,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "signal_significance": sig,
            "ceiling": ceiling,
            "pass_rate": pass_rate,
            "stability": stability,
            "operator_diversity": diversity,
        },
        "batch_size": len(results),
        "sharpe_range": [round(min(sharpe_values), 3), round(max(sharpe_values), 3)],
        "sharpe_mean": round(sum(sharpe_values) / len(sharpe_values), 3),
    }


def analyze_json_file(filepath: str) -> Dict:
    """直接从 JSON 回测结果文件分析"""
    with open(filepath) as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    expressions = [r.get("expression", "") for r in data]
    return analyze_batch(data, expressions)


# ===== CLI =====
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("信号灯系统 — 判断回测批次的方向性")
        print("用法:")
        print("  python direction_radar.py <results.json>")
        print("  python direction_radar.py <results.json> --verbose")
        sys.exit(0)

    filepath = sys.argv[1]
    verbose = "--verbose" in sys.argv

    result = analyze_json_file(filepath)

    print(f"\n{'='*50}")
    print(f"  {result['light']}  Score: {result['score']}")
    print(f"  Action: {result['action']}")
    print(f"  Batch: {result['batch_size']} results, "
          f"Sharpe [{result['sharpe_range'][0]}, {result['sharpe_range'][1]}], "
          f"mean={result['sharpe_mean']}")
    if result['reasons']:
        print(f"\n  Reasons:")
        for r in result['reasons']:
            print(f"    - {r}")

    if verbose:
        d = result['details']
        print(f"\n  Details:")
        print(f"    Signal: t={d['signal_significance']['t_statistic']}, "
              f"p={d['signal_significance']['p_value']}, "
              f"significant={d['signal_significance']['significant']}")
        print(f"    Ceiling: max={d['ceiling']['max']}, "
              f"top3={d['ceiling']['top3_avg']}, "
              f">=1.58: {d['ceiling']['above_1_58']}")
        print(f"    Pass: {d['pass_rate']['pass_count']}/{d['pass_rate']['total']} "
              f"({d['pass_rate']['pass_rate']}), "
              f"Wilson [{d['pass_rate']['wilson_ci'][0]}, {d['pass_rate']['wilson_ci'][1]}]")
        print(f"    Stability: std={d['stability']['std']}, cv={d['stability']['cv']}, "
              f"stable={d['stability']['stable']}")
        od = d['operator_diversity']
        print(f"    Diversity: {od['families_used']}/6 families, score={od['diversity_score']}")
        if od.get('family_names'):
            print(f"      Used: {', '.join(od['family_names'])}")
