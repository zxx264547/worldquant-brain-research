#!/usr/bin/env python3
"""研究型Alpha挖掘主循环"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.research_agent.memory import ResearchMemory, Insight
from scripts.research_agent.insight_engine import InsightEngine, AlphaMetrics
from scripts.research_agent.strategy_selector import StrategySelector
from scripts.research_agent.experiment_tracker import ExperimentTracker, ExperimentResult
from scripts.core.api_client import RetryableBrainClient
from scripts.core.exceptions import SimulationTimeoutError
from scripts.core.logging_config import setup_logging, setup_global_exception_handler

logger = setup_logging('research_loop')
setup_global_exception_handler(logger)


class ResearchLoop:
    """研究型挖掘主循环

    核心流程:
    1. 选择策略
    2. 执行实验
    3. 分析结果
    4. 更新记忆
    5. 检查是否找到可提交Alpha
    """

    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.client = RetryableBrainClient(credentials=credentials)
        self.memory = ResearchMemory()
        self.insight_engine = InsightEngine()
        self.strategy_selector = StrategySelector(self.memory)
        self.tracker = ExperimentTracker()
        self.iteration_count = 0

    async def authenticate(self) -> bool:
        """认证"""
        try:
            await self.client.authenticate_with_retry(
                self.credentials.get('email'),
                self.credentials.get('password')
            )
            logger.info("认证成功")
            return True
        except Exception as e:
            logger.error(f"认证失败: {e}")
            return False

    async def execute_strategy(self, strategy, max_concurrent: int = 3) -> List[ExperimentResult]:
        """执行策略（并发优化版）"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        total = 0

        async def evaluate_with_semaphore(expr: str, dataset: str, field_id: str, template_name: str):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._evaluate_expression(expr, dataset, field_id, template_name)
                    completed += 1
                    if completed % 5 == 0:
                        logger.info(f"  进度: {completed}/{total} 完成")
                    return result
                except Exception as e:
                    completed += 1
                    logger.warning(f"评估失败: {expr[:40]}...: {e}")
                    return None

        # 获取字段
        for dataset in strategy.datasets:
            try:
                fields = await self.client.get_datafields_with_retry(dataset)
                field_ids = [f['id'] for f in fields[:4]]  # 每数据集取4个字段（优化）

                logger.info(f"数据集 {dataset}: {len(field_ids)} 个字段")

                tasks = []
                for field_id in field_ids:
                    for template_expr, template_name in strategy.templates[:2]:  # 每模板取前2个（优化）
                        expr = template_expr.format(data=field_id)
                        tasks.append(evaluate_with_semaphore(expr, dataset, field_id, template_name))

                total = len(tasks)
                logger.info(f"开始执行 {total} 个模拟（并发上限: {max_concurrent}）...")

                task_results = await asyncio.gather(*tasks)

                for result in task_results:
                    if result:
                        results.append(result)
                        logger.info(f"  {result.template}: Sharpe={result.sharpe:.2f}, "
                                   f"M/T={result.margin_ratio:.2f}")

            except Exception as e:
                logger.error(f"获取字段失败 {dataset}: {e}")

        return results

    async def _evaluate_expression(self, expression: str, dataset: str,
                                  field_id: str, template: str) -> Optional[ExperimentResult]:
        """评估单个表达式"""
        settings = {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': 1,
            'decay': 0.0,
            'neutralization': 'NONE',
            'truncation': 0.0,
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False
        }

        try:
            result = await self.client.create_simulation_with_retry(expression, settings)

            if result.get('status') == 'ERROR':
                return None

            alpha_data = await self.client.get_alpha_with_retry(result['alpha_id'])

            exp_result = ExperimentResult(
                alpha_id=alpha_data['alpha_id'],
                expression=expression,
                dataset=dataset,
                template=template,
                field_id=field_id,
                sharpe=alpha_data['sharpe'],
                fitness=alpha_data['fitness'],
                turnover=alpha_data['turnover'],
                margin=alpha_data['margin'],
                ppc=alpha_data['ppc']
            )

            return exp_result

        except SimulationTimeoutError:
            logger.warning(f"评估超时（120秒）: {expression[:40]}...")
            return None
        except Exception as e:
            logger.warning(f"评估异常: {e}")
            return None

    async def run_iteration(self) -> bool:
        """执行一轮研究"""
        self.iteration_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"第 {self.iteration_count} 轮研究")
        logger.info(f"{'='*60}")

        # 1. 选择策略
        strategy = self.strategy_selector.select_next_strategy()
        logger.info(f"选择策略: {strategy.name}")
        logger.info(f"描述: {strategy.description}")

        # 2. 执行
        logger.info(f"执行中...")
        results = await self.execute_strategy(strategy)

        # 3. 记录实验
        experiment = self.tracker.record(strategy.name, results)

        # 4. 分析洞察
        alpha_metrics = [AlphaMetrics(
            alpha_id=r.alpha_id,
            expression=r.expression,
            dataset=r.dataset,
            template=r.template,
            field_id=r.field_id,
            sharpe=r.sharpe,
            fitness=r.fitness,
            turnover=r.turnover,
            margin=r.margin,
            ppc=r.ppc
        ) for r in results]

        insights = self.insight_engine.analyze_batch_results(alpha_metrics)

        # 5. 更新记忆
        for insight in insights:
            self.memory.add_insight(
                insight=insight.description,
                source=f"iteration_{self.iteration_count}",
                confidence=insight.confidence,
                hypothesis=f"基于{insight.category}模式"
            )

        self.memory.record_experiment(
            strategy=strategy.to_dict(),
            results=[r.to_dict() for r in results],
            metrics={
                'tested_count': len(results),
                'found_candidates': len(self.tracker.get_all_candidates())
            }
        )
        self.memory.save()

        # 6. 标记策略已测试
        self.strategy_selector.mark_strategy_tested(strategy, {
            'alphas': [r.to_dict() for r in results],
            'tested': len(results),
            'candidates': len([r for r in results if r.is_submittable])
        })

        # 7. 打印进度
        self.tracker.print_progress_report()

        # 8. 检查是否找到可提交Alpha
        candidates = self.tracker.get_all_candidates()
        if candidates:
            logger.info(f"\n🎉 找到 {len(candidates)} 个可提交Alpha!")
            return True

        return False

    async def run(self, max_iterations: int = 10) -> bool:
        """运行多轮研究"""
        if not await self.authenticate():
            logger.error("认证失败，退出")
            return False

        logger.info(f"开始研究，最多 {max_iterations} 轮")

        for i in range(max_iterations):
            found = await self.run_iteration()
            if found:
                logger.info("🎉 研究成功，找到可提交Alpha!")
                self.tracker.save()
                return True

            # 打印建议
            suggestions = self.strategy_selector.suggest_next_steps()
            if suggestions:
                logger.info(f"\n下轮建议:")
                for s in suggestions[:3]:
                    logger.info(f"  - {s}")

            await asyncio.sleep(1)

        logger.info(f"\n研究完成，共 {max_iterations} 轮，未找到可提交Alpha")
        self.tracker.save()
        self.memory.save()

        # 打印最终总结
        logger.info("\n" + self.memory.summarize())

        return False


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='研究型Alpha挖掘')
    parser.add_argument('--iterations', type=int, default=3, help='研究轮数')
    parser.add_argument('--config', type=str, default=None, help='配置文件路径')

    args = parser.parse_args()

    # 加载凭证
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config_path = Path(__file__).parent.parent.parent / 'config' / 'user_config.json'
        with open(config_path, 'r') as f:
            config = json.load(f)

    credentials = config.get('credentials', {})

    # 运行研究
    research = ResearchLoop(credentials)
    await research.run(max_iterations=args.iterations)


if __name__ == "__main__":
    asyncio.run(main())