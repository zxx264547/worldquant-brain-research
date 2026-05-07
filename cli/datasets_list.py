#!/usr/bin/env python3
"""
数据集列表CLI - wq-datasets
用法: wq-datasets
"""

import sys
import json
import asyncio
import argparse

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


async def list_datasets() -> dict:
    """获取可用数据集列表"""
    client = RetryableBrainClient()

    try:
        datasets = await client.get_datasets_with_retry()
        return {"success": True, "datasets": datasets, "count": len(datasets)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="获取可用数据集列表")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()
    result = await list_datasets()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print(f"可用数据集 ({result.get('count')}):")
            for d in result.get("datasets", []):
                print(f"  - {d.get('name', 'N/A')}: {d.get('description', '')[:40]}")
        else:
            print(f"获取失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    asyncio.run(main())
