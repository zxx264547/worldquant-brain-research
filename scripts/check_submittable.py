#!/usr/bin/env python3
"""检查现有Alpha是否满足提交条件"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    client = BrainApiClient()

    print("认证中...")
    await client.authenticate(config['credentials']['email'], config['credentials']['password'])
    print("✅ 认证成功!")

    # 获取所有IS阶段的Alpha
    print("\n获取用户的Alpha...")
    alphas = await client.get_user_alphas(stage='IS', limit=100, order='-dateCreated')

    if not alphas or 'results' not in alphas:
        print("没有找到Alpha")
        return

    results = alphas['results']
    print(f"找到 {len(results)} 个Alpha")

    # 严格筛选条件
    # Sharpe≥1.58, Fitness>0.5, PPC<0.5, Margin>Turnover, Turnover>0.01
    submittable = []
    near_miss = []

    for alpha in results:
        alpha_id = alpha.get('id')
        details = await client.get_alpha_details(alpha_id)

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
            'turnover': turnover > 0.01,
        }

        all_pass = all(checks.values())

        reg = details.get('regular', {})
        if isinstance(reg, dict):
            expression = reg.get('code', '')
        else:
            expression = str(reg)

        result = {
            'alpha_id': alpha_id,
            'sharpe': sharpe,
            'fitness': fitness,
            'ppc': ppc,
            'margin': margin,
            'turnover': turnover,
            'expression': expression[:80],
            'checks': checks,
            'all_pass': all_pass,
        }

        if all_pass:
            submittable.append(result)
        else:
            # 记录差一点就能提交的
            passed_count = sum(checks.values())
            if passed_count >= 4:  # 5个条件过了4个
                near_miss.append(result)

        print(f"Alpha {alpha_id}: Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, PPC={ppc:.2f}, Margin={margin:.4f}, Turnover={turnover:.4f}")
        print(f"  条件: Sharpe≥1.58:{'✅' if checks['sharpe'] else '❌'}, Fitness>0.5:{'✅' if checks['fitness'] else '❌'}, PPC<0.5:{'✅' if checks['ppc'] else '❌'}")
        print(f"        Margin>Turnover:{'✅' if checks['margin_gt_turnover'] else '❌'}, Turnover>0.01:{'✅' if checks['turnover'] else '❌'}")

    print("\n" + "=" * 60)
    print(f"总结: 满足所有条件的Alpha: {len(submittable)}")
    print(f"     差一点就能提交的: {len(near_miss)}")

    if submittable:
        print("\n🎉 可提交Alpha:")
        for s in submittable:
            print(f"  {s['alpha_id']}: Sharpe={s['sharpe']:.2f}, Fitness={s['fitness']:.2f}")
            print(f"    PPC={s['ppc']:.3f}, Margin={s['margin']:.4f}>T={s['turnover']:.4f}")
            print(f"    {s['expression']}")

    if near_miss:
        print("\n⚠️ 差一点就能提交的Alpha:")
        for n in near_miss:
            print(f"  {n['alpha_id']}: Sharpe={n['sharpe']:.2f}, Fitness={n['fitness']:.2f}, PPC={n['ppc']:.3f}")
            print(f"    Margin={n['margin']:.4f}, Turnover={n['turnover']:.4f}")
            print(f"    失败条件: {[k for k,v in n['checks'].items() if not v]}")
            print(f"    {n['expression']}")

    # 保存结果
    output = {
        'submittable': submittable,
        'near_miss': near_miss,
    }
    output_path = os.path.join(os.path.dirname(__file__), '..', 'submittable_check.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())