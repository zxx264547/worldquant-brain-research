#!/usr/bin/env python3
"""
New Dataset Exploration Script - 探索 min_loan_rate 以外的新数据集
修复：使用正确的 SimulationData/SimulationSettings API
"""

import asyncio
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
from platform_functions import BrainApiClient, SimulationData, SimulationSettings

RESULTS_FILE = Path('/home/zxx/worldQuant/worldquant_brain/state/_runtime/new_dataset_explore.json')
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

# 候选数据集和字段
CANDIDATES = [
    # analyst4 fields
    {'dataset': 'analyst4', 'field': 'anl47_totalrawsignal', 'type': 'VECTOR',
     'pattern': 'zscore(ts_mean({field}, 22))'},
    {'dataset': 'analyst4', 'field': 'anl47_indicator', 'type': 'SCALAR',
     'pattern': 'zscore(ts_mean({field}, 22))'},
    {'dataset': 'analyst4', 'field': 'anl47_rawexperts', 'type': 'SCALAR',
     'pattern': 'zscore(ts_mean({field}, 22))'},
    {'dataset': 'analyst4', 'field': 'anl47_epsvalue_af2', 'type': 'FUNDAMENTAL',
     'pattern': 'rank(zscore(ts_mean({field}, 66)))'},

    # analyst10 fields
    {'dataset': 'analyst10', 'field': 'anl10_eps_value_ttm', 'type': 'FUNDAMENTAL',
     'pattern': 'rank(zscore(ts_mean({field}, 66)))'},
    {'dataset': 'analyst10', 'field': 'anl10_epsrevise_ratio_to_close_fy2', 'type': 'FUNDAMENTAL',
     'pattern': 'rank(zscore(ts_mean({field}, 22)))'},

    # analyst14 fields
    {'dataset': 'analyst14', 'field': 'anl14_eps_value_ttm', 'type': 'FUNDAMENTAL',
     'pattern': 'rank(zscore(ts_mean({field}, 66)))'},

    # mdl136 fields
    {'dataset': 'mdl136', 'field': 'mdl136_bid_ask_spread', 'type': 'SCALAR',
     'pattern': 'zscore(ts_mean({field}, 5))'},

    # pv87 fields
    {'dataset': 'pv87', 'field': 'pv87_ebit', 'type': 'FUNDAMENTAL',
     'pattern': 'rank(zscore(ts_mean({field}, 120)))'},
]


class NewDatasetExplorer:
    def __init__(self):
        self.client = BrainApiClient()
        self.results = []
        self._pending_sims = {}  # sim_id -> candidate info
        self._authenticated = False

    def _clear_proxy(self):
        """清除代理设置"""
        for k in list(os.environ.keys()):
            if 'proxy' in k.lower():
                os.environ.pop(k, None)

    async def authenticate(self):
        """认证"""
        self._clear_proxy()
        # 凭据从本地配置加载（禁止硬编码；见 config/user_config.json）
        import json as _json
        cfg_path = Path('/home/zxx/worldQuant/worldquant_brain/config/user_config.json')
        creds = {}
        if cfg_path.exists():
            creds = _json.loads(cfg_path.read_text()).get('credentials', {})
        email = os.environ.get('WQ_BRAIN_EMAIL', creds.get('email', ''))
        password = os.environ.get('WQ_BRAIN_PASSWORD', creds.get('password', ''))
        if not email or not password:
            print('[AUTH] 缺少凭据：请配置 config/user_config.json 或环境变量')
            self._authenticated = False
            return
        # Use the SAME client instance - authenticate on the client
        result = await self.client.authenticate(email=email, password=password)
        print(f"[AUTH] {result.get('message', result)}")
        self._authenticated = True

    async def create_sim(self, expression: str, candidate: dict) -> dict:
        """创建模拟"""
        self._clear_proxy()

        sim_settings = SimulationSettings(
            region='USA',
            universe='TOP3000',
            delay=1,
            decay=0,
            neutralization='INDUSTRY',
            truncation=0.03,
        )
        sim_data = SimulationData(
            type='REGULAR',
            settings=sim_settings,
            regular=expression,
        )

        sim = await self.client.create_simulation(sim_data)
        sim_id = sim.get('simulationId', 'unknown')
        print(f"  [SIM] {candidate['dataset']}.{candidate['field'][:20]}: {sim_id}")

        self._pending_sims[sim_id] = candidate
        return sim_id

    async def check_results(self) -> list:
        """检查所有待处理模拟的结果"""
        results = []
        self._clear_proxy()

        # 获取alphas
        try:
            alphas_data = await self.client.get_user_alphas()
            alpha_list = alphas_data.get('data', alphas_data.get('alphas', []))

            if not alpha_list:
                print("  [WARN] No alphas found")
                return results

            print(f"  Found {len(alpha_list)} alphas")

            # 按时间排序，检查最新的一些
            sorted_alphas = sorted(alpha_list, key=lambda x: x.get('createdAt', ''), reverse=True)

            for sim_id, candidate in list(self._pending_sims.items()):
                found = False
                for alpha in sorted_alphas[:10]:  # 检查最新的10个
                    if sim_id in str(alpha.get('simulationId', '')):
                        results.append({
                            'status': 'ok',
                            'dataset': candidate['dataset'],
                            'field': candidate['field'],
                            'expression': candidate['pattern'].format(field=candidate['field']),
                            'alpha_id': alpha.get('alphaId'),
                            'sharpe': alpha.get('sharpe', 0),
                            'fitness': alpha.get('fitness', 0),
                            'ppc': alpha.get('ppc', 0),
                            'turnover': alpha.get('turnover', 0),
                            'margin': alpha.get('margin', 0),
                            'returns': alpha.get('returns', 0),
                            'timestamp': datetime.now().isoformat(),
                        })
                        found = True
                        print(f"  [OK] {candidate['field']}: Sharpe={alpha.get('sharpe', 0):.2f}")
                        del self._pending_sims[sim_id]
                        break

                if not found:
                    # 检查是否失败
                    for alpha in sorted_alphas[:10]:
                        if sim_id in str(alpha.get('simulationId', '')):
                            if alpha.get('status') == 'FAILED':
                                results.append({
                                    'status': 'failed',
                                    'dataset': candidate['dataset'],
                                    'field': candidate['field'],
                                    'expression': candidate['pattern'].format(field=candidate['field']),
                                    'error': 'Simulation failed',
                                    'timestamp': datetime.now().isoformat(),
                                })
                                del self._pending_sims[sim_id]
                                print(f"  [FAIL] {candidate['field']}")
                                found = True
                                break

        except Exception as e:
            print(f"  [ERROR] {e}")

        return results

    async def run(self):
        """运行探索"""
        print("=" * 60)
        print("NEW DATASET EXPLORATION")
        print("=" * 60)

        await self.authenticate()

        # 批量提交所有模拟
        print("\n--- Submitting Simulations ---")
        for candidate in CANDIDATES:
            expression = candidate['pattern'].format(field=candidate['field'])
            await self.create_sim(expression, candidate)
            await asyncio.sleep(5)  # 避免限流

        # 等待模拟完成 (轮询)
        print("\n--- Waiting for Results ---")
        max_wait = 15 * 60  # 15分钟
        start = time.time()
        poll_count = 0

        while self._pending_sims and time.time() - start < max_wait:
            await asyncio.sleep(30)
            poll_count += 1
            print(f"\n[POLL {poll_count}] Checking results... ({len(self._pending_sims)} pending)")

            results = await self.check_results()
            if results:
                self.results.extend(results)
                # 保存中间结果
                with open(RESULTS_FILE, 'w') as f:
                    json.dump(self.results, f, indent=2)

            # 如果等待超过5分钟还没结果，可能是API问题
            if poll_count >= 10 and self._pending_sims:
                print(f"[WARN] Still pending after 5 minutes: {list(self._pending_sims.keys())}")

        # 最终检查
        print("\n--- Final Check ---")
        final_results = await self.check_results()
        self.results.extend(final_results)

        # 总结
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        successful = [r for r in self.results if r.get('status') == 'ok' and r.get('sharpe', 0) > 0]
        successful.sort(key=lambda x: x.get('sharpe', 0), reverse=True)

        print(f"\nTotal tested: {len(self.results)}")
        print(f"Successful (Sharpe > 0): {len(successful)}")

        if successful:
            print("\nTop Results:")
            for r in successful[:10]:
                print(f"  {r['dataset']}.{r['field'][:25]:25s} Sharpe={r['sharpe']:.2f} Fitness={r['fitness']:.2f}")

            # 保存最终结果
            with open(RESULTS_FILE, 'w') as f:
                json.dump({
                    'results': self.results,
                    'summary': {
                        'total_tested': len(self.results),
                        'successful': len(successful),
                        'best_sharpe': successful[0]['sharpe'] if successful else 0,
                        'best_field': successful[0]['field'] if successful else None,
                    }
                }, f, indent=2)
        else:
            print("\nNo successful alphas found. Try different fields.")

        print(f"\nResults saved to {RESULTS_FILE}")
        return self.results


async def main():
    explorer = NewDatasetExplorer()
    await explorer.run()


if __name__ == '__main__':
    asyncio.run(main())