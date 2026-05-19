#!/usr/bin/env python3
"""通用批量回测 — 传JSON配置文件，统一跑批

用法: python batch_backtest.py <config.json>

config.json 格式:
{
  "base": {"region":"EUR","universe":"TOPCS1600"},
  "prefix": "BAT",
  "output": "results.json",
  "tests": [
    {"name":"test1","expression":"rank(close)","settings":{"neutralization":"SECTOR"}},
    {"name":"test2","expression":"zscore(ts_mean(close,22))"}
  ]
}
"""

import asyncio, json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from worldquant_brain.engine.backtest_runner import BacktestRunner

DEFAULTS = {"region":"USA","universe":"TOP3000","delay":1,"decay":0,"neutralization":"NONE","truncation":0.01}

async def main():
    if len(sys.argv) < 2:
        print(__doc__); return

    with open(sys.argv[1]) as f:
        config = json.load(f)
    base = {**DEFAULTS, **config.get("base",{})}
    tests = config.get("tests",[])
    outfile = config.get("output","batch_results.json")
    prefix = config.get("prefix","BAT")

    print(f"=== {prefix} ({len(tests)} tests) ===")
    runner = BacktestRunner()
    await runner.init()
    runner.client.set_batch_prefix(prefix)
    results = []

    for i, t in enumerate(tests):
        settings = {**base, **t.get("settings",{})}
        name = t.get("name",f"test_{i+1}")
        print(f"[{i+1}/{len(tests)}] {name}", end=" ", flush=True)
        try:
            r = await runner.run(t["expression"], settings=settings, name=name)
            if r.get("status") == "ok":
                s, f = r["sharpe"], r["fitness"]
                to = r.get("turnover",0)
                ppc = r.get("ppc",0)
                mark = "***" if s >= 1.58 else ("+" if s >= 1.0 else "")
                print(f"S={s:.3f} F={f:.2f} TO={to:.4f} PPC={ppc:.4f} {mark}")
                results.append(r)
                with open(outfile,"w") as fh: json.dump(results, fh, indent=2, default=str)
        except Exception as e:
            print(f"ERR: {e}")
        if (i+1) % 5 == 0 and i < len(tests)-1:
            print("  [冷却70s...]")
            await asyncio.sleep(70)

    ok = [r for r in results if r.get("status")=="ok"]
    sub = [r for r in ok if r["sharpe"]>=1.58]
    print(f"\n=== {len(ok)}/{len(tests)} done, {len(sub)} submittable ===")
    for r in sorted(ok, key=lambda x: x["sharpe"], reverse=True):
        print(f"  {r.get('name','?'):25s} S={r['sharpe']:.3f}")

    # Auto ingest
    if len(ok) > 0:
        try:
            from worldquant_brain.scripts.brain_data_scope import ingest_from_results, init_db
            db = init_db()
            c = ingest_from_results(db, outfile)
            print(f"  Ingested {c} records")
        except: pass
    print(f"\nResults: {outfile}")

if __name__ == "__main__":
    asyncio.run(main())
