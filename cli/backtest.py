#!/usr/bin/env python3
"""
回测CLI - wq-backtest
用法:
  单次回测: wq-backtest --expression "rank(close)" --dataset TOP1500
  批量回测: wq-backtest --batch ideas.json
  带设置:   wq-backtest -e "ts_mean(rank(close), 22)" --decay 2 --neut industry
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 添加项目路径
sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


# 默认回测设置
DEFAULT_SETTINGS = {
    "dataset": "TOP1500",
    "region": "USA",
    "universe": "TOP1500",
    "delay": 1,
    "decay": 0,
    "neutralization": "NONE",
    "truncation": 0.08,
    "wait": 60
}


async def run_single_backtest(
    expression: str,
    settings: Optional[Dict] = None,
    timeout: int = 600
) -> Dict[str, Any]:
    """执行单次回测"""
    client = RetryableBrainClient()

    if settings is None:
        settings = DEFAULT_SETTINGS.copy()

    try:
        result = await client.create_simulation_with_retry(
            expression=expression,
            settings=settings,
            timeout=timeout
        )
        return {
            "success": True,
            "expression": expression,
            "settings": settings,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "error": str(e)
        }


async def run_batch_backtest(ideas_file: str, max_concurrent: int = 3) -> list:
    """批量执行回测"""
    with open(ideas_file) as f:
        ideas = json.load(f).get("ideas", [])

    results = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(idea):
        async with semaphore:
            expression = idea.get("expression")
            settings = idea.get("settings", DEFAULT_SETTINGS.copy())
            result = await run_single_backtest(expression, settings)
            result["idea_id"] = idea.get("id")
            return result

    tasks = [run_one(idea) for idea in ideas]
    results = await asyncio.gather(*tasks)

    return results


def parse_settings(args) -> Dict:
    """从命令行参数解析设置"""
    settings = DEFAULT_SETTINGS.copy()

    if args.dataset:
        settings["dataset"] = args.dataset
    if args.region:
        settings["region"] = args.region
    if args.universe:
        settings["universe"] = args.universe
    if args.decay is not None:
        settings["decay"] = args.decay
    if args.neutralization:
        settings["neutralization"] = args.neutralization
    if args.truncation is not None:
        settings["truncation"] = args.truncation

    return settings


def main():
    parser = argparse.ArgumentParser(description="Alpha回测CLI")
    parser.add_argument("--expression", "-e", help="Alpha表达式")
    parser.add_argument("--dataset", default="TOP1500", help="数据集")
    parser.add_argument("--region", default="USA", help="区域")
    parser.add_argument("--universe", help="Universe")
    parser.add_argument("--decay", type=int, help="Decay值")
    parser.add_argument("--neutralization", help="中性化方式")
    parser.add_argument("--truncation", type=float, help="截断值")
    parser.add_argument("--batch", help="批量文件(JSON格式)")
    parser.add_argument("--timeout", type=int, default=600, help="超时时间(秒)")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    parser.add_argument("--save", help="保存结果到文件")

    args = parser.parse_args()

    if args.batch:
        # 批量回测
        print(f"开始批量回测: {args.batch}")
        results = asyncio.run(run_batch_backtest(args.batch))

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            success = sum(1 for r in results if r.get("success"))
            print(f"\n完成: {success}/{len(results)} 成功")

            for r in results:
                status = "✅" if r.get("success") else "❌"
                if r.get("success"):
                    result = r.get("result", {})
                    print(f"  {status} {r.get('idea_id')}: Sharpe={result.get('sharpe', 'N/A')}")
                else:
                    print(f"  {status} {r.get('idea_id')}: {r.get('error', 'unknown')[:50]}")

        if args.save:
            with open(args.save, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n结果已保存: {args.save}")

    elif args.expression:
        # 单次回测
        settings = parse_settings(args)

        if not args.json:
            print(f"表达式: {args.expression}")
            print(f"设置: {settings}")
            print("执行回测中...")

        result = asyncio.run(run_single_backtest(args.expression, settings))

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if result.get("success"):
                r = result.get("result", {})
                print("\n✅ 回测成功!")
                print(f"  Alpha ID: {r.get('alpha_id', 'N/A')}")
                print(f"  Sharpe: {r.get('sharpe', 'N/A')}")
                print(f"  Fitness: {r.get('fitness', 'N/A')}")
                print(f"  Turnover: {r.get('turnover', 0)*100:.1f}%")
                print(f"  PPC: {r.get('ppc', 'N/A')}")
                print(f"  Margin: {r.get('margin', 'N/A')}")
            else:
                print(f"\n❌ 回测失败: {result.get('error', '未知错误')}")

        if args.save:
            with open(args.save, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"结果已保存: {args.save}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()