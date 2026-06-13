#!/usr/bin/env python3
"""EUR region new fields exploration"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from worldquant_brain.engine import BacktestRunner
from worldquant_brain.engine.settings_manager import get_settings

async def test_field(expression, name, region='EUR', universe='TOPCS1600'):
    """Test a single field in EUR region"""
    settings = get_settings(
        region=region,
        universe=universe,
        decay=0,
        truncation=0.08,
        neutralization='NONE'
    )

    runner = BacktestRunner()
    result = await runner.run(expression, settings, name)

    return {
        'name': name,
        'expression': expression,
        'region': region,
        'universe': universe,
        'sharpe': result.get('sharpe', 0),
        'fitness': result.get('fitness', 0),
        'turnover': result.get('turnover', 0),
        'margin': result.get('margin', 0),
        'ppc': result.get('ppc', 0),
        'status': 'ok' if result.get('status') == 'ok' else 'error',
        'error': result.get('error', '')
    }

async def main():
    results = []

    # Test configurations
    tests = [
        # shortinterest3 new fields
        ("zscore(-ts_max(vec_max(si3_loan_utilization_ratio), 22))", "eur_s3_util"),
        ("zscore(-ts_max(vec_max(si3_mean_loan_rate), 22))", "eur_s3_meanloan"),
        ("zscore(-ts_max(vec_max(si3_max_loan_rate), 22))", "eur_s3_maxloan"),

        # risk60 fields (known working in USA)
        ("zscore(-ts_max(vec_max(rsk60_offer), 22))", "eur_rsk60_offer"),
        ("zscore(-ts_max(vec_max(rsk60_last), 22))", "eur_rsk60_last"),

        # analyst10 fields
        ("zscore(-ts_max(vec_max(anl10_pe_ratio), 22))", "eur_anl10_pe"),
        ("zscore(-ts_max(vec_max(anl10_earnings_yield), 22))", "eur_anl10_earn"),

        # market fields (baseline)
        ("zscore(-ts_max(vec_max(close), 22))", "eur_mkt_close"),
        ("rank(close)", "eur_mkt_close_rank"),
    ]

    print(f"Running {len(tests)} tests in EUR region...")
    print("-" * 60)

    for expr, name in tests:
        print(f"Testing {name}...", end=" ", flush=True)
        try:
            result = await test_field(expr, name)
            results.append(result)

            if result['status'] == 'ok':
                print(f"Sharpe={result['sharpe']:.3f}, Fitness={result['fitness']:.3f}")
            else:
                print(f"ERROR: {result['error'][:80]}")
        except Exception as e:
            print(f"EXCEPTION: {str(e)[:80]}")
            results.append({
                'name': name,
                'expression': expr,
                'status': 'error',
                'error': str(e)[:200]
            })

    print("=" * 60)
    print("EUR Region Exploration Results")
    print("=" * 60)

    valid_results = [r for r in results if r['status'] == 'ok']
    for r in sorted(valid_results, key=lambda x: -x.get('sharpe', 0)):
        submittable = r['sharpe'] >= 1.58 and r['fitness'] > 0.5
        flag = " [SUBMITTABLE]" if submittable else ""
        print(f"{r['name']:25s} Sharpe={r['sharpe']:.3f} Fitness={r['fitness']:.3f}{flag}")

    # Save to file
    output_file = Path('/tmp/multi_agent/eur_new_fields_results.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({
            'region': 'EUR',
            'universe': 'TOP1000',
            'timestamp': asyncio.get_event_loop().time(),
            'results': results
        }, f, indent=2)

    print(f"\nResults saved to {output_file}")

if __name__ == '__main__':
    asyncio.run(main())