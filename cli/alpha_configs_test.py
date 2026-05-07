#!/usr/bin/env python3
"""
Alpha配置测试CLI - wq-alpha-configs-test
用法: wq-alpha-configs-test --configs configs.json
"""

import sys
import json
import asyncio
import argparse

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


async def test_configs(configs_file: str) -> list:
    """测试多个Alpha配置"""
    with open(configs_file) as f:
        configs = json.load(f)

    client = RetryableBrainClient()
    results = []

    async def test_one(config):
        expression = config.get("expression")
        settings = {**DEFAULT_SETTINGS, **config.get("settings", {})}

        try:
            result = await client.create_simulation_with_retry(expression, settings)
            return {
                "success": True,
                "name": config.get("name", expression[:40]),
                "expression": expression,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "name": config.get("name", expression[:40]),
                "error": str(e)
            }

    tasks = [test_one(c) for c in configs]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    parser = argparse.ArgumentParser(description="Alpha配置测试")
    parser.add_argument("--configs", required=True, help="配置文件(JSON)")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--save", help="保存结果到文件")

    args = parser.parse_args()
    results = await test_configs(args.configs)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for r in results:
            status = "✅" if r.get("success") else "❌"
            if r.get("success"):
                print(f"{status} {r.get('name')}: Sharpe={r.get('result', {}).get('sharpe', 'N/A')}")
            else:
                print(f"{status} {r.get('name')}: {r.get('error', 'unknown')[:50]}")

    if args.save:
        with open(args.save, 'w') as f:
            json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())
