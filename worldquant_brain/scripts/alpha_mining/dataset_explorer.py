#!/usr/bin/env python3
"""
数据集探索器 - 批量测试多个数据集的基本特性
对每个数据集随机取字段测试，了解其Alpha潜力

用法:
  python dataset_explorer.py --datasets fundamental6 analyst4 pv87
  python dataset_explorer.py --all  # 测试所有数据集
"""

import asyncio
import json
import sys
import time
import random
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient

# 测试配置
DEFAULT_SETTINGS = {
    "dataset": "TOP1500",
    "region": "USA",
    "universe": "TOP1500",
    "delay": 1,
    "decay": 0,
    "neutralization": "NONE",
    "truncation": 0.08,
}

# 要测试的关键数据集（按类别选取代表性）
KEY_DATASETS = [
    "fundamental6", "fundamental1", "fundamental13",
    "analyst4", "analyst10", "analyst49",
    "pv87", "pv13", "pv1",
    "news12", "sentiment1", "socialmedia12",
    "macro63", "forward_beta_risk",
    "model109", "model136", "model127",
    "earnings6", "earnings27",
    "risk60", "risk62",
    "option3", "option23",
    "shortinterest2", "shortinterest10",
]


async def test_dataset(client: RetryableBrainClient, dataset_id: str, timeout: int = 120) -> dict:
    """测试单个数据集"""
    result = {
        "dataset": dataset_id,
        "success": False,
        "error": None,
        "sharpe": None,
        "fitness": None,
        "turnover": None,
        "margin": None,
        "fields_tested": 0,
        "best_field": None,
        "tested_fields": [],
    }

    try:
        # 获取字段列表
        fields = await client.get_datafields_with_retry(dataset_id)
        if not fields:
            result["error"] = "No fields found"
            return result

        # 随机取5个字段测试
        random.seed(42)  # 可重复性
        sample_size = min(5, len(fields))
        test_fields = random.sample(fields, sample_size)
        result["fields_tested"] = len(test_fields)

        best_sharpe = -999
        best_field = None

        for field in test_fields:
            field_id = field.get("id", "")
            if not field_id:
                continue

            # 简化表达式：rank(field_id)
            expression = f"rank({field_id})"

            try:
                sim_result = await client.create_simulation_with_retry(
                    expression=expression,
                    settings=DEFAULT_SETTINGS,
                    timeout=timeout
                )

                sharpe = sim_result.get("sharpe", 0) or 0
                result["tested_fields"].append({
                    "field": field_id,
                    "sharpe": sharpe,
                    "fitness": sim_result.get("fitness", 0)
                })

                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_field = field_id
                    result["sharpe"] = sharpe
                    result["fitness"] = sim_result.get("fitness", 0)
                    result["turnover"] = sim_result.get("turnover", 0)
                    result["margin"] = sim_result.get("margin", 0)

            except Exception as e:
                continue

        result["best_field"] = best_field
        result["success"] = best_sharpe > 0

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


async def explore_datasets(dataset_ids: list, output_file: str = None):
    """批量探索数据集"""
    client = RetryableBrainClient()
    await client.authenticate_with_retry()

    results = []
    stats = defaultdict(int)

    for i, ds_id in enumerate(dataset_ids):
        print(f"[{i+1}/{len(dataset_ids)}] Testing {ds_id}...", end=" ", flush=True)

        result = await test_dataset(client, ds_id)
        results.append(result)

        if result["success"]:
            print(f"Sharpe={result['sharpe']:.2f} Fitness={result['fitness']:.2f}")
            stats["success"] += 1
        elif result["error"]:
            print(f"Error: {result['error'][:40]}")
            stats["error"] += 1
        else:
            print("No signal (Sharpe<=0)")
            stats["no_signal"] += 1

        # 避免限流
        await asyncio.sleep(1)

    # 保存结果
    if output_file:
        output_data = {
            "results": results,
            "summary": {
                "total": len(results),
                "success": stats["success"],
                "error": stats["error"],
                "no_signal": stats["no_signal"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {output_file}")

    return results


async def get_all_datasets(client: RetryableBrainClient) -> list:
    """获取所有数据集ID"""
    datasets = await client.get_datasets_with_retry()
    return [d.get("id") for d in datasets if d.get("id")]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="数据集探索器")
    parser.add_argument("--datasets", nargs="+", help="数据集ID列表")
    parser.add_argument("--output", default="/home/zxx/worldQuant/worldquant_brain/data/outputs/dataset_exploration.json", help="输出文件")
    parser.add_argument("--all", action="store_true", help="测试所有数据集")
    args = parser.parse_args()

    if args.all:
        print("获取所有数据集...")
        client = RetryableBrainClient()
        asyncio.run(client.authenticate_with_retry())
        datasets = asyncio.run(get_all_datasets(client))
        print(f"找到 {len(datasets)} 个数据集")
    else:
        datasets = args.datasets or KEY_DATASETS

    asyncio.run(explore_datasets(datasets, args.output))
