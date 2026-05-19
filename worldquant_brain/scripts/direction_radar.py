#!/usr/bin/env python3
"""
信号灯系统 — 帖子#2009 JR57542 方法论
判断回测批次方向: 继续深挖 vs 止损

四盏灯: 🟢 GREEN 🟡 YELLOW 🔴 RED ⚫ DEAD

用法: python direction_radar.py <results.json> [--verbose]
"""

import json, math, sys
from collections import Counter

OPERATOR_FAMILIES = {
    "time_series": ["ts_mean","ts_sum","ts_delta","ts_decay_linear","ts_std_dev","ts_backfill","ts_av_diff","ts_arg_max","ts_arg_min","ts_quantile"],
    "cross_section": ["group_zscore","group_rank","group_backfill","group_neutralize","group_cartesian_product","group_min","group_max"],
    "math_transform": ["signed_power","power","log","abs","sign","winsorize"],
    "conditional": ["if_else","trade_when"],
    "ranking": ["rank","zscore","percentile","ts_rank"],
    "lag_shift": ["ts_delay","ts_delta"],
}

def analyze_batch(results):
    expressions = [r.get("expression","") for r in results if r.get("status")=="ok"]
    sharpe_values = [r.get("sharpe",0) for r in results if r.get("status")=="ok"]
    if not sharpe_values:
        return {"light":"⚫ DEAD","reason":"无有效结果","score":0}

    n = len(sharpe_values)
    mean_s = sum(sharpe_values)/n
    ceiling = max(sharpe_values)
    sub_count = sum(1 for s in sharpe_values if s>=1.58)

    # Stability
    variance = sum((s-mean_s)**2 for s in sharpe_values)/(n-1) if n>1 else 0
    cv = math.sqrt(variance)/abs(mean_s) if abs(mean_s)>1e-10 else 999

    # Operator diversity
    used_families = set()
    for expr in expressions:
        for family, ops in OPERATOR_FAMILIES.items():
            for op in ops:
                if op in expr.lower():
                    used_families.add(family)
                    break
    diversity = len(used_families)

    score = 0.0
    reasons = []

    if mean_s > 0.5: score += 0.35
    else: reasons.append("信号不显著")

    if ceiling >= 2.0: score += 0.25
    elif ceiling >= 1.58: score += 0.18
    elif ceiling >= 1.0: score += 0.10; reasons.append(f"天花板低({ceiling:.2f})")
    else: reasons.append("天花板过低")

    if sub_count > 0: score += 0.15 * (sub_count/n)
    else: reasons.append("无候选通过1.58")

    if cv < 1.0: score += 0.15
    else: score += 0.05; reasons.append("结果不稳定")

    if diversity >= 4: score += 0.10
    elif diversity >= 2: score += 0.05; reasons.append(f"算子族不足({diversity}/6)")
    else: reasons.append(f"算子单一({diversity}/6)，鱼饵问题")

    if score >= 0.70: light, action = "🟢 GREEN", "加大预算，细化参数"
    elif score >= 0.45: light, action = "🟡 YELLOW", "谨慎继续1-2轮"
    elif score >= 0.25: light, action = "🔴 RED", "结构性改动再评估"
    else: light, action = "⚫ DEAD", "换方向"

    return {
        "light": light, "action": action, "score": round(score,3),
        "reasons": reasons,
        "batch_size": n, "sharpe_mean": round(mean_s,3),
        "sharpe_range": [round(min(sharpe_values),3), round(ceiling,3)],
        "submittable_count": sub_count,
        "operator_diversity": f"{diversity}/6 families",
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    with open(sys.argv[1]) as f:
        data = json.load(f)
    if isinstance(data, dict): data = [data]
    r = analyze_batch(data)
    verbose = "--verbose" in sys.argv
    print(f"\n{r['light']} Score={r['score']} | {r['action']}")
    print(f"Batch: {r['batch_size']} results, Sharpe [{r['sharpe_range'][0]}, {r['sharpe_range'][1]}], mean={r['sharpe_mean']}")
    print(f"Submittable: {r['submittable_count']} | Diversity: {r['operator_diversity']}")
    if verbose and r['reasons']:
        for reason in r['reasons']: print(f"  - {reason}")
