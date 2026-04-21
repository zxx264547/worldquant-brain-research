#!/usr/bin/env python3
"""
挖掘高Sharpe且Margin>Turnover的Alpha
核心发现：mdl136字段高Sharpe但M/T低，pv87字段M/T高但Sharpe低
解决思路：用mdl136字段 + winsorize预处理
"""

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

    print("=" * 60)
    print("挖掘高Sharpe + Margin>Turnover Alpha")
    print("=" * 60)

    print("\n[1] 认证...")
    await client.authenticate(config['credentials']['email'], config['credentials']['password'])
    print("✅ 认证成功!")

    # 修复：使用真实有字段的数据集
    # mdl136/wds/news/alpha32返回0字段，只有这些可用：
    target_datasets = ['pv87', 'pv13', 'analyst4', 'fundamental6', 'pv1']
    all_fields = []

    for ds_id in target_datasets:
        print(f"\n[2.{ds_id}] 获取字段...")
        result = await client.get_datafields(dataset_id=ds_id)
        if result and 'results' in result:
            fields = result['results'][:12]  # 每个数据集取12个
            for f in fields:
                f['_dataset'] = ds_id
            all_fields.extend(fields)
            print(f"  {ds_id}: {len(fields)} 字段")
        else:
            print(f"  {ds_id}: 获取失败")
        await asyncio.sleep(0.5)

    if not all_fields:
        print("❌ 没有获取到任何字段!")
        return

    print(f"\n总计: {len(all_fields)} 个字段")

    # 核心模板：用winsorize预处理降turnover + 多样化模板提高Sharpe
    templates = [
        # winsorize系 - 降turnover
        ('winsorize({data})', 'winsorize'),
        ('winsorize(ts_backfill({data}))', 'win_backfill'),
        ('winsorize(ts_mean({data}, 10))', 'win_ts10'),
        ('winsorize(ts_mean({data}, 20))', 'win_ts20'),
        # ts_mean平滑
        ('ts_mean({data}, 10)', 'ts10'),
        ('ts_mean({data}, 20)', 'ts20'),
        # rank系 - 可能提高Sharpe
        ('rank({data})', 'rank'),
        ('rank(ts_mean({data}, 10))', 'rank_ts10'),
        # 复杂组合
        ('ts_mean(winsorize(ts_backfill({data})), 10)', 'mean_win_backfill'),
        ('rank(winsorize(ts_mean({data}, 10)))', 'rank_win_ts10'),
    ]

    settings_dict = {
        'instrumentType': 'EQUITY',
        'region': 'USA',
        'universe': 'TOP3000',
        'delay': 1,
        'decay': 0.0,
        'neutralization': 'NONE',
        'truncation': 0.0,
        'pasteurization': 'ON',
        'unitHandling': 'VERIFY',
        'nanHandling': 'OFF',
        'language': 'FASTEXPR',
        'visualization': False
    }

    results = []
    tested = 0
    max_tests = 200  # 限制测试数量

    print(f"\n[3] 开始挖掘 (最多测试 {min(len(all_fields), max_tests)} 字段 × {len(templates)} 模板)...")

    for field in all_fields:
        if tested >= max_tests:
            break
        field_id = field['id']
        ds = field.get('_dataset', 'unknown')

        for expr_template, template_name in templates:
            if tested >= max_tests:
                break

            tested += 1
            test_expr = expr_template.format(data=field_id)

            print(f"\n[{tested}] {ds}/{template_name}: {field_id[:25]}...")
            print(f"    {test_expr[:55]}...")

            payload = {
                'type': 'REGULAR',
                'settings': settings_dict,
                'regular': test_expr
            }

            resp = client.session.post(f'{client.base_url}/simulations', json=payload)

            if resp.status_code != 201:
                print(f"    ❌ 创建失败: {resp.status_code}")
                await asyncio.sleep(0.5)
                continue

            location = resp.headers.get('Location', '')

            # 轮询等待完成
            complete = False
            for _ in range(80):
                await asyncio.sleep(2)
                r = client.session.get(location)
                if r.status_code == 200:
                    data = r.json()
                    status = data.get('status')
                    if status == 'COMPLETE':
                        alpha_id = data.get('alpha')
                        if alpha_id:
                            ar = client.session.get(f'{client.base_url}/alphas/{alpha_id}')
                            if ar.status_code == 200:
                                alpha = ar.json()
                                is_data = alpha.get('is', {})
                                sharpe = is_data.get('sharpe', 0)
                                fitness = is_data.get('fitness', 0)
                                margin = is_data.get('margin', 0)
                                turnover = is_data.get('turnover', 0)
                                returns_val = is_data.get('returns', 0)
                                ppc = abs(margin / returns_val) if returns_val != 0 else 1

                                checks = {
                                    'sharpe': sharpe >= 1.0,  # 实际提交标准是1.0，不是1.58
                                    'fitness': fitness > 0.5,
                                    'ppc': ppc < 0.5,
                                    'margin_gt_turnover': margin > turnover,
                                    'turnover': turnover > 0.01,
                                }
                                all_pass = all(checks.values())

                                result = {
                                    'alpha_id': alpha_id,
                                    'sharpe': sharpe,
                                    'fitness': fitness,
                                    'margin': margin,
                                    'turnover': turnover,
                                    'ppc': ppc,
                                    'checks': checks,
                                    'all_pass': all_pass,
                                    'expression': test_expr,
                                    'template': template_name,
                                }
                                results.append(result)

                                print(f"    Sharpe={sharpe:.2f}, Fitness={fitness:.2f}")
                                print(f"    Margin={margin:.4f}, Turnover={turnover:.4f}, PPC={ppc:.3f}")
                                status_str = ', '.join([f"{k}:{'✅' if v else '❌'}" for k, v in checks.items()])
                                print(f"    {status_str}")

                                if all_pass:
                                    print(f"    🎉 可提交!")
                        complete = True
                        break
                    elif status == 'ERROR':
                        print(f"    ❌ 错误: {data.get('message', 'Unknown')[:50]}")
                        complete = True
                        break
                await asyncio.sleep(1)

            if not complete:
                print(f"    ⏰ 超时")

            await asyncio.sleep(0.5)

    # 汇总
    print("\n" + "=" * 60)
    print(f"挖掘完成! 测试了 {tested} 个")

    passing = [r for r in results if r['all_pass']]
    print(f"满足所有条件: {len(passing)} 个")

    # 按Sharpe排序
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    print("\nTop 10 高Sharpe Alpha:")
    for r in results[:10]:
        print(f"  Sharpe={r['sharpe']:.2f}, Margin={r['margin']:.4f}>T={r['turnover']:.4f}, {r['template']}")

    # 保存
    output = {
        'all_results': results,
        'passing': passing,
    }
    output_path = os.path.join(os.path.dirname(__file__), '..', 'high_sharpe_margin_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())