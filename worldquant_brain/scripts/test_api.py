#!/usr/bin/env python3
"""测试API连接"""

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

    print("\n[2] 获取数据集...")
    datasets = await client.get_datasets()
    print(f"数据集数量: {len(datasets.get('results', [])) if datasets else 0}")
    if datasets and 'results' in datasets:
        for ds in datasets['results'][:5]:
            print(f"  - {ds['id']}: {ds.get('name', 'N/A')}")

    print("\n[3] 获取字段 (pv87)...")
    fields = await client.get_datafields(dataset_id="pv87")
    print(f"字段数量: {len(fields.get('results', [])) if fields else 0}")
    if fields and 'results' in fields:
        for f in fields['results'][:3]:
            print(f"  - {f['id']}")

    print("\n[4] 创建简单模拟测试...")
    test_expr = "rank(demean(pv87_2_af_return_high))"
    print(f"表达式: {test_expr}")

    settings_dict = {
        'instrumentType': 'EQUITY',
        'region': 'USA',
        'universe': 'TOP3000',
        'delay': 1,
        'decay': 0.0,
        'neutralization': 'NONE',
        'truncation': 0.0,
        'testPeriod': 'P0Y0M',
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
    print(f"创建模拟状态: {resp.status_code}")
    if resp.status_code == 201:
        print(f"模拟ID: {resp.json().get('id')}")
        print(f"Location: {resp.headers.get('Location', 'N/A')}")
    else:
        print(f"错误: {resp.text[:200]}")

    print("\n✅ API测试完成!")


if __name__ == "__main__":
    asyncio.run(main())