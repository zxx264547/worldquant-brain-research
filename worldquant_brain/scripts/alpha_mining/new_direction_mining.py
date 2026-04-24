#!/usr/bin/env python3
"""
Alpha Mining - 新方向测试
基于research_summary中的待测方向 + 论坛经验优化
"""

import asyncio
import json
import sys
import os
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')
sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')

from scripts.core import RetryableBrainClient
from scripts.core.api_client import BrainApiClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试配置 - 基于论坛经验优化
TEST_CONFIGS = [
    # ts_sum 测试
    {
        'name': 'ts_sum_25',
        'expr': 'ts_sum(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    {
        'name': 'ts_sum_20',
        'expr': 'ts_sum(winsorize(actual_eps_value_quarterly), 20)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    {
        'name': 'ts_sum_15',
        'expr': 'ts_sum(winsorize(actual_eps_value_quarterly), 15)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # truncation 变化
    {
        'name': 'trunc_035',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.35}
    },
    {
        'name': 'trunc_015',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.15}
    },
    # signed_power 变换 - 论坛经验：当Sharpe>0.6时有帮助
    # signed_power 1.3 可提升robs约0.02
    {
        'name': 'signed_power_0.5',
        'expr': 'signed_power(ts_mean(winsorize(actual_eps_value_quarterly), 25), 0.5)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    {
        'name': 'signed_power_0.8',
        'expr': 'signed_power(ts_mean(winsorize(actual_eps_value_quarterly), 25), 0.8)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    {
        'name': 'signed_power_1.3',
        'expr': 'signed_power(ts_mean(winsorize(actual_eps_value_quarterly), 25), 1.3)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # decay 变化
    {
        'name': 'decay_2',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 2, 'truncation': 0.25}
    },
    {
        'name': 'decay_5',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 5, 'truncation': 0.25}
    },
    # neutralization - 论坛经验：crowding中性化快速且效果好
    {
        'name': 'neutralize_market',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25, 'neutralization': 'market'}
    },
    {
        'name': 'neutralize_industry',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25, 'neutralization': 'industry'}
    },
    {
        'name': 'neutralize_sector',
        'expr': 'ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25, 'neutralization': 'sector'}
    },
    # ts_rank
    {
        'name': 'ts_rank_20',
        'expr': 'ts_rank(winsorize(actual_eps_value_quarterly), 20)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    {
        'name': 'ts_rank_10',
        'expr': 'ts_rank(winsorize(actual_eps_value_quarterly), 10)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # 多窗口组合
    {
        'name': 'multi_window',
        'expr': '0.5*ts_mean(winsorize(actual_eps_value_quarterly), 10) + 0.5*ts_mean(winsorize(actual_eps_value_quarterly), 25)',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # 行业相对化
    {
        'name': 'industry_relative',
        'expr': 'industry_relative(ts_mean(winsorize(actual_eps_value_quarterly), 25))',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
]

CACHE_FILE = '/home/zxx/.worldquant_brain/results_cache.json'
SESSION_FILE = '/home/zxx/.worldquant_brain/session.json'


def load_cache():
    """加载缓存结果"""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_cache(cache):
    """保存缓存"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


async def test_alpha(name, expr, settings):
    """测试单个Alpha"""
    cache = load_cache()

    # 检查缓存
    cache_key = f"{name}_{expr[:30]}"
    if cache_key in cache:
        result = cache[cache_key]
        logger.info(f"[CACHE] {name}: Sharpe={result.get('sharpe', 'N/A')}")
        return result

    # 测试
    client = BrainApiClient()
    try:
        await client.authenticate('', '')

        full_settings = {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': settings.get('delay', 1),
            'decay': settings.get('decay', 0),
            'truncation': settings.get('truncation', 0.25),
            'neutralization': settings.get('neutralization', 'NONE'),
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False
        }

        logger.info(f"Testing: {name}")
        logger.info(f"  Expr: {expr}")
        logger.info(f"  Settings: {full_settings}")

        sim_result = await client.create_simulation_with_retry(expr, full_settings)

        if sim_result.get('status') == 'ERROR':
            logger.error(f"  Error: {sim_result.get('message', 'Unknown')}")
            return None

        alpha_id = sim_result.get('alpha_id')
        logger.info(f"  Created: https://api.worldquantbrain.com/simulations/{alpha_id}")

        # 等待结果
        alpha_data = await client.get_alpha_with_retry(alpha_id, timeout=600)

        result = {
            'name': name,
            'expr': expr,
            'sharpe': alpha_data.get('sharpe'),
            'fitness': alpha_data.get('fitness'),
            'turnover': alpha_data.get('turnover'),
            'ppc': alpha_data.get('ppc'),
            'margin': alpha_data.get('margin'),
            'alpha_id': alpha_id
        }

        # 缓存
        cache[cache_key] = result
        save_cache(cache)

        logger.info(f"  Result: Sharpe={result['sharpe']}, Fitness={result['fitness']}, PPC={result['ppc']}")

        return result

    except Exception as e:
        logger.error(f"  Failed: {e}")
        return None


async def main():
    """主函数"""
    logger.info("="*60)
    logger.info("Alpha Mining - 新方向测试")
    logger.info(f"待测试: {len(TEST_CONFIGS)} 个组合")
    logger.info("="*60)

    # 检查API
    try:
        client = BrainApiClient()
        await client.authenticate('', '')
        logger.info("API is UP")
    except Exception as e:
        logger.error(f"API is DOWN: {e}")
        logger.error("等待API恢复后重试")
        return

    results = []
    for config in TEST_CONFIGS:
        result = await test_alpha(config['name'], config['expr'], config['settings'])
        if result:
            results.append(result)
        await asyncio.sleep(2)  # 避免限流

    # 输出总结
    logger.info("="*60)
    logger.info("测试结果总结")
    logger.info("="*60)

    if results:
        results.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
        for r in results:
            status = "✓" if r.get('sharpe', 0) >= 1.0 else "✗"
            logger.info(f"{status} {r['name']}: Sharpe={r.get('sharpe')}, Fitness={r.get('fitness')}")

        # 保存
        output = f"/home/zxx/worldQuant/worldquant_brain/data/outputs/new_direction_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"结果已保存: {output}")
    else:
        logger.info("没有成功的结果")


if __name__ == "__main__":
    asyncio.run(main())