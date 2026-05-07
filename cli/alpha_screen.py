#!/usr/bin/env python3
"""
Alpha筛选CLI - wq-alpha-screen
用法: wq-alpha-screen --alpha-id ALPHA123
     wq-alpha-screen --batch alphas.json
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.alpha_mining.screening_pipeline import ScreeningPipeline, PPA_STANDARDS


async def screen_alpha(alpha_id: str, credentials: dict = None) -> dict:
    """筛选单个Alpha"""
    pipeline = ScreeningPipeline(credentials=credentials)

    result = await pipeline.screen_alpha(alpha_id)
    return {
        "success": result.passed,
        "alpha_id": result.alpha_id,
        "passed": result.passed,
        "sharpe": result.sharpe,
        "fitness": result.fitness,
        "ppc": result.ppc,
        "margin": result.margin,
        "turnover": result.turnover,
        "reasons": result.reasons
    }


async def main():
    parser = argparse.ArgumentParser(description="Alpha PPA筛选")
    parser.add_argument("--alpha-id", help="Alpha ID")
    parser.add_argument("--batch", help="批量文件(JSON格式)")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    if args.batch:
        with open(args.batch) as f:
            data = json.load(f)
        alpha_ids = data.get("alpha_ids", [])

        pipeline = ScreeningPipeline()
        passed, rejected = await pipeline.screen_batch(alpha_ids)

        results = {
            "total": len(alpha_ids),
            "passed": [r.to_dict() for r in passed],
            "rejected": [r.to_dict() for r in rejected]
        }

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print(f"筛选完成: {len(passed)}/{len(alpha_ids)} 通过")
            for r in passed:
                print(f"  ✅ {r.alpha_id}: Sharpe={r.sharpe:.2f}")

    elif args.alpha_id:
        result = await screen_alpha(args.alpha_id)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if result.get("passed"):
                print(f"✅ {result.get('alpha_id')}: 通过PPA筛选")
                print(f"   Sharpe={result.get('sharpe'):.2f}, Fitness={result.get('fitness'):.2f}")
            else:
                print(f"❌ {result.get('alpha_id')}: 未通过")
                for reason in result.get("reasons", []):
                    print(f"   - {reason}")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
