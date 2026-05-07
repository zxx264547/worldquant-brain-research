#!/usr/bin/env python3
"""
Alpha相关性分析CLI - wq-alpha-correlate
用法: wq-alpha-correlate --alphas alphas.json
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.alpha_mining.correlation_analysis import CorrelationScreening
from worldquant_brain.scripts.core.types import AlphaInfo


async def analyze_correlation(alpha_ids: list, threshold: float = 0.8) -> dict:
    """分析Alpha相关性"""
    screener = CorrelationScreening(correlation_threshold=threshold)

    alphas = [{"alpha_id": aid} for aid in alpha_ids]
    results, stats = await screener.screen(alphas, fetch_pnl=False)

    return {
        "success": True,
        "input_count": len(alpha_ids),
        "output_count": len(results),
        "representatives": [
            {
                "alpha_id": r.alpha_id,
                "sharpe": r.sharpe,
                "fitness": r.fitness
            }
            for r in results
        ],
        "stats": stats
    }


async def main():
    parser = argparse.ArgumentParser(description="Alpha相关性分析")
    parser.add_argument("--alphas", required=True, help="Alpha列表文件(JSON)")
    parser.add_argument("--threshold", type=float, default=0.8, help="相关性阈值")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    with open(args.alphas) as f:
        data = json.load(f)

    alpha_ids = data.get("alpha_ids", data.get("alphas", []))
    result = await analyze_correlation(alpha_ids, args.threshold)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"输入: {result.get('input_count')} 个Alpha")
        print(f"输出: {result.get('output_count')} 个代表Alpha")
        print(f"分族数: {result.get('stats', {}).get('total_families', 'N/A')}")
        for r in result.get("representatives", []):
            print(f"  - {r.get('alpha_id')}: Sharpe={r.get('sharpe', 0):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
