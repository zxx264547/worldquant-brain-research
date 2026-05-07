#!/usr/bin/env python3
"""
数据集字段CLI - wq-fields
用法: wq-fields --dataset TOP1500
"""

import sys
import json
import asyncio
import argparse

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


async def list_fields(dataset_id: str) -> dict:
    """获取数据集字段"""
    client = RetryableBrainClient()

    try:
        fields = await client.get_datafields_with_retry(dataset_id)
        return {"success": True, "dataset": dataset_id, "fields": fields, "count": len(fields)}
    except Exception as e:
        return {"success": False, "dataset": dataset_id, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="获取数据集字段")
    parser.add_argument("--dataset", required=True, help="数据集ID")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()
    result = await list_fields(args.dataset)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print(f"数据集: {result.get('dataset')}")
            print(f"字段数: {result.get('count')}")
            for f in result.get("fields", [])[:10]:
                print(f"  - {f.get('name', 'N/A')}: {f.get('description', '')[:40]}")
            if result.get("count", 0) > 10:
                print(f"  ... 还有 {result.get('count') - 10} 个字段")
        else:
            print(f"获取失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    asyncio.run(main())
