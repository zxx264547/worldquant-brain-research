#!/usr/bin/env python3
"""
统一Alpha挖掘脚本 — 替代 sequential/infinite/massive_mining
支持持续顺序模式和批量并发模式

用法:
    # 顺序模式 (稳定)
    python unified_mining.py --mode sequential

    # 批量模式 (高速, 可能触发限流)
    python unified_mining.py --mode batch --batch-size 10

    # 单次模式 (测试)
    python unified_mining.py --mode once
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')

from scripts.core import RetryableBrainClient

RESULTS_FILE = Path("/tmp/multi_agent/unified_mining_results.json")

EPS_BASES = [
    ("eps_252_09", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3)"),
    ("eps_180_09", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 180), 0.9), 3)"),
    ("eps_350_09", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 350), 0.9), 3)"),
    ("eps_mom", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + ts_mean(returns, 66), 252), 1.05), 3)"),
    ("eps_div", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_dividend_value_quarterly, 252), 1.05), 3)"),
    ("eps_252_105", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)"),
]

TECHNICALS = [
    ("beta_120", "rank(ts_corr(returns, ts_mean(close, 120), 120))"),
    ("beta_252", "rank(ts_corr(returns, ts_mean(close, 252), 252))"),
    ("vol_120", "rank(-ts_std_dev(returns, 120))"),
    ("vol_252", "rank(-ts_std_dev(returns, 252))"),
    ("rsi_14", "rank(ts_mean(close / ts_mean(close, 14) - 1, 20))"),
    ("rsi_66", "rank(ts_mean(close / ts_mean(close, 66) - 1, 20))"),
    ("mom_60", "rank(ts_delta(close, 60))"),
    ("mom_120", "rank(ts_delta(close, 120))"),
    ("vol_trend", "rank(ts_mean(volume, 20) / ts_mean(volume, 120))"),
]

SETTINGS_BASE = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0,
    "truncation": 0.08,
    "neutralization": "NONE",
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": False
}

WEIGHTS = [0.15, 0.2, 0.25, 0.3]
COMBO_TYPES = ["mul", "add", "rank"]


def load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            data = json.load(f)
            return data.get('results', []), data.get('best'), data.get('counter', 0)
    return [], None, 0


def save_results(results, best, counter):
    with open(RESULTS_FILE, 'w') as f:
        json.dump({
            'results': results,
            'best': best,
            'counter': counter,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)


def build_candidate(base_name, base_expr, tech_name, tech_expr, weight, combo_type):
    if combo_type == "mul":
        expr = f"(({base_expr})) * (1 + (({tech_expr})) * {weight})"
        name = f"{base_name}_{tech_name}_mul{int(weight * 100)}"
    elif combo_type == "add":
        expr = f"(({base_expr})) + (({tech_expr})) * 0.5"
        name = f"{base_name}_{tech_name}_add"
    else:
        expr = f"rank((({base_expr}))) * 0.7 + rank(({tech_expr})) * 0.3"
        name = f"{base_name}_{tech_name}_rank"
    return name, expr


async def run_backtest(client, expr, name):
    settings = SETTINGS_BASE.copy()
    settings["description"] = f"uni_{name}"

    try:
        sim_result = await client.create_simulation_with_retry(expr, settings)
        if sim_result.get('status') == 'ERROR':
            return None

        alpha_id = sim_result.get('alpha_id')
        alpha_data = await client.get_alpha_with_retry(alpha_id)

        sharpe = alpha_data.get('sharpe', 0)
        return {
            "alpha_id": alpha_id,
            "expression": expr,
            "sharpe": sharpe,
            "fitness": alpha_data.get('fitness', 0),
            "ppc": alpha_data.get('ppc', 0),
            "margin": alpha_data.get('margin', 0),
            "turnover": alpha_data.get('turnover', 0),
            "name": name,
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return None


async def run_sequential(client):
    """顺序模式 — 一次一个, 稳定执行"""
    results, best, counter = load_results()
    tested_exprs = {r.get('expression', '')[:80] for r in results}
    best_sharpe = best.get('sharpe', 0) if best else 0

    print(f"已加载: {len(results)} 结果, 最佳Sharpe: {best_sharpe:.3f}")
    wait_count = 0
    start = time.time()

    while True:
        base_idx = counter % len(EPS_BASES)
        tech_idx = (counter // len(EPS_BASES)) % len(TECHNICALS)
        weight_idx = (counter // (len(EPS_BASES) * len(TECHNICALS))) % len(WEIGHTS)
        combo_idx = (counter // (len(EPS_BASES) * len(TECHNICALS) * len(WEIGHTS))) % len(COMBO_TYPES)

        base_name, base_expr = EPS_BASES[base_idx]
        tech_name, tech_expr = TECHNICALS[tech_idx]
        weight = WEIGHTS[weight_idx]
        combo = COMBO_TYPES[combo_idx]

        name, expr = build_candidate(base_name, base_expr, tech_name, tech_expr, weight, combo)

        if expr[:80] in tested_exprs:
            counter += 1
            continue

        print(f"[{counter}] {name}...", end=" ", flush=True)
        result = await run_backtest(client, expr, name)

        if result:
            sharpe = result['sharpe']
            print(f"Sharpe={sharpe:.3f} Fitness={result['fitness']:.3f}")
            results.append(result)
            tested_exprs.add(expr[:80])

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best = result
                print(f"  *** 新最佳! ***")
            if sharpe >= 1.58:
                print(f"  *** 可提交! alpha_id={result['alpha_id']} ***")

            save_results(results, best, counter)
            wait_count = 0
        else:
            print("失败")
            wait_count += 1
            await asyncio.sleep(60)
            if wait_count > 5:
                client._authenticated = False
                await client.authenticate_with_retry()
                wait_count = 0
            continue

        counter += 1
        if counter % 10 == 0:
            elapsed = time.time() - start
            rate = counter / elapsed * 60 if elapsed > 0 else 0
            print(f"\n--- 进度: {counter} | {rate:.1f}/min | 最佳: {best_sharpe:.3f} ---\n")

        await asyncio.sleep(3)


async def run_batch(client, batch_size=10):
    """批量模式 — 并发执行"""
    results, best, _ = load_results()
    tested_exprs = {r.get('expression', '')[:80] for r in results}
    best_sharpe = best.get('sharpe', 0) if best else 0

    print(f"批量大小: {batch_size}, 最佳Sharpe: {best_sharpe:.3f}")

    # 预生成所有候选
    all_candidates = []
    counter = 0
    for bi, (bname, bexpr) in enumerate(EPS_BASES):
        for ti, (tname, texpr) in enumerate(TECHNICALS):
            for w in WEIGHTS:
                for ct in COMBO_TYPES:
                    name, expr = build_candidate(bname, bexpr, tname, texpr, w, ct)
                    if expr[:80] not in tested_exprs:
                        all_candidates.append((counter, name, expr))
                        counter += 1

    print(f"待测试: {len(all_candidates)} 个候选")

    for offset in range(0, len(all_candidates), batch_size):
        batch = all_candidates[offset:offset + batch_size]
        tasks = [run_backtest(client, expr, name) for _, name, expr in batch]
        batch_results = await asyncio.gather(*tasks)

        for result in batch_results:
            if result:
                results.append(result)
                tested_exprs.add(result['expression'][:80])
                sharpe = result['sharpe']
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best = result
                    print(f"*** 新最佳! Sharpe={sharpe:.3f} ***")
                if sharpe >= 1.58:
                    print(f"*** 可提交! alpha_id={result['alpha_id']} ***")

        save_results(results, best, offset + len(batch))
        print(f"已测试: {min(offset + batch_size, len(all_candidates))}/{len(all_candidates)} | 最佳: {best_sharpe:.3f}")
        await asyncio.sleep(5)


async def run_once(client):
    """单次模式 — 测试一个当前候选"""
    results, best, counter = load_results()
    base_name, base_expr = EPS_BASES[counter % len(EPS_BASES)]
    tech_name, tech_expr = TECHNICALS[(counter // len(EPS_BASES)) % len(TECHNICALS)]
    weight = WEIGHTS[(counter // (len(EPS_BASES) * len(TECHNICALS))) % len(WEIGHTS)]
    combo = COMBO_TYPES[(counter // (len(EPS_BASES) * len(TECHNICALS) * len(WEIGHTS))) % len(COMBO_TYPES)]
    name, expr = build_candidate(base_name, base_expr, tech_name, tech_expr, weight, combo)

    print(f"测试: {name}")
    result = await run_backtest(client, expr, name)
    if result:
        print(f"Sharpe={result['sharpe']:.3f} Fitness={result['fitness']:.3f}")
        results.append(result)
        save_results(results, result, counter + 1)


async def main():
    parser = argparse.ArgumentParser(description='统一Alpha挖掘脚本')
    parser.add_argument('--mode', choices=['sequential', 'batch', 'once'],
                        default='sequential', help='运行模式')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='批量模式每批数量 (默认10)')
    args = parser.parse_args()

    print("=" * 60)
    print(f"统一Alpha挖掘 — 模式: {args.mode}")
    print("=" * 60)

    client = RetryableBrainClient()
    await client.authenticate_with_retry()
    print("API认证完成\n")

    if args.mode == 'sequential':
        await run_sequential(client)
    elif args.mode == 'batch':
        await run_batch(client, args.batch_size)
    else:
        await run_once(client)


if __name__ == "__main__":
    asyncio.run(main())