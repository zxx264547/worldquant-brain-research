#!/usr/bin/env python3
"""
Multi-Dataset & Multi-Factor Exploration
探索不同数据集和组合Alpha，寻找Sharpe>=1.5且Turnover>=0.01的Alpha
"""

import asyncio
import json
import sys
import os
import logging
import random
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain')
sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')

from scripts.core.api_client import BrainApiClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 目标数据集
TARGET_DATASETS = [
    'fundamental6',  # bookvalue_ps, cashflow, sales
    'pv87',          # 金融数据
    'analyst49',     # 分析师49
    'analyst69',     # 分析师69
    'analyst10',     # 分析师10
    'earnings6',     # 盈利6
    'earnings27',    # 盈利27
    'risk60',        # 风险60
    'risk62',        # 风险62
    'model109',      # 模型109
    'model127',      # 模型127
    'mdl136',        # ETF数据
    'pv1',           # 价格/成交量
    'wds',           # 全球市场数据
]

# 时间窗口
WINDOWS = [5, 22, 66, 120, 252]

# 最佳基础Alpha (Sharpe 1.17)
BASE_ALPHA = "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)"


class MultiFactorExplorer:
    def __init__(self):
        self.client = BrainApiClient()
        self.results = []
        self.dataset_fields = {}

    async def authenticate(self) -> bool:
        """认证"""
        import json
        config_path = Path(__file__).parent.parent / 'config' / 'user_config.json'
        with open(config_path) as f:
            config = json.load(f)
        creds = config['credentials']
        result = await self.client.authenticate(creds['email'], creds['password'])
        if result.get('status') == 'authenticated':
            logger.info("Authentication successful")
            return True
        logger.error(f"Authentication failed: {result}")
        return False

    async def get_dataset_fields(self, dataset_id: str) -> list:
        """获取数据集字段"""
        if dataset_id in self.dataset_fields:
            return self.dataset_fields[dataset_id]

        try:
            fields_result = await self.client.get_datafields(dataset_id=dataset_id)
            if fields_result and 'results' in fields_result:
                fields = fields_result['results']
                self.dataset_fields[dataset_id] = fields
                return fields
        except Exception as e:
            logger.warning(f"Failed to get fields for {dataset_id}: {e}")
        return []

    async def get_datasets(self) -> list:
        """获取所有数据集"""
        try:
            datasets = await self.client.get_datasets()
            if datasets and 'results' in datasets:
                return datasets['results']
        except Exception as e:
            logger.warning(f"Failed to get datasets: {e}")
        return []

    def make_settings(self, delay=1, decay=0, neutralization='NONE', truncation=0.08):
        """创建模拟设置"""
        return {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': delay,
            'decay': decay,
            'neutralization': neutralization,
            'truncation': truncation,
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False
        }

    async def test_expression(self, expr: str, settings: dict = None) -> dict:
        """测试表达式"""
        if settings is None:
            settings = self.make_settings()

        payload = {
            'type': 'REGULAR',
            'settings': settings,
            'regular': expr
        }

        try:
            resp = self.client.session.post(
                f'{self.client.base_url}/simulations',
                json=payload,
                timeout=30
            )

            if resp.status_code != 201:
                return {'status': 'error', 'error': f'HTTP {resp.status_code}'}

            location = resp.headers.get('Location', '')

            # 轮询等待结果
            for _ in range(100):
                await asyncio.sleep(3)
                r = self.client.session.get(location, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('status') == 'COMPLETED':
                        alpha_id = data.get('alpha')
                        if alpha_id:
                            ar = self.client.session.get(
                                f'{self.client.base_url}/alphas/{alpha_id}',
                                timeout=30
                            )
                            if ar.status_code == 200:
                                alpha = ar.json()
                                is_data = alpha.get('is', {})
                                os_data = alpha.get('os', {})

                                return {
                                    'status': 'completed',
                                    'alpha_id': alpha_id,
                                    'sharpe': is_data.get('sharpe', 0),
                                    'fitness': is_data.get('fitness', 0),
                                    'margin': is_data.get('margin', 0),
                                    'turnover': is_data.get('turnover', 0),
                                    'ppc': is_data.get('ppc', 0),
                                    'returns': is_data.get('returns', 0),
                                    'os_sharpe': os_data.get('sharpe', 0),
                                    'expression': expr
                                }
                    elif data.get('status') == 'ERROR':
                        return {'status': 'error', 'error': 'Simulation error'}

            return {'status': 'error', 'error': 'Timeout'}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def explore_dataset(self, dataset_id: str, max_fields: int = 5) -> list:
        """探索单个数据集的随机字段"""
        logger.info(f"Exploring dataset: {dataset_id}")

        fields = await self.get_dataset_fields(dataset_id)
        if not fields:
            logger.warning(f"No fields found for {dataset_id}")
            return []

        # 随机选择字段
        if len(fields) > max_fields:
            selected_fields = random.sample(fields, max_fields)
        else:
            selected_fields = fields

        results = []

        for field in selected_fields:
            field_id = field['id'] if isinstance(field, dict) else field
            logger.info(f"  Testing field: {field_id}")

            # 测试 rank(field)
            expr1 = f"rank({field_id})"
            result1 = await self.test_expression(expr1)
            if result1['status'] == 'completed':
                result1['dataset'] = dataset_id
                result1['field'] = field_id
                result1['template'] = 'rank'
                results.append(result1)
                logger.info(f"    rank: Sharpe={result1.get('sharpe', 0):.3f}, T={result1.get('turnover', 0):.4f}")

            await asyncio.sleep(0.5)

            # 测试 ts_mean(field, 22)
            expr2 = f"ts_mean({field_id}, 22)"
            result2 = await self.test_expression(expr2)
            if result2['status'] == 'completed':
                result2['dataset'] = dataset_id
                result2['field'] = field_id
                result2['template'] = 'ts_mean_22'
                results.append(result2)
                logger.info(f"    ts_mean_22: Sharpe={result2.get('sharpe', 0):.3f}, T={result2.get('turnover', 0):.4f}")

            await asyncio.sleep(0.5)

        return results

    async def test_multi_factor_combinations(self) -> list:
        """测试多因子组合Alpha"""
        logger.info("Testing multi-factor combinations...")

        results = []

        # Alpha1: 基础Alpha (Sharpe 1.17)
        alpha1 = BASE_ALPHA

        # Alpha2: ts_mean(close, 22)
        alpha2 = "ts_mean(close, 22)"

        # Alpha3: ts_mean(volume, 22)
        alpha3 = "ts_mean(volume, 22)"

        # Alpha4: ts_mean(actual_eps_value_quarterly, 66)
        alpha4 = "ts_mean(actual_eps_value_quarterly, 66)"

        # 组合方式1: ts_sum(alpha1, alpha2)
        combos = [
            ("ts_sum(" + alpha1 + ", " + alpha2 + ")", "sum_a1_a2"),
            ("ts_sum(" + alpha1 + ", " + alpha3 + ")", "sum_a1_a3"),
            (alpha1 + " + " + alpha2, "add_a1_a2"),
            (alpha1 + " + " + alpha3, "add_a1_a3"),
            ("ts_mean(" + alpha1 + ", 5) + " + alpha2, "mean_a1_5_add_a2"),
            ("rank(" + alpha1 + ") + rank(" + alpha2 + ")", "rank_sum_a1_a2"),
            ("rank(" + alpha1 + ") + rank(" + alpha3 + ")", "rank_sum_a1_a3"),
            (alpha1 + " * " + alpha2, "mult_a1_a2"),
            ("ts_sum(" + alpha1 + ", " + alpha4 + ")", "sum_a1_a4"),
        ]

        for expr, name in combos:
            logger.info(f"  Testing combo: {name}")
            result = await self.test_expression(expr)
            if result['status'] == 'completed':
                result['combo_name'] = name
                results.append(result)
                logger.info(f"    Sharpe={result.get('sharpe', 0):.3f}, T={result.get('turnover', 0):.4f}")

            await asyncio.sleep(1)

        return results

    async def test_cross_field_factors(self) -> list:
        """测试跨字段因子"""
        logger.info("Testing cross-field factors...")

        results = []

        cross_field_exprs = [
            ("ts_sum(actual_eps_value_quarterly, 66) + ts_sum(actual_dividend_value_quarterly, 66)", "eps_div_sum_66"),
            ("ts_mean(actual_eps_value_quarterly, 22) * ts_mean(volume, 22)", "eps_vol_mult_22"),
            ("rank(actual_eps_value_quarterly) + rank(volume)", "eps_vol_rank_add"),
            ("ts_sum(actual_eps_value_quarterly, 22) - ts_delta(actual_eps_value_quarterly, 22)", "eps_sum_delta_22"),
            ("rank(ts_mean(actual_eps_value_quarterly, 22)) + rank(ts_mean(volume, 22))", "rank_mean_eps_vol"),
            ("ts_mean(actual_sales_value_quarterly, 22) * ts_mean(actual_eps_value_quarterly, 22)", "sales_eps_mult"),
            ("rank(actual_cashflow_value_quarterly) + rank(actual_eps_value_quarterly)", "cf_eps_rank_add"),
            ("ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3) + ts_mean(volume, 22)", "base_eps_vol_add"),
        ]

        for expr, name in cross_field_exprs:
            logger.info(f"  Testing: {name}")
            result = await self.test_expression(expr)
            if result['status'] == 'completed':
                result['cross_field_name'] = name
                results.append(result)
                logger.info(f"    Sharpe={result.get('sharpe', 0):.3f}, T={result.get('turnover', 0):.4f}")

            await asyncio.sleep(1)

        return results

    async def run_exploration(self):
        """运行完整探索流程"""
        output_dir = Path('/home/zxx/worldQuant/worldquant_brain/data/outputs')
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"multi_exploration_{timestamp}.json"

        all_results = {
            'dataset_exploration': [],
            'multi_factor_combos': [],
            'cross_field_factors': [],
            'submission_ready': []
        }

        # Step 1: 认证
        logger.info("[1/4] Authenticating...")
        if not await self.authenticate():
            logger.error("Authentication failed, exiting")
            return

        # Step 2: 获取数据集列表
        logger.info("[2/4] Getting dataset list...")
        datasets = await self.get_datasets()
        ds_dict = {ds['id']: ds for ds in datasets}
        logger.info(f"Found {len(datasets)} datasets")

        # Step 3: 探索目标数据集
        logger.info("[3/4] Exploring target datasets...")
        for ds_id in TARGET_DATASETS:
            if ds_id in ds_dict:
                results = await self.explore_dataset(ds_id, max_fields=5)
                all_results['dataset_exploration'].extend(results)

                # 检查是否有提交就绪的Alpha
                for r in results:
                    if r.get('sharpe', 0) >= 1.58 and r.get('margin', 0) > r.get('turnover', 0):
                        all_results['submission_ready'].append(r)

                await asyncio.sleep(2)
            else:
                logger.warning(f"Dataset {ds_id} not found")

        # Step 4: 测试多因子组合
        logger.info("[4/4] Testing multi-factor combinations...")
        combo_results = await self.test_multi_factor_combinations()
        all_results['multi_factor_combos'] = combo_results

        for r in combo_results:
            if r.get('sharpe', 0) >= 1.58 and r.get('margin', 0) > r.get('turnover', 0):
                all_results['submission_ready'].append(r)

        # Step 5: 测试跨字段因子
        logger.info("[5/5] Testing cross-field factors...")
        cross_results = await self.test_cross_field_factors()
        all_results['cross_field_factors'] = cross_results

        for r in cross_results:
            if r.get('sharpe', 0) >= 1.58 and r.get('margin', 0) > r.get('turnover', 0):
                all_results['submission_ready'].append(r)

        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info(f"Exploration complete!")
        logger.info(f"Results saved to: {output_file}")
        logger.info(f"Total dataset results: {len(all_results['dataset_exploration'])}")
        logger.info(f"Multi-factor combos: {len(all_results['multi_factor_combos'])}")
        logger.info(f"Cross-field factors: {len(all_results['cross_field_factors'])}")
        logger.info(f"Submission ready: {len(all_results['submission_ready'])}")

        # 打印Top 10
        if all_results['dataset_exploration']:
            logger.info("\nTop 10 Dataset Exploration Results:")
            sorted_results = sorted(
                all_results['dataset_exploration'],
                key=lambda x: x.get('sharpe', 0),
                reverse=True
            )
            for r in sorted_results[:10]:
                logger.info(f"  {r.get('dataset')}/{r.get('field')}/{r.get('template')}: "
                           f"Sharpe={r.get('sharpe', 0):.3f}, T={r.get('turnover', 0):.4f}, "
                           f"M={r.get('margin', 0):.4f}")

        if all_results['multi_factor_combos']:
            logger.info("\nMulti-factor Combo Results:")
            for r in all_results['multi_factor_combos']:
                logger.info(f"  {r.get('combo_name')}: Sharpe={r.get('sharpe', 0):.3f}, "
                          f"T={r.get('turnover', 0):.4f}, M={r.get('margin', 0):.4f}")

        if all_results['cross_field_factors']:
            logger.info("\nCross-field Factor Results:")
            for r in all_results['cross_field_factors']:
                logger.info(f"  {r.get('cross_field_name')}: Sharpe={r.get('sharpe', 0):.3f}, "
                          f"T={r.get('turnover', 0):.4f}, M={r.get('margin', 0):.4f}")

        return all_results


async def main():
    explorer = MultiFactorExplorer()
    await explorer.run_exploration()


if __name__ == "__main__":
    asyncio.run(main())