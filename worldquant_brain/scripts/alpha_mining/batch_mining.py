#!/usr/bin/env python3
"""
Alpha Batch Mining - 批量Alpha挖掘脚本
基于社区经验优化，支持并发控制
"""

import json
import time
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from ..core import RetryableBrainClient, setup_logging, BrainAPIError
from ..core.templates import DEFAULT_SETTINGS
from ..core.types import AlphaResultExtended as AlphaResult

logger = setup_logging(__name__)


CONFIG = {
    "region": "USA",
    "universe": "TOP3000",
    "instrument_type": "EQUITY",

    # 筛选阈值
    "min_sharpe_step1": 0.7,
    "min_sharpe_step2": 0.7,
    "min_sharpe_step3": 1.0,
    "min_fitness": 0.5,
    "max_turnover": 0.7,

    # 提交条件
    "submit_sharpe": 1.00,
    "submit_fitness": 0.6,
    "submit_turnover": 0.65,

    # 限制
    "max_fields_per_run": 10,
    "batch_size": 10,
    "max_variants": 20,
    "concurrent_workers": 5,

    # 延迟
    "delay": 1,
}


# 从核心模块导入模板
from ..core.templates import BASE_TEMPLATES as TEMPLATES



class BatchMining:
    """批量挖掘器"""

    def __init__(self, credentials: dict = None, config: dict = None):
        self.config = config or CONFIG
        self.results: List[AlphaResult] = []
        self.client = RetryableBrainClient(credentials=credentials)

    async def authenticate(self, email: str = None, password: str = None):
        """认证"""
        await self.client.authenticate_with_retry(email, password)

    def _generate_variants(self, field_id: str) -> List[tuple]:
        """生成Alpha变体

        基于验证有效的模板生成表达式
        """
        variants = []
        for template_expr, template_name in TEMPLATES:
            expr = template_expr.format(data=field_id)
            variants.append((expr, template_name))
        return variants

    async def _evaluate(self, expression: str, field_id: str, template_name: str) -> Optional[AlphaResult]:
        """评估单个Alpha表达式"""
        try:
            result = await self.client.create_simulation_with_retry(expression, DEFAULT_SETTINGS)

            if result.get('status') == 'ERROR':
                logger.warning(f"Simulation error: {expression[:50]}...")
                return None

            alpha_data = await self.client.get_alpha_with_retry(result['alpha_id'])

            return AlphaResult(
                alpha_id=alpha_data['alpha_id'],
                expression=expression,
                field_id=field_id,
                template=template_name,
                sharpe=alpha_data['sharpe'],
                fitness=alpha_data['fitness'],
                turnover=alpha_data['turnover'],
                ppc=alpha_data['ppc'],
                margin=alpha_data['margin'],
                status='ready' if alpha_data['sharpe'] >= self.config['min_sharpe_step1'] else 'need_optimize'
            )

        except BrainAPIError as e:
            logger.error(f"API error evaluating {expression[:50]}...: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    async def mine_field(self, field_id: str) -> List[AlphaResult]:
        """挖掘单个字段"""
        logger.info(f"开始挖掘字段: {field_id}")
        results = []

        variants = self._generate_variants(field_id)
        logger.info(f"生成 {len(variants)} 个变体")

        for expr, template_name in variants:
            result = await self._evaluate(expr, field_id, template_name)
            if result:
                results.append(result)
                logger.info(f"  {template_name}: Sharpe={result.sharpe:.2f}, "
                           f"Margin={result.margin:.4f}>T={result.turnover:.4f}")

            await asyncio.sleep(0.5)

        return results

    def _multi_round_screening(self, results: List[AlphaResult]) -> List[AlphaResult]:
        """多轮筛选"""
        filtered = [r for r in results if r.sharpe >= self.config['min_sharpe_step2']]
        filtered = [r for r in filtered if r.sharpe >= self.config['min_sharpe_step3']]
        filtered = [r for r in filtered if r.fitness >= self.config['min_fitness']]
        return filtered

    async def mine_fields(self, field_ids: List[str]) -> List[AlphaResult]:
        """批量挖掘字段列表"""
        all_results = []

        for field_id in field_ids:
            results = await self.mine_field(field_id)
            all_results.extend(results)

            await asyncio.sleep(1)

        self.results = all_results
        return all_results

    def get_submittable(self) -> List[AlphaResult]:
        """获取可提交的Alpha"""
        return [r for r in self.results if r.is_submittable()]

    def get_candidates(self) -> List[AlphaResult]:
        """获取候选Alpha（满足基本条件）"""
        return [
            r for r in self.results
            if r.sharpe >= self.config['submit_sharpe']
            and r.fitness >= self.config['submit_fitness']
            and r.turnover <= self.config['submit_turnover']
        ]

    def save_results(self, output_path: str = "mining_results.json"):
        """保存结果"""
        output = {
            "total": len(self.results),
            "submittable": len(self.get_submittable()),
            "candidates": len(self.get_candidates()),
            "results": [r.to_dict() for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存到: {output_path}")


async def main():
    """主函数"""
    import os
    import json

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = BatchMining(credentials=credentials)

    await miner.authenticate(credentials['email'], credentials['password'])

    # 获取pv87数据集的字段
    fields = await miner.client.get_datafields_with_retry('pv87')
    field_ids = [f['id'] for f in fields[:5]]

    logger.info(f"开始挖掘 {len(field_ids)} 个字段")

    results = await miner.mine_fields(field_ids)

    logger.info(f"共获得 {len(results)} 个Alpha")
    logger.info(f"可提交: {len(miner.get_submittable())}")

    miner.save_results()


if __name__ == "__main__":
    asyncio.run(main())