#!/usr/bin/env python3
"""
OS评分计算CLI - wq-os-score
用法: wq-os-score --pnl pnl.json
     wq-os-score --alpha-id ALPHA123
"""

import sys
import json
import asyncio
import argparse

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.analysis.os_score_calculator import PnlScoringCalculator


async def calculate_os_score(alpha_id: str, pnl: list = None) -> dict:
    """计算OS评分"""
    calculator = PnlScoringCalculator()

    if pnl is None:
        # 需要从API获取
        from worldquant_brain.scripts.core.api_client import RetryableBrainClient
        client = RetryableBrainClient()
        pnl = await client.get_pnl_with_retry(alpha_id)

    if not pnl:
        return {"success": False, "error": "No PnL data available"}

    result = calculator.calculate(alpha_id, pnl)

    return {
        "success": True,
        "alpha_id": result.alpha_id,
        "d1_kratio": result.d1,
        "d2_trend": result.d2,
        "d3_hurst": result.d3,
        "d4_health": result.d4,
        "total_score": result.total_score,
        "label": result.label
    }


async def main():
    parser = argparse.ArgumentParser(description="Alpha OS评分计算")
    parser.add_argument("--alpha-id", help="Alpha ID")
    parser.add_argument("--pnl-file", help="PnL文件(JSON)")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    pnl = None
    if args.pnl_file:
        with open(args.pnl_file) as f:
            pnl = json.load(f)

    if not args.alpha_id and not pnl:
        parser.print_help()
        return

    alpha_id = args.alpha_id or "local"
    result = await calculate_os_score(alpha_id, pnl)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print(f"Alpha: {result.get('alpha_id')}")
            print(f"总分: {result.get('total_score'):.1f}/100 ({result.get('label')})")
            print(f"  D1(K-Ratio): {result.get('d1_kratio'):.3f}")
            print(f"  D2(趋势): {result.get('d2_trend'):.3f}")
            print(f"  D3(Hurst): {result.get('d3_hurst'):.3f}")
            print(f"  D4(健康度): {result.get('d4_health'):.3f}")
        else:
            print(f"计算失败: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
