#!/usr/bin/env python3
"""
Alpha Mining Engine - 统一Alpha挖掘引擎

整合批量挖掘、筛选、相关性分析功能
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .api_client import RetryableBrainClient
from .logging_config import setup_logging
from .exceptions import BrainAPIError
from .types import AlphaResultExtended, MiningConfig
from .templates import BASE_TEMPLATES, DEFAULT_SETTINGS

logger = setup_logging(__name__)


# 保持向后兼容的别名
DEFAULT_TEMPLATES = BASE_TEMPLATES


class AlphaMiningEngine:
    """统一Alpha挖掘引擎

    提供完整的Alpha挖掘流程：
    1. 认证 - authenticate()
    2. 挖掘 - mine()
    3. 筛选 - screen_and_rank()
    4. 保存 - save_results()
    """

    def __init__(self, credentials: Dict[str, str] = None, config: MiningConfig = None):
        self.credentials = credentials
        self.config = config or MiningConfig()
        self.client = RetryableBrainClient(
            credentials=credentials,
            poll_timeout=self.config.poll_timeout,
            poll_interval=self.config.poll_interval
        )
        self.results: List[AlphaResultExtended] = []

    async def authenticate(self, email: str = None, password: str = None):
        """认证"""
        await self.client.authenticate_with_retry(email or self.credentials.get('email'),
                                                  password or self.credentials.get('password'))

    async def get_fields(self, dataset: str) -> List[Dict]:
        """获取数据集字段"""
        return await self.client.get_datafields_with_retry(dataset)

    async def mine(
        self,
        datasets: List[str] = None,
        templates: List[Tuple[str, str]] = None,
        max_combinations: int = None,
        progress_callback=None
    ) -> List[AlphaResultExtended]:
        """执行完整挖掘流程"""

        datasets = datasets or self.config.datasets
        templates = templates or BASE_TEMPLATES
        max_combos = max_combinations or self.config.max_combinations

        logger.info(f"开始挖掘: 数据集={datasets}, 模板数={len(templates)}")

        all_combinations = []

        for dataset in datasets:
            fields = await self.get_fields(dataset)
            field_ids = [f['id'] for f in fields[:self.config.max_fields_per_dataset]]

            for field_id in field_ids:
                for template_expr, template_name in templates:
                    expr = template_expr.format(data=field_id)
                    all_combinations.append({
                        'dataset': dataset,
                        'field_id': field_id,
                        'expression': expr,
                        'template': template_name
                    })

                    if len(all_combinations) >= max_combos:
                        break
                if len(all_combinations) >= max_combos:
                    break
            if len(all_combinations) >= max_combos:
                break

        logger.info(f"共 {len(all_combinations)} 个组合待测试")

        for i, combo in enumerate(all_combinations):
            if progress_callback:
                progress_callback(i + 1, len(all_combinations))

            result = await self._evaluate_combo(combo)

            if result:
                self.results.append(result)
                checks = result.get_checks()
                status = '🎉' if all(checks.values()) else '✅'
                logger.info(
                    f"{status} [{i+1}/{len(all_combinations)}] "
                    f"{result.template}: Sharpe={result.sharpe:.2f}, "
                    f"M={result.margin:.4f}>T={result.turnover:.4f}"
                )

            await asyncio.sleep(0.5)

        return self.results

    async def _evaluate_combo(self, combo: dict) -> Optional[AlphaResultExtended]:
        """评估单个组合"""
        try:
            result = await self.client.create_simulation_with_retry(
                combo['expression'],
                DEFAULT_SETTINGS
            )

            if result.get('status') == 'ERROR':
                logger.warning(f"Simulation error: {combo['expression'][:50]}...")
                return None

            alpha_data = await self.client.get_alpha_with_retry(result['alpha_id'])

            return AlphaResultExtended(
                alpha_id=alpha_data['alpha_id'],
                expression=combo['expression'],
                field_id=combo['field_id'],
                template=combo['template'],
                dataset=combo['dataset'],
                sharpe=alpha_data['sharpe'],
                fitness=alpha_data['fitness'],
                turnover=alpha_data['turnover'],
                ppc=alpha_data['ppc'],
                margin=alpha_data['margin'],
            )

        except BrainAPIError as e:
            logger.error(f"API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def screen_and_rank(self, min_sharpe: float = 1.0) -> List[AlphaResultExtended]:
        """多轮筛选与排序"""
        filtered = [r for r in self.results if r.sharpe >= min_sharpe]
        filtered.sort(key=lambda x: x.sharpe, reverse=True)
        return filtered

    def get_submittable(self) -> List[AlphaResultExtended]:
        """获取满足PPA条件的Alpha"""
        return [r for r in self.results if r.is_submittable()]

    def get_candidates(self) -> List[AlphaResultExtended]:
        """获取候选Alpha"""
        candidates = [r for r in self.results if r.sharpe >= 1.0 and r.fitness > 0.5]
        candidates.sort(key=lambda x: x.sharpe, reverse=True)
        return candidates

    def save_results(self, output_path: str = "mining_results.json"):
        """保存结果"""
        output = {
            'total': len(self.results),
            'submittable': len(self.get_submittable()),
            'candidates': len(self.get_candidates()),
            'results': [r.to_dict() for r in self.results]
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存到: {path}")

    def print_summary(self):
        """打印摘要"""
        submittable = self.get_submittable()
        candidates = self.get_candidates()

        logger.info("=" * 60)
        logger.info("挖掘结果摘要")
        logger.info("=" * 60)
        logger.info(f"总测试数: {len(self.results)}")
        logger.info(f"候选Alpha (Sharpe>=1.0, Fitness>0.5): {len(candidates)}")
        logger.info(f"可提交Alpha (满足所有PPA条件): {len(submittable)}")

        if submittable:
            logger.info("\n🎉 可提交Alpha:")
            for r in submittable[:5]:
                logger.info(f"  {r.alpha_id}: Sharpe={r.sharpe:.2f}, "
                           f"M={r.margin:.4f}>T={r.turnover:.4f}")
                logger.info(f"    {r.expression[:60]}...")

        if candidates and not submittable:
            logger.info("\n候选Alpha (Top 5):")
            for r in candidates[:5]:
                logger.info(f"  {r.alpha_id}: Sharpe={r.sharpe:.2f}, "
                           f"M={r.margin:.4f}>T={r.turnover:.4f}, "
                           f"checks={r.get_checks()}")