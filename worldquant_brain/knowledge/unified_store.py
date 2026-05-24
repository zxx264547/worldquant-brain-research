"""统一知识存储 — 包装所有知识后端，提供单一读写接口"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

from worldquant_brain.db.json_store import (
    alphas_store, experiments_store, knowledge_events_store,
    rule_changes_store, ensure_state_dir,
)


class UnifiedKnowledgeStore:
    """AI认知循环的统一知识访问层

    使用 JSON 文件作为主存储后端，forum.sqlite3 仅用于论坛搜索。
    """

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.forum_db_path = self.root / "worldquant_brain" / "data" / "forum.sqlite3"
        self.memory_dir = self.root / "worldquant_brain" / "knowledge_base" / "memory"
        self.agent_memory_dir = self.root / ".claude" / "agent-memory"
        ensure_state_dir()

    # ═══════════════════════════════════════════
    #  PERCEIVE — 感知当前全局状态
    # ═══════════════════════════════════════════

    def perceive(self) -> dict:
        """聚合所有来源的当前状态，供AI决策"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "research_progress": self._get_research_progress(),
            "recent_insights": self._get_recent_insights(limit=10),
            "strategy_effectiveness": self._get_strategy_effectiveness(),
            "anti_patterns_count": self._count_anti_patterns(),
            "submit_outcomes": self._get_submit_summary(),
            "pending_rule_changes": self._get_pending_rules(),
            "last_forum_sync": self._get_last_event_time("forum_sync"),
            "last_evolve": self._get_last_event_time("evolve"),
        }
        return state

    def _get_research_progress(self) -> dict:
        data = alphas_store.load()
        entries = [e for e in data["entries"].values() if e.get("status") == "done"]
        if entries:
            sharpes = [e.get("sharpe", 0) for e in entries]
            submittable = sum(1 for e in entries if e.get("is_submittable") == 1)
            return {
                "total_tested": len(entries),
                "best_sharpe": round(max(sharpes), 3),
                "avg_sharpe": round(sum(sharpes) / len(sharpes), 3),
                "submittable_count": submittable,
                "target_sharpe": 1.58,
            }
        return {"total_tested": 0, "best_sharpe": 0, "avg_sharpe": 0,
                "submittable_count": 0, "target_sharpe": 1.58}

    def _get_recent_insights(self, limit: int = 10) -> list[dict]:
        data = knowledge_events_store.load()
        insights = [e for e in data["items"] if e.get("event_type") == "insight"]
        insights.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [{"source": e.get("source", ""), "content": e.get("content", {}),
                 "confidence": e.get("confidence", 0), "created_at": e.get("created_at", "")}
                for e in insights[:limit]]

    def _get_strategy_effectiveness(self) -> dict:
        data = experiments_store.load()
        done = [e for e in data["items"] if e.get("status") == "done"]
        by_strategy = {}
        for exp in done:
            s = exp.get("strategy", "unknown")
            if s not in by_strategy:
                by_strategy[s] = {"runs": 0, "sharpes": []}
            by_strategy[s]["runs"] += 1
            by_strategy[s]["sharpes"].append(exp.get("best_sharpe", 0))
        return {s: {"runs": v["runs"],
                    "avg_best": round(sum(v["sharpes"]) / len(v["sharpes"]), 3) if v["sharpes"] else 0,
                    "max_best": round(max(v["sharpes"]), 3) if v["sharpes"] else 0}
                for s, v in by_strategy.items()}

    def _count_anti_patterns(self) -> int:
        data = knowledge_events_store.load()
        return sum(1 for e in data["items"] if e.get("event_type") == "anti_pattern")

    def _get_submit_summary(self) -> dict:
        data = alphas_store.load()
        summary = {"submitted": 0, "accepted": 0, "rejected": 0}
        for e in data["entries"].values():
            status = e.get("submit_status")
            if status and status in summary:
                summary[status] += 1
        return summary

    def _get_pending_rules(self) -> list[dict]:
        data = rule_changes_store.load()
        pending = [r for r in data["items"] if r.get("status") == "proposed"]
        pending.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return pending[:5]

    def _get_last_event_time(self, event_type: str) -> Optional[str]:
        data = knowledge_events_store.load()
        events = [e for e in data["items"] if e.get("event_type") == event_type]
        if events:
            events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return events[0].get("created_at")
        return None

    # ═══════════════════════════════════════════
    #  SEARCH — 跨源搜索
    # ═══════════════════════════════════════════

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """跨所有知识源搜索"""
        results = []
        results.extend(self._search_knowledge_events(query, limit))
        results.extend(self._search_forum(query, limit))
        results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return results[:limit]

    def _search_knowledge_events(self, query: str, limit: int) -> list[dict]:
        data = knowledge_events_store.load()
        query_lower = query.lower()
        matched = []
        for e in data["items"]:
            content_str = json.dumps(e.get("content", {}), ensure_ascii=False).lower()
            if query_lower in content_str:
                matched.append({
                    "source": "knowledge_events",
                    "type": e.get("event_type", ""),
                    "content": e.get("content", {}),
                    "confidence": e.get("confidence", 0),
                    "relevance": e.get("confidence", 0),
                })
        matched.sort(key=lambda x: x["confidence"], reverse=True)
        return matched[:limit]

    def _search_forum(self, query: str, limit: int) -> list[dict]:
        """搜索论坛知识（如果forum.sqlite3存在）"""
        if not self.forum_db_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(self.forum_db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT slug, title, summary, confidence FROM knowledge_pages
                WHERE status = 'published' AND (title LIKE ? OR summary LIKE ?)
                ORDER BY confidence DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
            conn.close()
            return [{"source": "forum_rag", "slug": r['slug'], "title": r['title'],
                     "summary": r['summary'], "confidence": r['confidence'],
                     "relevance": r['confidence'] * 0.9}
                    for r in rows]
        except Exception:
            return []

    # ═══════════════════════════════════════════
    #  WRITE — 记录各类事件
    # ═══════════════════════════════════════════

    def record_insight(self, insight: str, source: str = "cognitive_loop",
                       confidence: float = 0.5, metadata: dict = None) -> int:
        """记录一条洞察到知识事件日志"""
        content = {"insight": insight}
        if metadata:
            content.update(metadata)
        return self._record_event("insight", source, content, confidence)

    def record_experiment(self, strategy: str, results_summary: dict,
                          source: str = "cognitive_loop") -> int:
        """记录实验结果"""
        content = {"strategy": strategy, **results_summary}
        confidence = min(results_summary.get("best_sharpe", 0) / 1.58, 1.0)
        return self._record_event("experiment", source, content, confidence)

    def record_submit_result(self, alpha_id: str, expression: str,
                             result: str, reason: str = None) -> int:
        """记录提交结果（accept/reject），驱动反馈回路"""
        from worldquant_brain.db.repository import update_alpha, find_by_hash, hash_alpha
        # 更新 alpha 记录
        data = alphas_store.load()
        for h, entry in data["entries"].items():
            if entry.get("id") == alpha_id:
                entry["submit_status"] = result
                entry["submit_date"] = datetime.now().isoformat()
                entry["reject_reason"] = reason
                alphas_store.save()
                break

        content = {"alpha_id": alpha_id, "expression": expression,
                   "result": result, "reason": reason}
        confidence = 1.0 if result == "accepted" else 0.8
        return self._record_event("submit", "brain_platform", content, confidence)

    def record_anti_pattern(self, pattern: str, evidence: list[str],
                            confidence: float = 0.7) -> int:
        """记录反模式"""
        content = {"pattern": pattern, "evidence": evidence,
                   "evidence_count": len(evidence)}
        return self._record_event("anti_pattern", "anti_pattern_tracker",
                                  content, confidence)

    def record_forum_sync(self, new_posts: int, new_pages: int) -> int:
        """记录论坛同步事件"""
        content = {"new_posts": new_posts, "new_pages": new_pages}
        return self._record_event("forum_sync", "forum_syncer", content, 1.0)

    def propose_rule_change(self, rule_type: str, old_value: str,
                            new_value: str, reason: str,
                            evidence_ids: list[int] = None) -> int:
        """提议规则修改（L2级别，需人工审批）"""
        data = rule_changes_store.load()
        rid = data["_meta"]["next_id"]
        data["items"].append({
            "id": rid,
            "rule_type": rule_type,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "evidence_ids": evidence_ids or [],
            "status": "proposed",
            "created_at": datetime.now().isoformat(),
        })
        data["_meta"]["next_id"] = rid + 1
        rule_changes_store.save()
        return rid

    def approve_rule_change(self, rule_id: int):
        """批准规则修改"""
        data = rule_changes_store.load()
        for r in data["items"]:
            if r["id"] == rule_id:
                r["status"] = "approved"
                break
        rule_changes_store.save()

    def apply_rule_change(self, rule_id: int):
        """标记规则已应用"""
        data = rule_changes_store.load()
        for r in data["items"]:
            if r["id"] == rule_id:
                r["status"] = "applied"
                break
        rule_changes_store.save()

    def _record_event(self, event_type: str, source: str,
                      content: dict, confidence: float) -> int:
        data = knowledge_events_store.load()
        eid = data["_meta"]["next_id"]
        data["items"].append({
            "id": eid,
            "event_type": event_type,
            "source": source,
            "content": content,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
        })
        data["_meta"]["next_id"] = eid + 1
        knowledge_events_store.save()
        return eid

    # ═══════════════════════════════════════════
    #  QUERY — 特定查询
    # ═══════════════════════════════════════════

    def get_anti_patterns(self, min_confidence: float = 0.6) -> list[dict]:
        """获取所有反模式"""
        data = knowledge_events_store.load()
        patterns = [e for e in data["items"]
                    if e.get("event_type") == "anti_pattern" and e.get("confidence", 0) >= min_confidence]
        patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return [{"content": e.get("content", {}),
                 "confidence": e.get("confidence", 0),
                 "created_at": e.get("created_at", "")}
                for e in patterns]

    def get_submit_patterns(self, min_count: int = 3) -> dict:
        """分析提交结果的模式（用于驱动规则进化）"""
        data = alphas_store.load()
        submitted = [e for e in data["entries"].values() if e.get("submit_status")]
        if not submitted:
            return {"total": 0, "patterns": []}

        accepted = [e for e in submitted if e.get("submit_status") == "accepted"]
        rejected = [e for e in submitted if e.get("submit_status") == "rejected"]

        return {
            "total": len(submitted),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "accepted_sharpe_range": self._range_stats(accepted, 'sharpe'),
            "rejected_sharpe_range": self._range_stats(rejected, 'sharpe'),
            "rejection_reasons": self._count_reasons(rejected),
        }

    def get_knowledge_events_since(self, since: str, event_type: str = None) -> list[dict]:
        """获取某时间后的所有知识事件"""
        data = knowledge_events_store.load()
        events = data["items"]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        events = [e for e in events if e.get("created_at", "") > since]
        events.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [{"id": e.get("id"), "type": e.get("event_type"), "source": e.get("source"),
                 "content": e.get("content", {}),
                 "confidence": e.get("confidence", 0), "created_at": e.get("created_at", "")}
                for e in events]

    @staticmethod
    def _range_stats(items: list[dict], field: str) -> dict:
        if not items:
            return {"min": 0, "max": 0, "avg": 0}
        values = [i.get(field, 0) for i in items if i.get(field) is not None]
        if not values:
            return {"min": 0, "max": 0, "avg": 0}
        return {"min": round(min(values), 3), "max": round(max(values), 3),
                "avg": round(sum(values) / len(values), 3)}

    @staticmethod
    def _count_reasons(rejected: list[dict]) -> dict:
        reasons = {}
        for r in rejected:
            reason = r.get('reject_reason', 'unknown') or 'unknown'
            reasons[reason] = reasons.get(reason, 0) + 1
        return reasons
