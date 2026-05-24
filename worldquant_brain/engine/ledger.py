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

from worldquant_brain.db.json_store import research_ledger_store, failure_log_store


@dataclass
class ResearchRound:
    """一轮研究的完整记录"""
    round_id: str
    contract_id: str
    structural_question: str

    winner: Optional[dict] = None
    nearline: list = field(default_factory=list)
    closed: list = field(default_factory=list)
    blocker: list = field(default_factory=list)
    next_question: str = ""

    total_tested: int = 0
    passed_is: int = 0
    passed_self: int = 0

    quality_failures: int = 0
    correlation_failures: int = 0
    threshold_failures: int = 0
    infrastructure_failures: int = 0

    decision: str = "unknown"
    decision_reason: str = ""

    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ResearchLedger:
    """研究总账 — 持久化记录每轮研究"""

    def __init__(self, db_path: str = None):
        self._ledger_store = research_ledger_store
        self._failure_store = failure_log_store
        self._ensure_files()

    def _ensure_files(self):
        self._ledger_store.load()
        self._failure_store.load()

    def save_round(self, round_: ResearchRound):
        data = self._ledger_store.load()
        data["rounds"][round_.round_id] = {
            "round_id": round_.round_id,
            "contract_id": round_.contract_id,
            "structural_question": round_.structural_question,
            "winner_id": round_.winner.get('alpha_id') if round_.winner else None,
            "winner_sharpe": round_.winner.get('sharpe') if round_.winner else None,
            "winner_expression": round_.winner.get('expression') if round_.winner else None,
            "nearline_count": len(round_.nearline),
            "closed_count": len(round_.closed),
            "blocker_count": len(round_.blocker),
            "total_tested": round_.total_tested,
            "quality_failures": round_.quality_failures,
            "correlation_failures": round_.correlation_failures,
            "threshold_failures": round_.threshold_failures,
            "infrastructure_failures": round_.infrastructure_failures,
            "decision": round_.decision,
            "decision_reason": round_.decision_reason,
            "next_question": round_.next_question,
            "data_json": round_.to_dict(),
            "started_at": round_.started_at,
            "finished_at": round_.finished_at,
            "created_at": datetime.now().isoformat(),
        }
        self._ledger_store.save()

    def log_failure(self, round_id: str, alpha: dict, failure_type: str):
        """记录失败Alpha"""
        data = self._failure_store.load()
        fid = data["_meta"]["next_id"]
        data["items"].append({
            "id": fid,
            "round_id": round_id,
            "alpha_id": alpha.get('alpha_id', ''),
            "expression": alpha.get('expression', ''),
            "failure_type": failure_type,
            "sharpe": alpha.get('sharpe', 0),
            "fitness": alpha.get('fitness', 0),
            "self_corr": alpha.get('self_correlation'),
            "prod_corr": alpha.get('prod_correlation'),
            "details": {k: str(v)[:200] for k, v in alpha.items()},
            "recorded_at": datetime.now().isoformat(),
        })
        data["_meta"]["next_id"] = fid + 1
        self._failure_store.save()

    def get_rounds(self, limit: int = 20) -> list[dict]:
        data = self._ledger_store.load()
        rounds = list(data["rounds"].values())
        rounds.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return rounds[:limit]

    def get_failures(self, failure_type: str = None, limit: int = 50) -> list[dict]:
        data = self._failure_store.load()
        items = data["items"]
        if failure_type:
            items = [f for f in items if f.get("failure_type") == failure_type]
        items.sort(key=lambda f: f.get("recorded_at", ""), reverse=True)
        return items[:limit]

    def get_summary(self) -> dict:
        """总账摘要"""
        data = self._ledger_store.load()
        rounds = list(data["rounds"].values())
        fail_data = self._failure_store.load()

        total = len(rounds)
        green = sum(1 for r in rounds if r.get("decision") == "green")
        winners = sum(1 for r in rounds if r.get("winner_id"))
        total_failures = len(fail_data["items"])

        fail_by_type = {}
        for f in fail_data["items"]:
            ft = f.get("failure_type", "unknown")
            fail_by_type[ft] = fail_by_type.get(ft, 0) + 1

        return {
            "total_rounds": total,
            "green_rounds": green,
            "rounds_with_winner": winners,
            "total_failures_logged": total_failures,
            "failures_by_type": fail_by_type,
        }


# 全局实例
ledger = ResearchLedger()
