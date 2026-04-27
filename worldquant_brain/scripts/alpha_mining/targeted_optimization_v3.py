#!/usr/bin/env python3
"""
Alpha Targeted Optimization - Best Alpha Settings Variation
Parent: ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)
Parent Sharpe: 1.17, Fitness: 2.06
Target: Sharpe >= 1.58

Generate 8 variants with VALID settings only:
Since "industry", "market", "sector" neutralizations are not valid,
we focus on truncation, decay, and universe variations.
1. Decay = 2
2. Decay = 4
3. Truncation = 0.01
4. Truncation = 0.08
5. Universe = TOP500
6. Delay = 2
7. decay=2 + trunc=0.01
8. decay=4 + trunc=0.01
"""

import asyncio
import json
import sys
import logging
from datetime import datetime

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')

from scripts.core.api_client import RetryableBrainClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = '/home/zxx/worldQuant/worldquant_brain/config/user_config.json'
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

credentials = config.get('credentials', {})

# Parent alpha info
PARENT_EXPR = 'ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)'
PARENT_ALPHA_ID = 'A1g1Z1Vw'
PARENT_SHARPE = 1.17
PARENT_FITNESS = 2.06

# 8 variants with VALID settings only
VARIANTS = [
    # 1. Decay = 2
    {
        'name': 'decay_2',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 2, 'truncation': 0.25, 'neutralization': 'NONE'}
    },
    # 2. Decay = 4
    {
        'name': 'decay_4',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 4, 'truncation': 0.25, 'neutralization': 'NONE'}
    },
    # 3. Truncation = 0.01
    {
        'name': 'trunc_001',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 0, 'truncation': 0.01, 'neutralization': 'NONE'}
    },
    # 4. Truncation = 0.08
    {
        'name': 'trunc_008',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 0, 'truncation': 0.08, 'neutralization': 'NONE'}
    },
    # 5. Universe = TOP500
    {
        'name': 'universe_top500',
        'settings': {'region': 'USA', 'universe': 'TOP500', 'delay': 1, 'decay': 0, 'truncation': 0.25, 'neutralization': 'NONE'}
    },
    # 6. Delay = 2
    {
        'name': 'delay_2',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 2, 'decay': 0, 'truncation': 0.25, 'neutralization': 'NONE'}
    },
    # 7. Decay = 2 + Truncation = 0.01
    {
        'name': 'decay2_trunc001',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 2, 'truncation': 0.01, 'neutralization': 'NONE'}
    },
    # 8. Decay = 4 + Truncation = 0.01
    {
        'name': 'decay4_trunc001',
        'settings': {'region': 'USA', 'universe': 'TOP3000', 'delay': 1, 'decay': 4, 'truncation': 0.01, 'neutralization': 'NONE'}
    },
]

OUTPUT_FILE = '/tmp/multi_agent/results.json'


def load_results():
    try:
        with open(OUTPUT_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"results": [], "last_updated": ""}


def save_results(data):
    data['last_updated'] = datetime.now().isoformat()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


async def test_variant(client, variant):
    name = variant['name']
    settings = variant['settings']

    logger.info(f"Testing: {name}")
    logger.info(f"  Settings: {settings}")

    full_settings = {
        'instrumentType': 'EQUITY',
        'region': settings.get('region', 'USA'),
        'universe': settings.get('universe', 'TOP3000'),
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

    try:
        sim_result = await client.create_simulation_with_retry(PARENT_EXPR, full_settings, timeout=600)

        if sim_result.get('status') == 'ERROR':
            logger.error(f"  Error: {sim_result.get('message', 'Unknown')}")
            return None

        alpha_id = sim_result.get('alpha_id')
        logger.info(f"  Alpha ID: {alpha_id}")

        alpha_data = await client.get_alpha_with_retry(alpha_id)

        sharpe = alpha_data.get('sharpe', 0)
        fitness = alpha_data.get('fitness', 0)
        ppc = alpha_data.get('ppc', 1)
        margin = alpha_data.get('margin', 0)
        turnover = alpha_data.get('turnover', 0)

        # Determine status
        if sharpe >= 1.58 and fitness > 0.5 and ppc < 0.5 and margin > turnover:
            status = 'ready_to_submit'
        elif sharpe > PARENT_SHARPE:
            status = 'improved'
        else:
            status = 'needs_optimization'

        result = {
            'parent_alpha_id': PARENT_ALPHA_ID,
            'alpha_id': alpha_id,
            'name': name,
            'expression': PARENT_EXPR,
            'sharpe': sharpe,
            'fitness': fitness,
            'turnover': turnover,
            'ppc': ppc,
            'margin': margin,
            'region': settings.get('region', 'USA'),
            'universe': settings.get('universe', 'TOP3000'),
            'delay': settings.get('delay', 1),
            'decay': settings.get('decay', 0),
            'truncation': settings.get('truncation', 0.25),
            'neutralization': settings.get('neutralization', 'NONE'),
            'optimization': name,
            'status': status
        }

        logger.info(f"  Result: Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, "
                   f"PPC={ppc:.2f}, Margin={margin:.4f}, Turnover={turnover:.4f}, Status={status}")

        return result

    except Exception as e:
        logger.error(f"  Failed: {e}")
        return None


async def main():
    logger.info("="*60)
    logger.info("Alpha Targeted Optimization - Settings Variation")
    logger.info(f"Parent: {PARENT_EXPR}")
    logger.info(f"Parent Sharpe: {PARENT_SHARPE}, Fitness: {PARENT_FITNESS}")
    logger.info("="*60)

    client = RetryableBrainClient(credentials)
    client.load_results_cache()

    try:
        await client.authenticate_with_retry()
        logger.info("Authentication: SUCCESS")
    except Exception as e:
        logger.error(f"Authentication FAILED: {e}")
        return

    existing_results = load_results()
    logger.info(f"Loaded {len(existing_results.get('results', []))} existing results")

    all_results = []
    for i, variant in enumerate(VARIANTS):
        logger.info("-"*40)
        logger.info(f"[{i+1}/8] Testing variant...")
        result = await test_variant(client, variant)
        if result:
            all_results.append(result)
            if result['sharpe'] >= 1.58:
                logger.info(f"*** TARGET REACHED! Sharpe={result['sharpe']} ***")
        await asyncio.sleep(3)  # Rate limiting

    existing_results['results'].extend(all_results)
    save_results(existing_results)

    # Summary
    logger.info("="*60)
    logger.info("Targeted Optimization Results Summary")
    logger.info("="*60)

    if all_results:
        all_results.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
        for r in all_results:
            sharpe = r.get('sharpe', 0)
            fitness = r.get('fitness', 0)
            ppc = r.get('ppc', 0)
            margin = r.get('margin', 0)
            turnover = r.get('turnover', 0)
            sharpe_ok = "Y" if sharpe >= 1.58 else "N"
            margin_ok = "Y" if margin > turnover else "N"
            fitness_ok = "Y" if fitness > 0.5 else "N"
            ppc_ok = "Y" if ppc < 0.5 else "N"

            logger.info(f"[{sharpe_ok}{margin_ok}{fitness_ok}{ppc_ok}] {r['name']}: "
                       f"Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, "
                       f"PPC={ppc:.2f}, Margin={margin:.4f}, Turnover={turnover:.4f}")

        # Check submission ready
        submission_ready = [r for r in all_results
                           if r['sharpe'] >= 1.58 and r['fitness'] > 0.5
                           and r['ppc'] < 0.5 and r['margin'] > r['turnover']]
        if submission_ready:
            logger.info("="*60)
            logger.info(f"SUBMISSION-READY ALPHAS: {len(submission_ready)}")
            for r in submission_ready:
                logger.info(f"  - {r['name']}: Sharpe={r['sharpe']}")
                logger.info(f"    Settings: region={r['region']}, universe={r['universe']}, "
                           f"decay={r['decay']}, neut={r['neutralization']}, trunc={r['truncation']}")
        else:
            best = all_results[0]
            logger.info(f"No submission-ready yet. Best: {best['name']} with Sharpe={best['sharpe']}")
            if best['sharpe'] > PARENT_SHARPE:
                logger.info("Progress made! Continuing optimization...")
            else:
                logger.info("No progress from parent. Need different strategy.")
    else:
        logger.info("No results from this batch")

    logger.info(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())