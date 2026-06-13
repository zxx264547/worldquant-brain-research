#!/usr/bin/env python3
"""
Earnings27 Dataset Exploration
测试earnings27数据集中的VECTOR字段
"""

import sys
import asyncio
import json
import time
from pathlib import Path

sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
from platform_functions import BrainApiClient, SimulationData, SimulationSettings

OUTPUT_FILE = Path('/tmp/multi_agent/earnings27_batch1.json')
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# 候选表达式 - 使用earnings27字段
CANDIDATES = [
    # 基础模式测试
    ('ern27_earnings w22', 'zscore(-ts_max(vec_max(ern27_earnings), 22))'),
    ('ern27_expectations w22', 'zscore(-ts_max(vec_max(ern27_expectations), 22))'),
    ('ern27_positive w22', 'zscore(-ts_max(vec_max(ern27_positive), 22))'),
    ('ern27_negative w22', 'zscore(-ts_max(vec_max(ern27_negative), 22))'),
    ('ern27_neutral w22', 'zscore(-ts_max(vec_max(ern27_neutral), 22))'),
    # 不同窗口
    ('ern27_earnings w5', 'zscore(-ts_max(vec_max(ern27_earnings), 5))'),
    ('ern27_earnings w66', 'zscore(-ts_max(vec_max(ern27_earnings), 66))'),
    ('ern27_expectations w5', 'zscore(-ts_max(vec_max(ern27_expectations), 5))'),
]

SETTINGS = SimulationSettings(
    instrumentType='EQUITY',
    region='USA',
    universe='TOP3000',
    delay=1,
    decay=0,
    truncation=0.08,
    neutralization='INDUSTRY'
)

async def main():
    print('🔐 Authenticating...')
    client = BrainApiClient()
    await client.authenticate('2645471525@qq.com', '20001025ZHANG')
    print('✅ Authenticated\\n')

    results = []

    for name, expr in CANDIDATES:
        print(f'Creating: {name} - {expr[:50]}...')
        sim_data = SimulationData(
            type='REGULAR',
            regular=expr,
            settings=SETTINGS
        )

        try:
            result = await client.create_simulation(simulation_data=sim_data)
            sim_id = result.get('simulationId', 'N/A')
            print(f'  ✅ Created: {sim_id}')

            results.append({
                'name': name,
                'expression': expr,
                'simulationId': sim_id,
                'status': 'created'
            })

            # 保存进度
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)

            await asyncio.sleep(5)  # 避免限流

        except Exception as e:
            print(f'  ❌ Error: {e}')
            results.append({
                'name': name,
                'expression': expr,
                'error': str(e),
                'status': 'error'
            })

    print(f'\\n📊 Results saved to {OUTPUT_FILE}')
    print(f'Total: {len(results)} expressions submitted')

asyncio.run(main())