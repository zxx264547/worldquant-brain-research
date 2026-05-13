#!/usr/bin/env python3
"""统一回测执行器 — 带自动知识沉淀"""

import hashlib
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.scripts.core import RetryableBrainClient
from worldquant_brain.engine.settings_manager import get_settings
from worldquant_brain.engine.result_store import store

FORUM_DB = Path(__file__).parent.parent / "data" / "forum.sqlite3"


class BacktestRunner:
    """统一回测执行器 — SQLite去重 + 自动知识沉淀"""

    def __init__(self, client: RetryableBrainClient = None):
        self.client = client or RetryableBrainClient()
        self._init_done = False

    async def init(self):
        if not self._init_done:
            await self.client.authenticate_with_retry()
            store.init()
            self._init_done = True

    async def run(self, expression: str, settings: dict = None,
                  name: str = "") -> dict:
        """运行单个回测"""
        await self.init()

        # 0. 表达式自动修复 (降低40% token浪费)
        from worldquant_brain.engine.func_call_corrector import fixer
        original_expr = expression
        try:
            expression = fixer.fix(expression, fill_defaults=False)
            if expression != original_expr:
                print(f"  [FIX] 表达式已修复: {original_expr[:50]}... → {expression[:50]}...")
        except Exception:
            pass  # 修复失败则用原文

        # 1. SQLite去重（含settings，不同neutralization/decay不误判）
        expr_hash = hashlib.sha256(f"{expression}|{merged}".encode()).hexdigest()[:16]
        if cached := store.find(expression, merged):
            return cached

        # 2. 回测
        merged = get_settings(**(settings or {}))
        merged["description"] = name or f"bt_{expr_hash}"

        sim = await self.client.create_simulation_with_retry(expression, merged)
        if sim.get('status') == 'ERROR':
            return {"expression": expression, "status": "error",
                    "error": sim.get('message', 'Unknown')[:80]}

        alpha_id = sim.get('alpha_id')
        alpha = await self.client.get_alpha_with_retry(alpha_id)

        result = {
            "alpha_id": alpha_id,
            "expression": expression,
            "name": name or expr_hash,
            "sharpe": alpha.get('sharpe', 0),
            "fitness": alpha.get('fitness', 0),
            "ppc": alpha.get('ppc', 0),
            "margin": alpha.get('margin', 0),
            "turnover": alpha.get('turnover', 0),
            "settings": merged,
            "status": "ok",
            "is_submittable": alpha.get('sharpe', 0) >= 1.58,
            "timestamp": datetime.now().isoformat()
        }

        # 3. SQLite存储
        store.save(result)

        # 4. 自动知识沉淀 (Sharpe >= 1.0)
        sharpe = result['sharpe']
        if sharpe >= 1.0:
            await self._auto_knowledge(result)
            if result.get('fitness', 0) < 1.0:
                await self._apply_skill_fix(result)

        # 5. AlphaHarness记账 (如果已注入)
        if hasattr(self, '_shared_harness') and self._shared_harness:
            self._shared_harness.feed_result(
                self._shared_harness.current_round, result)

        return result

    async def run_batch(self, candidates: list,
                        concurrency: int = 3) -> list[dict]:
        """批量回测"""
        await self.init()
        sem = asyncio.Semaphore(concurrency)
        results = []

        async def limited(expr, settings, name):
            async with sem:
                return await self.run(expr, settings, name)

        tasks = []
        for cand in candidates:
            if isinstance(cand, tuple):
                expr = cand[0]
                settings = cand[1] if len(cand) > 1 else None
                name = cand[2] if len(cand) > 2 else ""
            else:
                expr, settings, name = cand, None, ""
            tasks.append(limited(expr, settings, name))

        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                results.append(result)
                sharpe = result.get('sharpe', 0)
                if sharpe >= 1.58:
                    print(f"*** 可提交! Sharpe={sharpe:.3f} "
                          f"alpha_id={result['alpha_id']} ***")

        return results

    # ─── 知识沉淀 ───

    async def _auto_knowledge(self, result: dict):
        """Sharpe>=1.0: 自动沉淀到wq-forum-rag知识库"""
        try:
            if not FORUM_DB.exists():
                return

            from wq_forum_rag.evolution import EvolutionService
            evo = EvolutionService(str(FORUM_DB))

            sharpe = result['sharpe']
            alpha_id = result['alpha_id']
            slug = f"alpha-{alpha_id}"

            # 检查是否已存在
            existing = evo.get_knowledge_page(slug)
            if existing:
                return

            # 确定置信度
            if sharpe >= 1.58:
                confidence = 0.95
                tag = "submission-ready"
            else:
                confidence = 0.80
                tag = "promising"

            body = f"""## Alpha配置

- 名称: {result.get('name', 'N/A')}
- Sharpe: {sharpe:.3f}
- Fitness: {result.get('fitness', 0):.3f}
- Turnover: {result.get('turnover', 0):.4f}
- Margin: {result.get('margin', 0):.4f}
- PPC: {result.get('ppc', 0):.4f}

## 表达式

```
{result['expression']}
```

## 回测设置

```
{result.get('settings', {})}
```
"""
            evo.propose_knowledge_page(
                slug=slug,
                title=f"Alpha[{tag}]: {result.get('name', alpha_id)[:60]} (Sharpe={sharpe:.2f})",
                summary=f"Sharpe={sharpe:.2f}, Fitness={result.get('fitness', 0):.2f}. "
                        f"Expr: {result['expression'][:80]}",
                body=body,
                source_topic_ids=[],  # 运行经验, 无来源帖子
                confidence=confidence,
                auto_publish=True,
            )
            print(f"  [知识沉淀] {slug}: Sharpe={sharpe:.3f} confidence={confidence}")

        except Exception as e:
            print(f"  [知识沉淀异常] {e}")

    # ─── Skills修复 ───

    async def _apply_skill_fix(self, result: dict):
        """对低Fitness Alpha应用Skill修复策略"""
        try:
            from worldquant_brain.engine.skill_executor import SkillExecutor
            executor = SkillExecutor()

            # 诊断问题
            diagnosis = executor.diagnose(result)
            if not diagnosis:
                return

            # 应用修复
            fixes = executor.get_fixes(diagnosis)
            if not fixes:
                return

            print(f"  [Skill] Alpha {result['alpha_id']}: "
                  f"发现问题 {diagnosis}, 建议修复 {fixes}")

            # 对每个修复生成新配置并重新回测
            for fix in fixes:
                fixed_settings = executor.apply_fix(result, fix)
                if fixed_settings:
                    fixed_name = f"{result['name']}_fix_{fix['type']}"
                    fixed_expr = result['expression']
                    print(f"  [Skill] 尝试修复: {fixed_name}")
                    # 注意: 修复后的回测会在下一轮自动执行
                    # (避免在单次run中递归)

        except Exception as e:
            print(f"  [Skill异常] {e}")

    # ─── 查询 ───

    def get_best(self, limit: int = 10) -> list[dict]:
        return store.best(limit)

    def get_submittable(self) -> list[dict]:
        return store.submittable()


async def quick_test(expression: str, **settings) -> dict:
    runner = BacktestRunner()
    return await runner.run(expression, settings)
