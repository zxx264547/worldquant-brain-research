"""认知循环 — AI Agent 的工具函数集

混合模式：AI负责高层决策（perceive/plan/reflect/evolve），
Python Worker负责批量执行（dispatch/execute）。

使用方式（由AI Agent通过CLI调用）：
    python worldquant_brain/cli.py perceive
    python worldquant_brain/cli.py reflect --results-file /tmp/batch_results.json
    python worldquant_brain/cli.py evolve
"""
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from worldquant_brain.knowledge.unified_store import UnifiedKnowledgeStore
from worldquant_brain.knowledge.anti_pattern_tracker import AntiPatternTracker


class CognitiveLoop:
    """AI认知循环的工具函数集"""

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.root = Path(project_root)
        self.store = UnifiedKnowledgeStore(self.root)
        self.tracker = AntiPatternTracker(self.root)

    # ═══════════════════════════════════════════
    #  PERCEIVE — AI调用此函数了解当前状态
    # ═══════════════════════════════════════════

    def perceive(self) -> dict:
        """返回当前全局状态供AI决策

        AI Agent应该首先调用此函数，然后基于返回的状态决定下一步行动。
        """
        state = self.store.perceive()

        # 增加认知循环特有的上下文
        state["anti_patterns"] = [
            ap["content"].get("pattern", "")
            for ap in self.tracker.get_all_patterns()
        ]
        state["hours_since_forum_sync"] = self._hours_since(state.get("last_forum_sync"))
        state["hours_since_evolve"] = self._hours_since(state.get("last_evolve"))

        # 加载策略配置（如果存在）
        config_path = self.root / "worldquant_brain" / "strategies" / "strategy_config.yaml"
        if config_path.exists():
            state["strategy_config_exists"] = True
        else:
            state["strategy_config_exists"] = False

        return state

    # ═══════════════════════════════════════════
    #  DISPATCH — 下发批量任务给Python Worker
    # ═══════════════════════════════════════════

    def dispatch(self, plan: dict) -> dict:
        """将AI的计划转化为可执行的批量任务

        Args:
            plan: AI生成的计划，格式：
                {
                    "action": "mine",
                    "strategy": "analyst4_eps",
                    "expressions": ["expr1", "expr2", ...],
                    "settings": {...},
                    "max_batch": 8
                }

        Returns:
            dispatch结果：任务ID列表或错误信息
        """
        action = plan.get("action", "mine")

        if action == "mine":
            return self._dispatch_mine(plan)
        elif action == "analyze":
            return self._dispatch_analyze(plan)
        elif action == "forum_sync":
            return self._dispatch_forum_sync(plan)
        else:
            return {"status": "error", "message": f"未知action: {action}"}

    def _dispatch_mine(self, plan: dict) -> dict:
        """将挖掘任务入队并启动Worker执行

        完整流程：
        1. 反模式过滤
        2. 任务入队（SQLite task queue）
        3. 启动 WorkerPool 消费任务（调用 BRAIN API 回测）
        4. 等待完成，收集结果
        5. 将结果写入文件供 reflect() 使用
        """
        from worldquant_brain.db.repository import push_task, get_pending_count

        expressions = plan.get("expressions", [])
        strategy = plan.get("strategy", "cognitive_loop")
        settings = plan.get("settings", {})

        # 反模式过滤
        dataset = plan.get("dataset", "")
        filtered = []
        skipped = []
        for expr in expressions:
            if self.tracker.should_skip(expr, dataset):
                skipped.append(expr)
            else:
                filtered.append(expr)

        # 入队
        task_ids = []
        for expr in filtered[:plan.get("max_batch", 8)]:
            tid = push_task(strategy, expr, settings, priority=plan.get("priority", 5))
            task_ids.append(tid)

        if not task_ids:
            return {
                "status": "all_skipped",
                "tasks_created": 0,
                "tasks_skipped_anti_pattern": len(skipped),
                "task_ids": [],
                "pending_total": get_pending_count()
            }

        # 启动Worker执行（如果run_workers=True）
        run_workers = plan.get("run_workers", True)
        results_file = None
        if run_workers:
            results_file = self._run_workers_and_collect(
                task_ids, strategy, dataset,
                workers=plan.get("workers", 3)
            )

        return {
            "status": "dispatched",
            "tasks_created": len(task_ids),
            "tasks_skipped_anti_pattern": len(skipped),
            "task_ids": task_ids,
            "pending_total": get_pending_count(),
            "results_file": results_file,
            "message": "Worker已执行完成，用 reflect <results_file> 分析结果" if results_file else "任务已入队，需手动启动Worker"
        }

    def _run_workers_and_collect(self, task_ids: list[int], strategy: str,
                                  dataset: str, workers: int = 3) -> Optional[str]:
        """启动WorkerPool执行任务并收集结果"""
        try:
            import asyncio
            from worldquant_brain.db.repository import get_pending_count

            async def _execute():
                from worldquant_brain.scheduler.worker_pool import WorkerPool
                pool = WorkerPool(size=workers)
                await pool.start()
                # 等待所有任务完成
                max_wait = 600  # 最多等10分钟
                waited = 0
                while get_pending_count() > 0 and waited < max_wait:
                    await asyncio.sleep(5)
                    waited += 5
                await pool.stop()

            asyncio.run(_execute())

            # 收集结果
            from worldquant_brain.db.repository import get_best_alphas
            results = get_best_alphas(limit=len(task_ids))
            results_with_meta = []
            for r in results:
                r["strategy"] = strategy
                r["dataset"] = dataset
                results_with_meta.append(r)

            # 写入临时文件
            results_path = Path("/tmp/cognitive_loop_results.json")
            results_path.write_text(json.dumps(results_with_meta, indent=2, ensure_ascii=False))
            return str(results_path)

        except ImportError as e:
            # 外部依赖缺失（如 platform_functions），降级为仅入队
            return None
        except Exception as e:
            # Worker执行异常，降级
            return None

    def _dispatch_analyze(self, plan: dict) -> dict:
        """下发数据分析任务（目前同步执行）"""
        query = plan.get("query", "")
        results = self.store.search(query)
        return {"status": "analyzed", "results_count": len(results), "results": results[:10]}

    def _dispatch_forum_sync(self, plan: dict) -> dict:
        """触发论坛同步（占位，P5实现）"""
        return {"status": "pending", "message": "forum_syncer尚未实现，请等待P5阶段"}

    # ═══════════════════════════════════════════
    #  REFLECT — AI分析批量执行结果
    # ═══════════════════════════════════════════

    def reflect(self, results: list[dict]) -> dict:
        """分析一批回测结果，提取insights

        Args:
            results: 回测结果列表，每个元素包含 expression, sharpe, fitness, ppc, margin, turnover

        Returns:
            反思摘要：包含insights、建议的下一步、是否应该进化
        """
        if not results:
            return {"insights": [], "suggestion": "无结果，建议换方向",
                    "should_evolve": False}

        # 基础统计
        sharpes = [r.get("sharpe", 0) for r in results]
        best_sharpe = max(sharpes)
        avg_sharpe = sum(sharpes) / len(sharpes)
        pass_count = sum(1 for r in results if self._passes_ppa(r))

        # 提取insights
        insights = []

        # insight 1: 总体方向判断
        if avg_sharpe > 0.8:
            insights.append({
                "type": "direction",
                "content": f"当前方向有潜力，平均Sharpe={avg_sharpe:.3f}，继续深入",
                "confidence": 0.7
            })
        elif avg_sharpe < 0.3:
            insights.append({
                "type": "direction",
                "content": f"当前方向效果差，平均Sharpe={avg_sharpe:.3f}，建议切换",
                "confidence": 0.8
            })

        # insight 2: 检测失败模式
        failures = [r for r in results if r.get("sharpe", 0) < 0.5]
        for r in failures:
            self.tracker.record_failure(
                r.get("expression", ""),
                r.get("dataset", ""),
                r.get("sharpe", 0),
                self._classify_failure(r)
            )

        # insight 3: 发现成功模式
        successes = [r for r in results if r.get("sharpe", 0) >= 1.0]
        for r in successes:
            insights.append({
                "type": "success_pattern",
                "content": f"高Sharpe表达式: {r.get('expression', '')[:80]}",
                "sharpe": r.get("sharpe", 0),
                "confidence": min(r.get("sharpe", 0) / 1.58, 1.0)
            })

        # 写入知识库
        for ins in insights:
            self.store.record_insight(
                ins["content"], source="reflect",
                confidence=ins.get("confidence", 0.5),
                metadata={"type": ins["type"]}
            )

        # 记录实验
        strategy = results[0].get("strategy", "unknown") if results else "unknown"
        self.store.record_experiment(strategy, {
            "batch_size": len(results),
            "best_sharpe": best_sharpe,
            "avg_sharpe": round(avg_sharpe, 3),
            "pass_count": pass_count
        })

        # 判断是否应该触发进化
        should_evolve = self._should_evolve()

        return {
            "batch_size": len(results),
            "best_sharpe": round(best_sharpe, 3),
            "avg_sharpe": round(avg_sharpe, 3),
            "pass_ppa_count": pass_count,
            "insights": insights,
            "new_anti_patterns": len(failures),
            "should_evolve": should_evolve,
            "suggestion": self._suggest_next(avg_sharpe, best_sharpe, pass_count)
        }

    # ═══════════════════════════════════════════
    #  REMEMBER — 显式写入知识
    # ═══════════════════════════════════════════

    def remember(self, insight: str, confidence: float = 0.6,
                 category: str = "general") -> dict:
        """AI显式记录一条发现到知识库"""
        event_id = self.store.record_insight(
            insight, source="ai_decision",
            confidence=confidence,
            metadata={"category": category}
        )
        return {"status": "remembered", "event_id": event_id}

    # ═══════════════════════════════════════════
    #  EVOLVE — 检查并提议规则修改
    # ═══════════════════════════════════════════

    def evolve(self) -> dict:
        """基于累积证据提议规则修改

        检查条件：
        1. 提交结果模式 → 阈值调整建议
        2. 策略效果差异 → 优先级调整
        3. 反模式累积 → 规则更新
        """
        proposals = []

        # 检查提交模式
        submit_patterns = self.store.get_submit_patterns()
        if submit_patterns["total"] >= 5:
            proposals.extend(self._propose_threshold_changes(submit_patterns))

        # 检查策略效果
        effectiveness = self.store._get_strategy_effectiveness()
        if len(effectiveness) >= 3:
            proposals.extend(self._propose_strategy_reorder(effectiveness))

        # 记录进化事件
        if proposals:
            self.store._record_event("evolve", "cognitive_loop",
                                     {"proposals": proposals}, 0.8)

        return {
            "status": "evolved" if proposals else "no_change",
            "proposals": proposals,
            "message": f"生成{len(proposals)}条进化提议" if proposals else "证据不足，暂不进化"
        }

    # ═══════════════════════════════════════════
    #  内部辅助方法
    # ═══════════════════════════════════════════

    @staticmethod
    def _passes_ppa(result: dict) -> bool:
        return (result.get("sharpe", 0) >= 1.58 and
                result.get("fitness", 0) > 0.5 and
                result.get("ppc", 1) < 0.5 and
                result.get("margin", 0) > result.get("turnover", 1))

    @staticmethod
    def _classify_failure(result: dict) -> str:
        if result.get("sharpe", 0) < 0.3:
            return "low_sharpe"
        if result.get("fitness", 0) < 0.3:
            return "low_fitness"
        if result.get("ppc", 1) >= 0.5:
            return "high_ppc"
        if result.get("margin", 0) <= result.get("turnover", 0):
            return "low_margin"
        return "other"

    def _should_evolve(self) -> bool:
        """判断是否有足够证据触发进化"""
        last_evolve = self.store._get_last_event_time("evolve")
        if last_evolve:
            last_dt = datetime.fromisoformat(last_evolve)
            if datetime.now() - last_dt < timedelta(hours=6):
                return False
        # 至少需要10个新实验结果
        recent = self.store.get_knowledge_events_since(
            (datetime.now() - timedelta(hours=24)).isoformat(), "experiment")
        return len(recent) >= 10

    @staticmethod
    def _suggest_next(avg_sharpe: float, best_sharpe: float, pass_count: int) -> str:
        if pass_count > 0:
            return "有通过PPA的Alpha，建议深度优化或直接提交"
        if best_sharpe >= 1.0:
            return "接近目标，建议对最佳Alpha做参数微调和变体生成"
        if avg_sharpe >= 0.5:
            return "方向正确但距目标有差距，建议增加复杂度或换数据集"
        return "当前方向效果不佳，建议切换策略/数据集/算子"

    @staticmethod
    def _hours_since(timestamp: Optional[str]) -> float:
        if not timestamp:
            return 999.0
        try:
            dt = datetime.fromisoformat(timestamp)
            return (datetime.now() - dt).total_seconds() / 3600
        except (ValueError, TypeError):
            return 999.0

    def _propose_threshold_changes(self, patterns: dict) -> list[dict]:
        """基于提交结果提议阈值调整"""
        proposals = []
        accepted_sharpe = patterns.get("accepted_sharpe_range", {})
        if accepted_sharpe.get("min", 999) < 1.58:
            proposals.append({
                "type": "threshold",
                "rule": "sharpe_min",
                "current": 1.58,
                "proposed": round(accepted_sharpe["min"] - 0.05, 2),
                "evidence": f"有{patterns['accepted_count']}个Alpha以Sharpe<1.58被接受",
                "level": "L2"
            })
        return proposals

    def _propose_strategy_reorder(self, effectiveness: dict) -> list[dict]:
        """基于策略效果提议优先级调整"""
        if not effectiveness:
            return []
        sorted_strats = sorted(effectiveness.items(),
                               key=lambda x: x[1].get("avg_best", 0), reverse=True)
        if len(sorted_strats) >= 2:
            best = sorted_strats[0]
            worst = sorted_strats[-1]
            if best[1].get("avg_best", 0) > worst[1].get("avg_best", 0) * 2:
                return [{
                    "type": "strategy_priority",
                    "rule": "strategy_order",
                    "proposed": f"提升 {best[0]} 优先级，降低 {worst[0]}",
                    "evidence": f"{best[0]} avg_best={best[1]['avg_best']}, "
                                f"{worst[0]} avg_best={worst[1]['avg_best']}",
                    "level": "L1"
                }]
        return []


# ─── CLI 入口函数（供 cli.py 调用）───

def cli_perceive():
    """CLI: perceive 命令"""
    loop = CognitiveLoop()
    state = loop.perceive()
    print(json.dumps(state, indent=2, ensure_ascii=False))


def cli_dispatch(plan_json: str):
    """CLI: dispatch 命令"""
    loop = CognitiveLoop()
    plan = json.loads(plan_json)
    result = loop.dispatch(plan)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cli_reflect(results_file: str = None):
    """CLI: reflect 命令

    如果不传 results_file，自动使用上次 dispatch 的结果文件
    """
    loop = CognitiveLoop()
    if results_file is None or results_file == "auto":
        results_file = "/tmp/cognitive_loop_results.json"
    path = Path(results_file)
    if not path.exists():
        print(json.dumps({"error": f"结果文件不存在: {results_file}",
                          "hint": "先执行 dispatch 或手动指定结果文件"}, ensure_ascii=False))
        return
    results = json.loads(path.read_text())
    reflection = loop.reflect(results)
    print(json.dumps(reflection, indent=2, ensure_ascii=False))


def cli_remember(insight: str, confidence: float = 0.6):
    """CLI: remember 命令"""
    loop = CognitiveLoop()
    result = loop.remember(insight, confidence)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cli_evolve():
    """CLI: evolve 命令"""
    loop = CognitiveLoop()
    result = loop.evolve()
    print(json.dumps(result, indent=2, ensure_ascii=False))
