#!/usr/bin/env python3
"""Ledger记账系统 — 每轮研究记录: winner/nearline/blocked/next question

基于 JW52291:
    "以前的问题是只记录成功候选，导致下次又重复踩坑。
    现在失败也要入账，而且要分类型。"
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ResearchRound:
    """一轮研究的完整记录"""
    round_id: str                    # 轮次ID
    contract_id: str                 # 合约ID
    structural_question: str         # 本轮要回答的结构性问题

    # 结果
    winner: Optional[dict] = None    # 本轮的获胜Alpha
    nearline: list = field(default_factory=list)   # 接近门槛的
    closed: list = field(default_factory=list)     # 本轮关闭的分支
    blocker: list = field(default_factory=list)    # 本轮发现的阻碍
    next_question: str = ""          # 下一轮的结构性问题

    # 统计
    total_tested: int = 0
    passed_is: int = 0
    passed_self: int = 0

    # 失败分类
    quality_failures: int = 0
    correlation_failures: int = 0
    threshold_failures: int = 0
    infrastructure_failures: int = 0

    # 决策
    decision: str = "unknown"        # green/yellow/red/black
    decision_reason: str = ""

    # 时间
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ResearchLedger:
    """研究总账 — 持久化记录每轮研究"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "brain.db")
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS research_ledger (
                round_id TEXT PRIMARY KEY,
                contract_id TEXT,
                structural_question TEXT,
                winner_id TEXT,
                winner_sharpe REAL,
                winner_expression TEXT,
                nearline_count INTEGER DEFAULT 0,
                closed_count INTEGER DEFAULT 0,
                blocker_count INTEGER DEFAULT 0,
                total_tested INTEGER DEFAULT 0,
                quality_failures INTEGER DEFAULT 0,
                correlation_failures INTEGER DEFAULT 0,
                threshold_failures INTEGER DEFAULT 0,
                infrastructure_failures INTEGER DEFAULT 0,
                decision TEXT DEFAULT 'unknown',
                decision_reason TEXT,
                next_question TEXT,
                data_json TEXT DEFAULT '{}',
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # 失败记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS failure_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT,
                alpha_id TEXT,
                expression TEXT,
                failure_type TEXT,
                sharpe REAL,
                fitness REAL,
                self_corr REAL,
                prod_corr REAL,
                details TEXT,
                recorded_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()

    def save_round(self, round_: ResearchRound):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO research_ledger
            (round_id, contract_id, structural_question, winner_id, winner_sharpe,
             winner_expression, nearline_count, closed_count, blocker_count,
             total_tested, quality_failures, correlation_failures,
             threshold_failures, infrastructure_failures, decision,
             decision_reason, next_question, data_json, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            round_.round_id, round_.contract_id, round_.structural_question,
            round_.winner.get('alpha_id') if round_.winner else None,
            round_.winner.get('sharpe') if round_.winner else None,
            round_.winner.get('expression') if round_.winner else None,
            len(round_.nearline), len(round_.closed), len(round_.blocker),
            round_.total_tested, round_.quality_failures,
            round_.correlation_failures, round_.threshold_failures,
            round_.infrastructure_failures, round_.decision,
            round_.decision_reason, round_.next_question,
            json.dumps(round_.to_dict(), ensure_ascii=False),
            round_.started_at, round_.finished_at
        ))
        conn.commit()
        conn.close()

    def log_failure(self, round_id: str, alpha: dict, failure_type: str):
        """记录失败Alpha"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO failure_log
            (round_id, alpha_id, expression, failure_type, sharpe, fitness,
             self_corr, prod_corr, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            round_id, alpha.get('alpha_id', ''),
            alpha.get('expression', ''),
            failure_type,
            alpha.get('sharpe', 0),
            alpha.get('fitness', 0),
            alpha.get('self_correlation'),
            alpha.get('prod_correlation'),
            json.dumps({k: str(v)[:200] for k, v in alpha.items()},
                      ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

    def get_rounds(self, limit: int = 20) -> list[dict]:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM research_ledger ORDER BY created_at DESC LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_failures(self, failure_type: str = None, limit: int = 50) -> list[dict]:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if failure_type:
            rows = conn.execute(
                "SELECT * FROM failure_log WHERE failure_type=? "
                "ORDER BY recorded_at DESC LIMIT ?",
                (failure_type, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM failure_log ORDER BY recorded_at DESC LIMIT ?",
                (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_summary(self) -> dict:
        """总账摘要"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM research_ledger").fetchone()[0]
        green = conn.execute(
            "SELECT COUNT(*) FROM research_ledger WHERE decision='green'").fetchone()[0]
        winners = conn.execute(
            "SELECT COUNT(*) FROM research_ledger WHERE winner_id IS NOT NULL").fetchone()[0]
        total_failures = conn.execute(
            "SELECT COUNT(*) FROM failure_log").fetchone()[0]
        fail_by_type = {}
        for row in conn.execute(
            "SELECT failure_type, COUNT(*) as cnt FROM failure_log GROUP BY failure_type"
        ).fetchall():
            fail_by_type[row[0]] = row[1]
        conn.close()
        return {
            "total_rounds": total,
            "green_rounds": green,
            "rounds_with_winner": winners,
            "total_failures_logged": total_failures,
            "failures_by_type": fail_by_type
        }


# 全局实例
ledger = ResearchLedger()
