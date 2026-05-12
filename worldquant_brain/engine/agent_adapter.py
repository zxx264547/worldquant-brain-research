#!/usr/bin/env python3
"""Agent适配层 — 多智能体直接读写SQLite

Agent通过CLI调用: python worldquant_brain/cli.py <command>
CLI调用本模块函数, 全部直接读写SQLite brain.db
"""

import json
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "brain.db"


# ═══ Ideas ═══

def load_ideas(limit: int = 8) -> list[dict]:
    """从SQLite tasks表加载待处理idea"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT ?",
        (limit,)).fetchall()
    conn.close()
    return [{
        "idea_id": f"task_{r['id']}",
        "expression": r['expression'],
        "strategy": r['strategy'],
        "settings": json.loads(r.get('settings_json', '{}') or '{}'),
    } for r in rows]


def save_ideas(ideas: list[dict]):
    """保存ideas到SQLite tasks表"""
    conn = sqlite3.connect(str(DB_PATH))
    for idea in ideas:
        conn.execute("""
            INSERT OR IGNORE INTO tasks (expression, strategy, settings_json, status, priority)
            VALUES (?, ?, ?, 'queued', 0)
        """, (
            idea.get('expression', ''),
            idea.get('strategy', 'manual'),
            json.dumps(idea.get('settings', {}) or {}),
        ))
    conn.commit()
    conn.close()


# ═══ Results ═══

def load_results(recent: int = 50) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM alphas WHERE status='done' ORDER BY created_at DESC LIMIT ?",
        (recent,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_result(result: dict):
    result['timestamp'] = datetime.now().isoformat()
    from worldquant_brain.db.repository import save_alpha
    save_alpha(result)


# ═══ State ═══

def load_state() -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    workers = [dict(r) for r in conn.execute("SELECT * FROM workers").fetchall()]
    conn.close()
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
