#!/usr/bin/env python3
"""
Alpha详情CLI - wq-alpha-get
用法: wq-alpha-get --alpha-id ALPHA123
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


async def get_alpha(alpha_id: str) -> dict:
    """获取Alpha详情"""
    client = RetryableBrainClient()

    try:
        result = await client.get_alpha_with_retry(alpha_id)
        return {"success": True, "alpha_id": alpha_id, **result}
    except Exception as e:
        return {"success": False, "alpha_id": alpha_id, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="获取Alpha详情")
    parser.add_argument("--alpha-id", required=True, help="Alpha ID")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()
    result = await get_alpha(args.alpha_id)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print(f"Alpha: {result.get('alpha_id')}")
            print(f"  Sharpe: {result.get('sharpe', 'N/A')}")
            print(f"  Fitness: {result.get('fitness', 'N/A')}")
            print(f"  Turnover: {result.get('turnover', 'N/A')}")
            print(f"  Margin: {result.get('margin', 'N/A')}")
            print(f"  PPC: {result.get('ppc', 'N/A')}")
            print(f"  Expression: {result.get('expression', 'N/A')[:50]}...")
        else:
            print(f"获取失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    asyncio.run(main())
