#!/usr/bin/env python3
"""EUR Alpha with window=66 - addressing LOW_SUB_UNIVERSE_SHARPE"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from worldquant_brain.engine import BacktestRunner
from worldquant_brain.engine.settings_manager import get_settings

OUTPUT_FILE = Path('/tmp/multi_agent/eur_long_window_results.json')


async def test_alpha(expression, name, region='EUR', universe='TOPCS1600',
                     decay=0, truncation=0.08, neutralization='SECTOR'):
    """Test a single alpha configuration"""
    settings = get_settings(
        region=region,
        universe=universe,
        decay=decay,
        truncation=truncation,
        neutralization=neutralization
    )

    runner = BacktestRunner()
    result = await runner.run(expression, settings, name)

    return {
        'name': name,
        'expression': expression,
        'region': region,
        'universe': universe,
        'decay': decay,
        'truncation': truncation,
        'neutralization': neutralization,
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

    # Test configurations with window=66
    # Format: (expression, name, decay, truncation, neutralization)
    tests = [
        # === S3单字段长窗口 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_win66_z", 0, 0.08, "SECTOR"),
        ("zscore(-ts_max(vec_max(mean_loan_rate), 66))", "s3_mean_win66_z", 0, 0.08, "SECTOR"),
        ("zscore(-ts_max(vec_max(max_loan_rate), 66))", "s3_max_win66_z", 0, 0.08, "SECTOR"),
        ("zscore(-ts_max(vec_max(loan_utilization_ratio), 66))", "s3_util_win66_z", 0, 0.08, "SECTOR"),

        # === S3 + truncation调优 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_w66_t001", 0, 0.01, "SECTOR"),
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_w66_t005", 0, 0.05, "SECTOR"),

        # === S3 + decay调优 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_w66_d2", 2, 0.08, "SECTOR"),
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_w66_d4", 4, 0.08, "SECTOR"),

        # === INDUSTRY中性化 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_w66_ind", 0, 0.08, "INDUSTRY"),
        ("zscore(-ts_max(vec_max(mean_loan_rate), 66))", "s3_mean_w66_ind", 0, 0.08, "INDUSTRY"),

        # === USA region with TOP3000 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_usa3k", 0, 0.08, "SECTOR"),
        ("zscore(-ts_max(vec_max(mean_loan_rate), 66))", "s3_mean_usa3k", 0, 0.08, "SECTOR"),

        # === 跨字段组合 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66)) + zscore(-ts_max(vec_max(mean_loan_rate), 66))",
         "s3_min_mean_combo", 0, 0.08, "SECTOR"),

        # === 无中性化基准 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 66))", "s3_min_win66_none", 0, 0.08, "NONE"),

        # === 66 vs 22 对比基准 ===
        ("zscore(-ts_max(vec_max(min_loan_rate), 22))", "s3_min_win22_z", 0, 0.08, "SECTOR"),
    ]

    print(f"Running {len(tests)} EUR window=66 tests...")
    print("=" * 70)

    for i, test in enumerate(tests):
        if len(test) == 5:
            expr, name, decay, trunc, neut = test
        else:
            expr, name = test[0], test[1]
            decay, trunc, neut = 0, 0.08, "SECTOR"

        print(f"[{i+1}/{len(tests)}] {name}...", end=" ", flush=True)
        try:
            result = await test_alpha(expr, name,
                                     decay=decay,
                                     truncation=trunc,
                                     neutralization=neut)
            results.append(result)

            if result['status'] == 'ok':
                sub = " [SUBMITTABLE]" if result['sharpe'] >= 1.58 and result['fitness'] > 0.5 else ""
                print(f"Sharpe={result['sharpe']:.3f} Fitness={result['fitness']:.3f}{sub}")
            else:
                print(f"ERROR: {result['error'][:60]}")
        except Exception as e:
            print(f"EXCEPTION: {str(e)[:60]}")
            results.append({
                'name': name, 'expression': expr, 'status': 'error', 'error': str(e)[:200]
            })

    print("=" * 70)
    print("EUR Window=66 Results Summary")
    print("=" * 70)

    valid = [r for r in results if r['status'] == 'ok']
    for r in sorted(valid, key=lambda x: -x.get('sharpe', 0)):
        sub = " [SUBMITTABLE]" if r['sharpe'] >= 1.58 and r['fitness'] > 0.5 else ""
        neut = r.get('neutralization', 'SECTOR')
        trunc = r.get('truncation', 0.08)
        decay = r.get('decay', 0)
        print(f"{r['name']:25s} S={r['sharpe']:.3f} F={r['fitness']:.3f} "
              f"T={r['turnover']:.1f} N={neut:8s} d={decay} tr={trunc:.2f}{sub}")

    # Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({'results': results, 'timestamp': asyncio.get_event_loop().time()}, f, indent=2)

    print(f"\nResults saved to {OUTPUT_FILE}")

    return results


if __name__ == '__main__':
    asyncio.run(main())
