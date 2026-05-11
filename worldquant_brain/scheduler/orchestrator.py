#!/usr/bin/env python3
"""编排器 — 知识增强的Alpha挖掘流程"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.scheduler.task_queue import TaskQueue
from worldquant_brain.scheduler.worker_pool import WorkerPool
from worldquant_brain.strategies import ALL_STRATEGIES, get_strategy
from worldquant_brain.engine.result_store import store
from worldquant_brain.engine import ExpressionTemplates, get_settings

FORUM_DB = Path(__file__).parent.parent / "data" / "forum.sqlite3"


class Orchestrator:
    """知识增强编排器

    流程: 知识研究 → 生成候选 → Worker执行 → 结果沉淀
    """

    def __init__(self, strategy_names: list = None, worker_count: int = 4):
        self.strategies = [get_strategy(s)
                          for s in (strategy_names or ['combination'])]
        self.pool = WorkerPool(size=worker_count)
        self.queue = TaskQueue()

    async def run(self, context: dict = None):
        if context is None:
            context = self._default_context()

        store.init()

        # ─── Step 0: 知识研究 ───
        knowledge_context = self._research(context)

        # ─── Step 1: 生成候选 (注入知识上下文) ───
        total = 0
        for strategy in self.strategies:
            # 让每个策略用知识增强后的上下文生成候选
            ctx = {**context, 'knowledge_context': knowledge_context}
            for expr, settings, name in strategy.generate_candidates(ctx):
                self.queue.store.enqueue(strategy.name, expr, settings)
                total += 1

        print(f"[Orchestrator] {total} tasks enqueued from "
              f"{len(self.strategies)} strategies")

        # ─── Step 2: Worker池执行 ───
        await self.pool.start()

        while self.queue.pending > 0:
            await asyncio.sleep(5)
            print(f"[Orchestrator] Pending: {self.queue.pending}")

        await self.pool.stop()

        # ─── Step 3: 本轮总结 ───
        best = store.best(5)
        submittable = store.submittable()

        print(f"\n[Orchestrator] 完成. 总Alpha数: {store.count}")
        print(f"[Orchestrator] 可提交: {len(submittable)}")
        print(f"[Orchestrator] Top 5:")
        for a in best:
            print(f"  {a['name'][:40]}: Sharpe={a['sharpe']:.3f}")

        # ─── Step 4: 知识库链接发现 ───
        self._link_discoveries(best)

    def _research(self, context: dict) -> dict:
        """搜索知识库获取相关经验"""
        try:
            if not FORUM_DB.exists():
                print("[Orchestrator] 论坛数据库不存在，跳过知识搜索")
                return {}

            from wq_forum_rag.evolution import EvolutionService
            evo = EvolutionService(str(FORUM_DB))

            queries = [
                f"alpha mining {strategy.name} {strategy.description}"
                for strategy in self.strategies
            ]
            queries.append("high sharpe alpha combination pattern")

            all_knowledge = []
            for q in queries[:3]:  # 限制查询次数
                result = evo.build_evolution_context(q, top_k=3)
                all_knowledge.extend(result.get('published_knowledge', []))
                all_knowledge.extend(result.get('forum_evidence', []))

            print(f"[Orchestrator] 知识搜索: 找到 {len(all_knowledge)} 条相关记录")

            # 提取关键发现
            key_patterns = set()
            for k in all_knowledge:
                if isinstance(k, dict):
                    summary = k.get('summary', '') or k.get('title', '')
                    if summary:
                        key_patterns.add(summary[:120])

            return {
                'knowledge_count': len(all_knowledge),
                'key_patterns': list(key_patterns)[:10],
                'raw': all_knowledge
            }

        except Exception as e:
            print(f"[Orchestrator] 知识搜索异常: {e}")
            return {}

    def _link_discoveries(self, best_alphas: list):
        """在高Sharpe Alpha之间建立知识链接"""
        try:
            if not FORUM_DB.exists() or len(best_alphas) < 2:
                return

            from wq_forum_rag.evolution import EvolutionService
            evo = EvolutionService(str(FORUM_DB))

            # 找到最佳Alpha的知识页slug
            slugs = []
            for a in best_alphas[:3]:
                slug = f"alpha-{a['id']}"
                page = evo.get_knowledge_page(slug)
                if page:
                    slugs.append(slug)

            # 建立refines链接
            for i in range(len(slugs) - 1):
                evo.link_knowledge_pages(
                    slugs[i + 1], slugs[i],
                    relation_type='refines',
                    weight=0.8, confidence=0.7
                )

            if len(slugs) >= 2:
                print(f"[Orchestrator] 知识链接: {len(slugs)} 个相关Alpha已关联")

        except Exception as e:
            print(f"[Orchestrator] 知识链接异常: {e}")

    def _default_context(self) -> dict:
        bases = [
            ("eps_252_09", ExpressionTemplates.eps_basic()),
            ("eps_mom", ExpressionTemplates.eps_with_momentum()),
            ("eps_div", ExpressionTemplates.eps_with_dividend()),
        ]
        techs = [
            ("beta_120", ExpressionTemplates.tech_beta(120)),
            ("beta_252", ExpressionTemplates.tech_beta(252)),
            ("vol_120", ExpressionTemplates.tech_vol(120)),
            ("vol_252", ExpressionTemplates.tech_vol(252)),
            ("rsi_14", ExpressionTemplates.tech_rsi(14)),
            ("mom_60", ExpressionTemplates.tech_momentum(60)),
        ]
        return {"base_alphas": bases, "technicals": techs}


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Alpha Research Orchestrator')
    parser.add_argument('--strategy', '-s', nargs='+',
                        default=['combination'],
                        choices=list(ALL_STRATEGIES.keys()),
                        help='Strategies to run')
    parser.add_argument('--workers', '-w', type=int, default=4,
                        help='Number of workers')
    args = parser.parse_args()

    orch = Orchestrator(args.strategy, args.workers)
    await orch.run()


if __name__ == "__main__":
    asyncio.run(main())
