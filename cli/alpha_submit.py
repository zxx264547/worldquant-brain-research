#!/usr/bin/env python3
"""
检查可提交Alpha CLI - wq-alpha-submit
用法: wq-alpha-submit --stage IS
"""

import sys
import json
import asyncio
import argparse

sys.path.insert(0, "/home/zxx/worldQuant")
from worldquant_brain.scripts.core.api_client import RetryableBrainClient


async def check_submittable(stage: str = "IS", limit: int = 50) -> dict:
    """检查可提交的Alpha"""
    client = RetryableBrainClient()

    try:
        # 获取用户Alpha
        from platform_functions import BrainApiClient
        api_client = BrainApiClient()

        config_path = "/home/zxx/worldQuant/worldquant_brain/config/user_config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)

        await api_client.authenticate(
            config.get('email', ''),
            config.get('password', '')
        )

        alphas = await api_client.get_user_alphas(stage=stage, limit=limit)

        if not alphas or 'results' not in alphas:
            return {"success": True, "alphas": [], "message": "No alphas found"}

        results = alphas['results']
        submittable = []
        near_miss = []

        for alpha in results[:limit]:
            alpha_id = alpha.get('id')
            details = await api_client.get_alpha_details(alpha_id)

            if not details:
                continue

            is_data = details.get('is', {})
            sharpe = is_data.get('sharpe', 0)
            fitness = is_data.get('fitness', 0)
            turnover = is_data.get('turnover', 0)
            margin = is_data.get('margin', 0)
            returns_val = is_data.get('returns', 0)

            ppc = abs(margin / returns_val) if returns_val != 0 else 1

            checks = {
                'sharpe': sharpe >= 1.58,
                'fitness': fitness > 0.5,
                'ppc': ppc < 0.5,
                'margin_gt_turnover': margin > turnover,
                'turnover': turnover > 0.01
            }

            passed = sum(checks.values())
            total = len(checks)

            alpha_info = {
                'alpha_id': alpha_id,
                'sharpe': sharpe,
                'fitness': fitness,
                'ppc': ppc,
                'margin': margin,
                'turnover': turnover,
                'passed': passed,
                'total': total,
                'checks': checks
            }

            if all(checks.values()):
                submittable.append(alpha_info)
            elif passed >= total - 1:
                near_miss.append(alpha_info)

        return {
            "success": True,
            "total": len(results),
            "submittable": submittable,
            "near_miss": near_miss,
            "submittable_count": len(submittable),
            "near_miss_count": len(near_miss)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="检查可提交的Alpha")
    parser.add_argument("--stage", default="IS", help="阶段 (IS/OS)")
    parser.add_argument("--limit", type=int, default=50, help="检查数量")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()
    result = await check_submittable(args.stage, args.limit)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if result.get("success"):
            print(f"检查完成: {result.get('total')} 个Alpha")
            print(f"可提交: {result.get('submittable_count')} 个")
            print(f"Near Miss: {result.get('near_miss_count')} 个")

            if result.get("submittable"):
                print("\n✅ 可提交的Alpha:")
                for a in result.get("submittable", []):
                    print(f"  {a.get('alpha_id')}: Sharpe={a.get('sharpe'):.2f}")

            if result.get("near_miss"):
                print("\n⚠️ Near Miss:")
                for a in result.get("near_miss", []):
                    failed = [k for k, v in a.get('checks', {}).items() if not v]
                    print(f"  {a.get('alpha_id')}: {failed}")
        else:
            print(f"检查失败: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
