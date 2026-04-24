#!/usr/bin/env python3
"""测试pv87字段创建模拟"""

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

    print("[1] 认证...")
    await client.authenticate(config['credentials']['email'], config['credentials']['password'])
    print("✅ 认证成功!")

    # 获取pv87的字段
    print("\n[2] 获取pv87字段...")
    pv87_result = await client.get_datafields(dataset_id="pv87")
    if not pv87_result or 'results' not in pv87_result:
        print("❌ 获取pv87字段失败")
        return

    pv87_fields = pv87_result['results']
    print(f"pv87字段数量: {len(pv87_fields)}")

    # 使用第一个字段创建模拟
    field = pv87_fields[0]
    field_id = field['id']
    print(f"\n[3] 使用字段: {field_id}")
    print(f"描述: {field.get('description', 'N/A')[:50]}...")

    # 测试不同模板
    templates = [
        ('rank(demean({data}))', 'rank_demean'),
        ('winsorize({data})', 'winsorize'),
        ('ts_mean({data}, 20)', 'ts_mean_20'),
    ]

    for expr_template, name in templates:
        test_expr = expr_template.format(data=field_id)
        print(f"\n[4.{name}] 测试: {test_expr}")

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

        payload = {
            'type': 'REGULAR',
            'settings': settings_dict,
            'regular': test_expr
        }

        resp = client.session.post(f'{client.base_url}/simulations', json=payload)
        print(f"  状态: {resp.status_code}")
        if resp.status_code == 201:
            print(f"  ✅ 成功! Location: {resp.headers.get('Location', 'N/A')[:60]}...")
            # 等待模拟完成
            location = resp.headers.get('Location', '')
            for i in range(50):
                await asyncio.sleep(2)
                r = client.session.get(location)
                if r.status_code == 200:
                    data = r.json()
                    status = data.get('status')
                    print(f"  状态: {status}")
                    if status == 'COMPLETE':
                        alpha_id = data.get('alpha')
                        if alpha_id:
                            print(f"  Alpha ID: {alpha_id}")
                            # 获取alpha详情
                            ar = client.session.get(f'{client.base_url}/alphas/{alpha_id}')
                            if ar.status_code == 200:
                                alpha = ar.json()
                                is_data = alpha.get('is', {})
                                print(f"    Sharpe: {is_data.get('sharpe', 'N/A')}")
                                print(f"    Fitness: {is_data.get('fitness', 'N/A')}")
                                print(f"    Margin: {is_data.get('margin', 'N/A')}")
                                print(f"    Turnover: {is_data.get('turnover', 'N/A')}")
                        break
                    elif status == 'ERROR':
                        print(f"  ❌ 错误: {data.get('message', 'Unknown')[:50]}")
                        break
        else:
            print(f"  ❌ 失败: {resp.text[:150]}")
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())