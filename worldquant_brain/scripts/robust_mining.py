#!/usr/bin/env python3
"""稳健Alpha挖掘 — 自动处理认证过期，永不卡死"""
import asyncio, sys, json, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')
from scripts.core import RetryableBrainClient

RESULTS_FILE = Path("/tmp/multi_agent/robust_mining_results.json")

# ─── 候选生成 ───
EPS = "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3)"

TECHS = [
    ("beta_120", "rank(ts_corr(returns, ts_mean(close, 120), 120))"),
    ("beta_252", "rank(ts_corr(returns, ts_mean(close, 252), 252))"),
    ("vol_120", "rank(-ts_std_dev(returns, 120))"),
    ("vol_252", "rank(-ts_std_dev(returns, 252))"),
    ("rsi_14", "rank(ts_mean(close / ts_mean(close, 14) - 1, 20))"),
    ("mom_60", "rank(ts_delta(close, 60))"),
    ("mom_120", "rank(ts_delta(close, 120))"),
]

NON_EPS = [
    ("eps_div", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_dividend_value_quarterly, 252), 1.05), 3)"),
    ("eps_cf", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + actual_cashflow_per_share_value_quarterly, 252), 1.05), 3)"),
    ("eps_price", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly * rank(returns), 252), 1.05), 3)"),
    ("eps_mom", "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly + ts_mean(returns, 66), 252), 1.05), 3)"),
    ("dividend", "ts_backfill(signed_power(ts_sum(actual_dividend_value_quarterly, 252), 1.05), 3)"),
]

SETTINGS = {"instrumentType":"EQUITY","region":"USA","universe":"TOP3000",
            "delay":1,"decay":0,"truncation":0.08,"neutralization":"NONE",
            "pasteurization":"ON","unitHandling":"VERIFY","nanHandling":"OFF",
            "language":"FASTEXPR","visualization":False}

def load():
    if RESULTS_FILE.exists():
        d = json.loads(RESULTS_FILE.read_text())
        return d.get('results',[]), d.get('best'), d.get('counter',0)
    return [], None, 0

def save(results, best, counter):
    RESULTS_FILE.write_text(json.dumps({
        'results': results, 'best': best, 'counter': counter,
        'timestamp': datetime.now().isoformat()}, indent=2))

def gen():
    idx = 0
    # 非EPS + tech
    for bn, be in NON_EPS:
        for tn, te in TECHS[:5]:
            for w in [0.15, 0.2, 0.25, 0.3]:
                yield idx, f"{bn}_{tn}_w{int(w*100)}", f"(({be})) * (1 + (({te})) * {w})"
                idx += 1
    # 多信号叠加
    for i in range(4):
        for j in range(i+1, 5):
            t1n, t1e = TECHS[i]
            t2n, t2e = TECHS[j]
            for w in [0.1, 0.15]:
                yield idx, f"eps_mul2_{t1n}_{t2n}_w{int(w*100)}", f"(({EPS})) * (1 + (({t1e})) * {w}) * (1 + (({t2e})) * {w})"
                idx += 1

async def main():
    print("="*55)
    print("稳健Alpha挖掘 — 自动刷新认证")
    print("="*55)

    client = RetryableBrainClient()
    await client.authenticate_with_retry()
    print("认证完成\n")

    results, best, counter = load()
    tested = {r.get('expression','')[:80] for r in results}
    best_s = best.get('sharpe',0) if best else 0
    last_auth = time.time()
    candidates = list(gen())

    print(f"已加载: {len(results)} 条, 最佳: {best_s:.3f}")
    print(f"待测: {len(candidates)} 个\n")

    new = 0
    for idx, name, expr in candidates:
        if expr[:80] in tested:
            continue

        # 每30分钟刷新认证
        if time.time() - last_auth > 1800:
            client._authenticated = False
            await client.authenticate_with_retry()
            last_auth = time.time()
            print(f"  [认证刷新]")

        print(f"[{new+1}] {name[:50]}...", end=" ", flush=True)
        settings = SETTINGS.copy()
        settings["description"] = f"r_{name}"

        try:
            sim = await client.create_simulation_with_retry(expr, settings)
            if sim.get('status') == 'ERROR':
                print(f"API错误: {sim.get('message','')[:60]}")
                await asyncio.sleep(30)
                continue

            alpha = await client.get_alpha_with_retry(sim['alpha_id'])
            s = alpha.get('sharpe', 0)
            print(f"Sharpe={s:.3f}")

            r = {"alpha_id": sim['alpha_id'], "expression": expr, "name": name,
                 "sharpe": s, "fitness": alpha.get('fitness',0),
                 "ppc": alpha.get('ppc',0), "margin": alpha.get('margin',0),
                 "turnover": alpha.get('turnover',0),
                 "status": "ok", "timestamp": datetime.now().isoformat()}

            results.append(r)
            tested.add(expr[:80])

            if s > best_s:
                best_s = s; best = r
                save(results, best, counter + new)
                print(f"  *** 新最佳! ***")

            if s >= 1.58:
                print(f"  *** 可提交! alpha_id={r['alpha_id']} ***")
                save(results, best, counter + new)
                break

        except Exception as e:
            err = str(e)[:60]
            print(f"错误: {err}")
            if '401' in err or 'auth' in err.lower():
                client._authenticated = False
                await client.authenticate_with_retry()
                last_auth = time.time()
                print(f"  [重新认证]")
            await asyncio.sleep(30)
            continue

        new += 1
        if new % 5 == 0:
            save(results, best, counter + new)
        await asyncio.sleep(2)

    save(results, best, counter + new)
    print(f"\n完成: {new} 新测试, 最佳Sharpe: {best_s:.3f}")

if __name__ == "__main__":
    asyncio.run(main())