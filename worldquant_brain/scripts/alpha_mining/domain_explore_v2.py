#!/usr/bin/env python3
"""
Alpha Deep Exploration V2 - Focus on USA with Alternative Datasets
Using USA/TOP3000 which is confirmed working
Target: Break through Sharpe 1.17 ceiling by finding new signal sources
"""

import asyncio
import json
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')

from scripts.core.api_client import RetryableBrainClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = '/home/zxx/worldQuant/worldquant_brain/config/user_config.json'
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

credentials = config.get('credentials', {})

# 8 variants - focusing on USA with different datasets and expressions
# Each should have different characteristics from the EPS-based alphas
TEST_VARIANTS = [
    # Variant 1: analyst10 EPS consensus with signed_power (like our best alpha pattern)
    {
        'name': 'anl10_signedpower_eps252',
        'dataset': 'analyst10',
        'field': 'anl10_cpsfq1_consensus_2351',
        'expr': 'signed_power(ts_sum(anl10_cpsfq1_consensus_2351, 252), 1.05)',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 2: fundamental6 book value per share with ts_sum pattern
    {
        'name': 'fund6_bvps_sum252',
        'dataset': 'fundamental6',
        'field': 'bookvalue_ps',
        'expr': 'ts_sum(bookvalue_ps, 252) / 252',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 3: pv87 estimate change ratio with signed_power
    {
        'name': 'pv87_signedpower_chngratio252',
        'dataset': 'pv87',
        'field': 'pv87_2_bps_af_matrix_all_chngratio_mean',
        'expr': 'signed_power(ts_sum(pv87_2_bps_af_matrix_all_chngratio_mean, 252), 1.05)',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 4: analyst49 growth rate
    {
        'name': 'anl49_growthrate_sum252',
        'dataset': 'analyst49',
        'field': 'anl49_35estd35yrgrowthrateearningspershare',
        'expr': 'ts_sum(anl49_35estd35yrgrowthrateearningspershare, 252) / 252',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 5: analyst4 cashflow per share (alternative to EPS)
    {
        'name': 'anl4_cashflow_sum252',
        'dataset': 'analyst4',
        'field': 'actual_cashflow_per_share_value_quarterly',
        'expr': 'ts_sum(actual_cashflow_per_share_value_quarterly, 252) / 252',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 6: fundamental6 with signed_power on cashflow
    {
        'name': 'fund6_cashflow_signedpower252',
        'dataset': 'fundamental6',
        'field': 'cashflow',
        'expr': 'signed_power(ts_sum(cashflow, 252), 1.05)',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 7: earnings6 eps change percentage
    {
        'name': 'ern6_epschange_sum252',
        'dataset': 'earnings6',
        'field': 'eps_change_percentage_value',
        'expr': 'ts_sum(eps_change_percentage_value, 252) / 252',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
    # Variant 8: model dataset (Starmine valuation) - using known model field
    {
        'name': 'mfm_model_sum252',
        'dataset': 'mfm_model_output',
        'field': 'mfm_1_return_1m',
        'expr': 'ts_sum(mfm_1_return_1m, 252) / 252',
        'region': 'USA',
        'universe': 'TOP3000',
        'settings': {'delay': 1, 'decay': 0, 'truncation': 0.25}
    },
]

OUTPUT_FILE = '/tmp/multi_agent/results.json'
STATE_FILE = '/tmp/multi_agent/domain_explore_v2_state.json'
DEEP_RESULTS_FILE = '/tmp/multi_agent/domain_exploration_v2_results.json'


def load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"completed": [], "failed": []}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


async def test_variant(client, variant) -> Optional[Dict[str, Any]]:
    name = variant['name']
    expr = variant['expr']
    region = variant['region']
    universe = variant['universe']
    dataset = variant['dataset']
    field = variant['field']
    settings = variant['settings']

    logger.info(f"Testing: {name}")
    logger.info(f"  Dataset: {dataset}, Field: {field[:40] if field else 'N/A'}")
    logger.info(f"  Region: {region}, Universe: {universe}")

    full_settings = {
        'instrumentType': 'EQUITY',
        'region': region,
        'universe': universe,
        'delay': settings.get('delay', 1),
        'decay': settings.get('decay', 0),
        'truncation': settings.get('truncation', 0.25),
        'neutralization': 'NONE',
        'pasteurization': 'ON',
        'unitHandling': 'VERIFY',
        'nanHandling': 'OFF',
        'language': 'FASTEXPR',
        'visualization': False
    }

    try:
        sim_result = await client.create_simulation_with_retry(expr, full_settings, timeout=600)

        if sim_result.get('status') == 'ERROR':
            logger.error(f"  Error: {sim_result.get('message', 'Unknown')}")
            return None

        alpha_id = sim_result.get('alpha_id')
        logger.info(f"  Alpha ID: {alpha_id}")

        alpha_data = await client.get_alpha_with_retry(alpha_id)

        sharpe = alpha_data.get('sharpe', 0)
        fitness = alpha_data.get('fitness', 0)
        turnover = alpha_data.get('turnover', 0)
        ppc = alpha_data.get('ppc', 1)
        margin = alpha_data.get('margin', 0)

        result = {
            'parent_alpha_id': 'A1g1Z1Vw',  # Best current alpha
            'alpha_id': alpha_id,
            'name': name,
            'expression': expr,
            'dataset': dataset,
            'field': field,
            'sharpe': sharpe,
            'fitness': fitness,
            'turnover': turnover,
            'ppc': ppc,
            'margin': margin,
            'region': region,
            'universe': universe,
            'optimization': f'domain_explore_v2_{name}',
            'status': 'ready_to_submit' if sharpe >= 1.58 and fitness > 0.5 and ppc < 0.5 and margin > turnover else 'needs_optimization'
        }

        logger.info(f"  Result: Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, PPC={ppc:.2f}, Margin={margin:.4f}, Turnover={turnover:.4f}")

        return result

    except Exception as e:
        logger.error(f"  Failed: {e}")
        return None


async def main():
    logger.info("="*60)
    logger.info("Alpha Deep Exploration V2 - USA Dataset Switching")
    logger.info(f"Testing {len(TEST_VARIANTS)} variants")
    logger.info("Target: Sharpe >= 1.58 (break through 1.17 ceiling)")
    logger.info("="*60)

    client = RetryableBrainClient(credentials)
    client.load_results_cache()

    try:
        await client.authenticate_with_retry()
        logger.info("Authentication: SUCCESS")
    except Exception as e:
        logger.error(f"Authentication FAILED: {e}")
        return

    state = load_state()
    completed = set(state.get('completed', []))
    failed = set(state.get('failed', []))

    all_results = []
    for i, variant in enumerate(TEST_VARIANTS):
        name = variant['name']
        if name in completed:
            logger.info(f"[{i+1}/{len(TEST_VARIANTS)}] SKIPPING {name} (already completed)")
            continue
        if name in failed:
            logger.info(f"[{i+1}/{len(TEST_VARIANTS)}] SKIPPING {name} (previously failed)")
            continue

        logger.info("-"*40)
        logger.info(f"[{i+1}/{len(TEST_VARIANTS)}] {name}")

        result = await test_variant(client, variant)

        if result:
            all_results.append(result)
            completed.add(name)
            state['completed'] = list(completed)
            save_state(state)

            if result['sharpe'] >= 1.58:
                logger.info(f"*** TARGET REACHED! Sharpe={result['sharpe']} ***")
        else:
            failed.add(name)
            state['failed'] = list(failed)
            save_state(state)

        await asyncio.sleep(8)  # Rate limiting - longer delay

    # Save deep exploration results
    deep_results = {
        'base_alpha': {
            'alpha_id': 'A1g1Z1Vw',
            'expression': 'ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)',
            'sharpe': 1.17
        },
        'variants': all_results,
        'best_sharpe': max([r['sharpe'] for r in all_results], default=0),
        'target_reached': any(r['sharpe'] >= 1.58 for r in all_results),
        'timestamp': datetime.now().isoformat()
    }
    with open(DEEP_RESULTS_FILE, 'w') as f:
        json.dump(deep_results, f, indent=2)

    # Summary
    logger.info("="*60)
    logger.info("Domain Exploration V2 Results Summary")
    logger.info("="*60)

    if all_results:
        all_results.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
        for r in all_results:
            sharpe = r.get('sharpe', 0)
            fitness = r.get('fitness', 0)
            ppc = r.get('ppc', 0)
            margin = r.get('margin', 0)
            turnover = r.get('turnover', 0)
            sharpe_ok = "✓" if sharpe >= 1.58 else "✗"
            margin_ok = "✓" if margin > turnover else "✗"
            fitness_ok = "✓" if fitness > 0.5 else "✗"
            ppc_ok = "✓" if ppc < 0.5 else "✗"

            logger.info(f"{sharpe_ok}{margin_ok}{fitness_ok}{ppc_ok} {r['name']}: "
                       f"Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, "
                       f"PPC={ppc:.2f}, Margin={margin:.4f}, Turnover={turnover:.4f}")

        submission_ready = [r for r in all_results
                         if r['sharpe'] >= 1.58 and r['fitness'] > 0.5
                         and r['ppc'] < 0.5 and r['margin'] > r['turnover']]
        if submission_ready:
            logger.info("="*60)
            logger.info(f"SUBMISSION-READY ALPHAS: {len(submission_ready)}")
            for r in submission_ready:
                logger.info(f"  - {r['name']}: Sharpe={r['sharpe']}, Expression={r['expression'][:60]}...")
        else:
            best = all_results[0]
            logger.info(f"No submission-ready yet. Best: {best['name']} with Sharpe={best['sharpe']}")
    else:
        logger.info("No results from this batch")

    logger.info(f"\nResults saved to: {DEEP_RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())