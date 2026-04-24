#!/usr/bin/env python3
"""检查字段格式"""

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

    # 检查pv87数据集的字段
    print("\n[2] pv87字段结构:")
    fields = await client.get_datafields(dataset_id="pv87")
    if fields and 'results' in fields:
        for f in fields['results'][:3]:
            print(f"  字段: {json.dumps(f, indent=4)[:300]}")

    # 检查analyst10数据集的字段
    print("\n[3] analyst10字段结构:")
    fields = await client.get_datafields(dataset_id="analyst10")
    if fields and 'results' in fields:
        for f in fields['results'][:3]:
            print(f"  字段: {json.dumps(f, indent=4)[:300]}")

    # 尝试用pv87的字段创建模拟
    print("\n[4] 尝试用pv87创建模拟...")
    pv87_fields = fields['results'] if fields and 'results' in fields else []
    if pv87_fields:
        field_id = pv87_fields[0]['id']
        print(f"  使用字段: {field_id}")

        test_expr = f"rank(demean({field_id}))"
        print(f"  表达式: {test_expr}")

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
            print(f"  ✅ 成功! Location: {resp.headers.get('Location', 'N/A')}")
        else:
            print(f"  ❌ 失败: {resp.text[:200]}")


if __name__ == "__main__":
    asyncio.run(main())