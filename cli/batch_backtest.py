#!/usr/bin/env python3
"""
Alpha批量回测CLI - wq-batch-backtest
用法: wq-batch-backtest --ideas ideas.json --concurrent 5
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


DEFAULT_SETTINGS = {
    "dataset": "TOP1500",
    "region": "USA",
    "universe": "TOP1500",
    "delay": 1,
    "decay": 0,
    "neutralization": "NONE",
    "truncation": 0.08,
}


async def run_batch_backtest(ideas_file: str, concurrent: int = 5) -> list:
    """批量回测"""
    with open(ideas_file) as f:
        data = json.load(f)
    ideas = data.get("ideas", data.get("alpha_ids", []))

    client = RetryableBrainClient()
    semaphore = asyncio.Semaphore(concurrent)
    results = []

    async def run_one(idea):
        async with semaphore:
            if isinstance(idea, str):
                expression = idea
                settings = DEFAULT_SETTINGS.copy()
            else:
                expression = idea.get("expression", idea.get("alpha_id"))
                settings = idea.get("settings", DEFAULT_SETTINGS.copy())

            try:
                result = await client.create_simulation_with_retry(expression, settings)
                return {"success": True, "expression": expression, "result": result}
            except Exception as e:
                return {"success": False, "expression": expression, "error": str(e)}

    tasks = [run_one(idea) for idea in ideas]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    parser = argparse.ArgumentParser(description="Alpha批量回测")
    parser.add_argument("--ideas", required=True, help="Ideas文件(JSON)")
    parser.add_argument("--concurrent", type=int, default=5, help="并发数")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--save", help="保存结果到文件")

    args = parser.parse_args()
    results = await run_batch_backtest(args.ideas, args.concurrent)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        success = sum(1 for r in results if r.get("success"))
        print(f"完成: {success}/{len(results)} 成功")
        for r in results:
            status = "✅" if r.get("success") else "❌"
            if r.get("success"):
                print(f"  {status} {r.get('expression', 'N/A')[:40]}: Sharpe={r.get('result', {}).get('sharpe', 'N/A')}")
            else:
                print(f"  {status} {r.get('expression', 'N/A')[:40]}: {r.get('error', 'unknown')[:50]}")

    if args.save:
        with open(args.save, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n结果已保存: {args.save}")


if __name__ == "__main__":
    asyncio.run(main())
