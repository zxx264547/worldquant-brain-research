#!/usr/bin/env python3
"""调试 API - 查看返回数据格式"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings, SimulationData

async def debug():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    client = BrainApiClient()

    print("[1] 认证...")
    await client.authenticate(config['credentials']['email'], config['credentials']['password'])
    print("✅ 认证成功\n")

    print("[2] 获取数据集...")
    datasets = await client.get_datasets()
    if isinstance(datasets, dict) and 'results' in datasets:
        results = datasets['results']
        print(f"数据集数量: {len(results) if results else 0}")
        if results and len(results) > 0:
            print(f"第一个数据集: {json.dumps(results[0], indent=2)[:300]}")
    print()

    print("[3] 获取pv87字段...")
    fields = await client.get_datafields("pv87")
    if isinstance(fields, dict) and 'results' in fields:
        results = fields['results']
        if isinstance(results, list):
            print(f"字段数量: {len(results)}")
            if len(results) > 0:
                print(f"第一个字段: {json.dumps(results[0], indent=2)[:300]}")
    print()

    print("[4] 运行简单模拟...")
    test_expr = "rank(demean(pv87_2_af_return_high))"
    print(f"表达式: {test_expr}")

    settings = SimulationSettings(
        instrumentType="EQUITY",
        region="USA",
        universe="TOP3000",
        delay=1,
        decay=0.0,
        neutralization="NONE",
        truncation=0,
        testPeriod="P0Y0M",
        unitHandling="VERIFY",
        nanHandling="OFF",
        language="FASTEXPR",
        visualization=False
    )

    sim_data = SimulationData(
        type="REGULAR",
        settings=settings,
        regular=test_expr
    )

    sim_result = await client.create_simulation(sim_data)

    print(f"\n返回类型: {type(sim_result)}")
    if isinstance(sim_result, dict):
        print(f"返回键: {sim_result.keys()}")
        if 'data' in sim_result:
            data = sim_result['data']
            print(f"data类型: {type(data)}")
            if isinstance(data, dict):
                print(f"data内容: {json.dumps(data, indent=2)[:500]}")
            elif isinstance(data, list):
                print(f"data长度: {len(data)}")
                if len(data) > 0:
                    print(f"data[0]: {data[0]}")
        elif 'simulationId' in sim_result:
            print(f"simulationId: {sim_result['simulationId']}")
    else:
        print(f"返回: {str(sim_result)[:500]}")

if __name__ == "__main__":
    asyncio.run(debug())
