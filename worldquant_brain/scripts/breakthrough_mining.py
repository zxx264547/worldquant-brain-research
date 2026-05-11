#!/usr/bin/env python3
"""突破EPS天花板 — 新方向挖掘
探索非EPS基础、多信号叠加、新表达式结构
"""

import asyncio
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')

from scripts.core import RetryableBrainClient

RESULTS_FILE = Path("/tmp/multi_agent/breakthrough_results.json")

# ═══ 非EPS基础Alpha ═══
NON_EPS_BASES = [
    ("cashflow", "ts_backfill(signed_power(ts_sum(actual_cashflow_per_share_value_quarterly, 252), 1.05), 3)"),
    ("dividend", "ts_backfill(signed_power(ts_sum(actual_dividend_value_quarterly, 252), 1.05), 3)"),
    ("sales", "ts_backfill(signed_power(ts_sum(actual_sales_value_quarterly, 252), 1.05), 3)"),
    ("eps_cf", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_cashflow_per_share_value_quarterly, 252), 1.05), 3)"),
    ("eps_div", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_dividend_value_quarterly, 252), 1.05), 3)"),
    ("eps_sales", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_sales_value_quarterly, 252), 1.05), 3)"),
    # 分析师预期
    ("analyst_eps", "ts_backfill(signed_power(ts_sum(rank(anl4_afv4_eps_mean), 252), 1.05), 3)"),
    ("analyst_cfps", "ts_backfill(signed_power(ts_sum(rank(anl4_afv4_cfps_mean), 252), 1.05), 3)"),
    # EPS + 价格交互
    ("eps_price", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly * rank(returns), 252), 1.05), 3)"),
]

# 最佳EPS基准 (已验证)
EPS_BASE = "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3)"

# 技术信号
TECH_SIGNALS = [
    ("beta_120", "rank(ts_corr(returns, ts_mean(close, 120), 120))"),
    ("beta_252", "rank(ts_corr(returns, ts_mean(close, 252), 252))"),
    ("vol_120", "rank(-ts_std_dev(returns, 120))"),
    ("vol_252", "rank(-ts_std_dev(returns, 252))"),
    ("rsi_14", "rank(ts_mean(close / ts_mean(close, 14) - 1, 20))"),
    ("mom_60", "rank(ts_delta(close, 60))"),
    ("mom_120", "rank(ts_delta(close, 120))"),
]

WEIGHTS = [0.15, 0.2, 0.25, 0.3]

SETTINGS_BASE = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1, "decay": 0,
    "truncation": 0.08,
    "neutralization": "NONE",
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": False
}


def load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            data = json.load(f)
            return data.get('results', []), data.get('best'), data.get('counter', 0)
    return [], None, 0


def save_results(results, best, counter):
    with open(RESULTS_FILE, 'w') as f:
        json.dump({
            'results': results, 'best': best, 'counter': counter,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)


def generate_candidates():
    """生成突破性候选"""
    idx = 0

    # 1. 非EPS基础 + 最佳技术信号 (乘法组合)
    for bname, bexpr in NON_EPS_BASES:
        for tname, texpr in TECH_SIGNALS[:4]:  # 只用Top 4技术信号
            for w in WEIGHTS:
                expr = f"(({bexpr})) * (1 + (({texpr})) * {w})"
                yield idx, f"neps_{bname}_x_{tname}_w{int(w*100)}", expr, {}
                idx += 1

    # 2. EPS + 多技术信号叠加 (乘法叠加)
    for i, (t1name, t1expr) in enumerate(TECH_SIGNALS[:5]):
        for (t2name, t2expr) in TECH_SIGNALS[i+1:i+3]:
            for w in [0.1, 0.15, 0.2]:
                expr = (f"(({EPS_BASE})) * (1 + (({t1expr})) * {w})"
                        f" * (1 + (({t2expr})) * {w})")
                yield idx, f"eps_multi_{t1name}_{t2name}_w{int(w*100)}", expr, {}
                idx += 1

    # 3. 不同signed_power指数
    for sp in [0.7, 0.8, 0.95, 1.0, 1.1]:
        base = f"ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), {sp}), 3)"
        for tname, texpr in TECH_SIGNALS[:4]:
            expr = f"(({base})) * (1 + (({texpr})) * 0.2)"
            yield idx, f"eps_sp{sp}_{tname}", expr, {}
            idx += 1

    # 4. 不同backfill天数
    for bf in [1, 5, 10, 15]:
        base = f"ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), {bf})"
        expr = f"(({base})) * (1 + (rank(ts_corr(returns, ts_mean(close, 120), 120))) * 0.2)"
        yield idx, f"eps_bf{bf}_beta120", expr, {}
        idx += 1

    # 5. 不同EPS窗口 (120/180/350/504)
    for window in [120, 180, 350, 504]:
        for sp in [0.9, 1.05]:
            base = f"ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, {window}), {sp}), 3)"
            expr = f"(({base})) * (1 + (rank(ts_corr(returns, ts_mean(close, 120), 120))) * 0.2)"
            yield idx, f"eps_win{window}_sp{sp}", expr, {}
            idx += 1

    # 6. 技术信号独立rank + EPS rank 组合
    for tname, texpr in TECH_SIGNALS[:5]:
        expr = (f"rank((({EPS_BASE}))) * 0.5 + "
                f"rank((({texpr}))) * 0.3 + "
                f"rank(delay(returns, 1)) * 0.2")
        yield idx, f"eps_rank_{tname}_delay", expr, {}
        idx += 1


async def run_backtest(client, expr, name, settings_mod=None):
    settings = SETTINGS_BASE.copy()
    settings["description"] = f"bt_{name}"
    if settings_mod:
        settings.update(settings_mod)

    try:
        sim = await client.create_simulation_with_retry(expr, settings)
        if sim.get('status') == 'ERROR':
            return None

        alpha_id = sim.get('alpha_id')
        alpha = await client.get_alpha_with_retry(alpha_id)

        sharpe = alpha.get('sharpe', 0)
        return {
            "alpha_id": alpha_id, "expression": expr,
            "sharpe": sharpe, "fitness": alpha.get('fitness', 0),
            "ppc": alpha.get('ppc', 0), "margin": alpha.get('margin', 0),
            "turnover": alpha.get('turnover', 0), "name": name,
            "status": "ok", "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


async def main():
    print("=" * 65)
    print("突破性Alpha挖掘 — 超越EPS天花板")
    print("=" * 65)

    client = RetryableBrainClient()
    await client.authenticate_with_retry()
    print("API认证完成\n")

    results, best, counter = load_results()
    tested_exprs = {r.get('expression', '')[:80] for r in results}
    best_sharpe = best.get('sharpe', 0) if best else 0

    print(f"已加载: {len(results)} 结果, 最佳: {best_sharpe:.3f}\n")

    candidates = list(generate_candidates())
    total = len(candidates)
    new_count = 0
    start = time.time()

    for i, (idx, name, expr, settings_mod) in enumerate(candidates):
        if expr[:80] in tested_exprs:
            continue

        print(f"[{new_count+1}/{total}] {name[:55]}...", end=" ", flush=True)
        result = await run_backtest(client, expr, name, settings_mod)

        if result:
            sharpe = result['sharpe']
            print(f"Sharpe={sharpe:.3f}")

            results.append(result)
            tested_exprs.add(expr[:80])

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best = result
                save_results(results, best, counter + new_count)
                print(f"  *** 新最佳! Sharpe={sharpe:.3f} ***")
            if sharpe >= 1.58:
                print(f"  *** 可提交! alpha_id={result['alpha_id']} ***")
        else:
            print("失败, 等待60秒")
            await asyncio.sleep(60)
            continue

        new_count += 1
        if new_count % 10 == 0:
            save_results(results, best, counter + new_count)

        await asyncio.sleep(2)

    # 最终保存
    save_results(results, best, counter + new_count)

    elapsed = time.time() - start
    print(f"\n{'='*65}")
    print(f"突破性挖掘完成: {new_count} 新测试")
    print(f"最佳Sharpe: {best_sharpe:.3f}")
    print(f"耗时: {elapsed/60:.1f} 分钟")

    if best_sharpe >= 1.58:
        print(f"\n*** 可提交Alpha已找到! ***")
        print(f"  {best['alpha_id']}: Sharpe={best_sharpe:.3f}")


if __name__ == "__main__":
    asyncio.run(main())