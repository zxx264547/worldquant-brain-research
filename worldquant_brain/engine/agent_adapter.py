#!/usr/bin/env python3
"""Agent适配层 — 多智能体通过repository读写状态

Agent通过CLI调用: python worldquant_brain/cli.py <command>
CLI调用本模块函数, 全部通过repository层操作JSON状态文件
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime

from worldquant_brain.db.repository import (
    get_queued_tasks, push_task, get_best_alphas, save_alpha, get_workers,
)


# ═══ Ideas ═══

def load_ideas(limit: int = 8) -> list[dict]:
    """从tasks加载待处理idea"""
    tasks = get_queued_tasks(limit)
    return [{
        "idea_id": f"task_{t['id']}",
        "expression": t['expression'],
        "strategy": t['strategy'],
        "settings": json.loads(t.get('settings_json', '{}') or '{}'),
    } for t in tasks]


def save_ideas(ideas: list[dict]):
    """保存ideas到tasks"""
    for idea in ideas:
        push_task(
            strategy=idea.get('strategy', 'manual'),
            expression=idea.get('expression', ''),
            settings=idea.get('settings', {}),
            priority=0,
        )


# ═══ Results ═══

def load_results(recent: int = 50) -> list[dict]:
    return get_best_alphas(recent)


def save_result(result: dict):
    result['timestamp'] = datetime.now().isoformat()
    save_alpha(result)


# ═══ State ═══

def load_state() -> dict:
    workers = get_workers()
    return {"workers": workers, "timestamp": datetime.now().isoformat()}


# ═══ 回测 ═══

async def run_backtest(expression: str, settings: dict = None,
                       name: str = "") -> dict:
    from worldquant_brain.engine.backtest_runner import BacktestRunner
    return await BacktestRunner().run(expression, settings, name)


# ═══ 知识 ═══

def search_knowledge(query: str) -> list[dict]:
    forum_db = Path(__file__).parent.parent / "data" / "forum.sqlite3"
    if not forum_db.exists():
        return []

    import sys
    forum_src = str(Path(__file__).parent.parent / "wq_forum_rag" / "src")
    if forum_src not in sys.path:
        sys.path.insert(0, forum_src)
    from wq_forum_rag.evolution import EvolutionService
    evo = EvolutionService(str(forum_db))
    result = evo.build_evolution_context(query, top_k=3)
    return result.get('published_knowledge', []) + result.get('forum_evidence', [])


# ═══ 统计 ═══

def get_stats() -> dict:
    from worldquant_brain.engine.result_store import store
    best = store.best(1)
    return {
        "total_alphas": store.count,
        "best": best[0] if best else None,
        "submittable": store.submittable(),
        "timestamp": datetime.now().isoformat()
    }


# ═══ 表达式 ═══

def fix_expression(expr: str) -> str:
    from worldquant_brain.engine.func_call_corrector import fixer
    return fixer.fix(expr)


# ═══ 信号灯 ═══

def evaluate_batch(results: list[dict]) -> dict:
    from worldquant_brain.engine.traffic_light import evaluate_direction, get_light_emoji
    r = evaluate_direction(results)
    r['emoji'] = get_light_emoji(r['light'])
    return r
