"""统一知识存储 — 包装所有知识后端，提供单一读写接口"""
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager


class UnifiedKnowledgeStore:
    """AI认知循环的统一知识访问层

    包装现有存储后端（brain.db, forum.sqlite3, markdown files），
    不迁移底层数据，只提供统一的读写接口。
    """

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.brain_db_path = self.root / "worldquant_brain" / "data" / "brain.db"
        self.forum_db_path = self.root / "worldquant_brain" / "data" / "forum.sqlite3"
        self.memory_dir = self.root / "worldquant_brain" / "knowledge_base" / "memory"
        self.agent_memory_dir = self.root / ".claude" / "agent-memory"
        self._ensure_schema()

    @contextmanager
    def _brain_conn(self):
        self.brain_db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.brain_db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self):
        """确保所有表和列存在（幂等）"""
        # 先确保基础 schema 存在
        base_schema = self.root / "worldquant_brain" / "db" / "schema.sql"
        with self._brain_conn() as conn:
            if base_schema.exists():
                conn.executescript(base_schema.read_text())
            conn.executescript(SCHEMA_EXTENSIONS)
            # alphas 表列扩展（忽略已存在的错误）
            for sql in ALPHAS_COLUMN_MIGRATIONS:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass  # 列已存在，跳过

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
        with self._brain_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total,
                       MAX(sharpe) as best_sharpe,
                       AVG(sharpe) as avg_sharpe,
                       SUM(CASE WHEN is_submittable=1 THEN 1 ELSE 0 END) as submittable
                FROM alphas WHERE status='done'
            """).fetchone()
            if row and row['total'] > 0:
                return {
                    "total_tested": row['total'],
                    "best_sharpe": round(row['best_sharpe'] or 0, 3),
                    "avg_sharpe": round(row['avg_sharpe'] or 0, 3),
                    "submittable_count": row['submittable'] or 0,
                    "target_sharpe": 1.58,
                }
            return {"total_tested": 0, "best_sharpe": 0, "avg_sharpe": 0,
                    "submittable_count": 0, "target_sharpe": 1.58}

    def _get_recent_insights(self, limit: int = 10) -> list[dict]:
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM knowledge_events
                WHERE event_type = 'insight'
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [{"source": r['source'], "content": json.loads(r['content_json']),
                     "confidence": r['confidence'], "created_at": r['created_at']}
                    for r in rows]

    def _get_strategy_effectiveness(self) -> dict:
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT strategy, COUNT(*) as runs,
                       AVG(best_sharpe) as avg_best,
                       MAX(best_sharpe) as max_best
                FROM experiments WHERE status='done'
                GROUP BY strategy ORDER BY avg_best DESC
            """).fetchall()
            return {r['strategy']: {"runs": r['runs'], "avg_best": round(r['avg_best'] or 0, 3),
                                     "max_best": round(r['max_best'] or 0, 3)}
                    for r in rows}

    def _count_anti_patterns(self) -> int:
        with self._brain_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) FROM knowledge_events
                WHERE event_type = 'anti_pattern'
            """).fetchone()
            return row[0] if row else 0

    def _get_submit_summary(self) -> dict:
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT submit_status, COUNT(*) as cnt
                FROM alphas WHERE submit_status IS NOT NULL
                GROUP BY submit_status
            """).fetchall()
            summary = {"submitted": 0, "accepted": 0, "rejected": 0}
            for r in rows:
                if r['submit_status'] in summary:
                    summary[r['submit_status']] = r['cnt']
            return summary

    def _get_pending_rules(self) -> list[dict]:
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM rule_changes WHERE status = 'proposed'
                ORDER BY created_at DESC LIMIT 5
            """).fetchall()
            return [dict(r) for r in rows]

    def _get_last_event_time(self, event_type: str) -> Optional[str]:
        with self._brain_conn() as conn:
            row = conn.execute("""
                SELECT created_at FROM knowledge_events
                WHERE event_type = ? ORDER BY created_at DESC LIMIT 1
            """, (event_type,)).fetchone()
            return row['created_at'] if row else None

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
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM knowledge_events
                WHERE content_json LIKE ?
                ORDER BY confidence DESC, created_at DESC LIMIT ?
            """, (f"%{query}%", limit)).fetchall()
            return [{"source": "knowledge_events", "type": r['event_type'],
                     "content": json.loads(r['content_json']),
                     "confidence": r['confidence'], "relevance": r['confidence']}
                    for r in rows]

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
        with self._brain_conn() as conn:
            conn.execute("""
                UPDATE alphas SET submit_status=?, submit_date=datetime('now'),
                reject_reason=? WHERE id=?
            """, (result, reason, alpha_id))

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
        with self._brain_conn() as conn:
            cur = conn.execute("""
                INSERT INTO rule_changes (rule_type, old_value, new_value, reason, evidence_ids)
                VALUES (?, ?, ?, ?, ?)
            """, (rule_type, old_value, new_value, reason,
                  json.dumps(evidence_ids or [])))
            return cur.lastrowid

    def approve_rule_change(self, rule_id: int):
        """批准规则修改"""
        with self._brain_conn() as conn:
            conn.execute("""
                UPDATE rule_changes SET status='approved' WHERE id=?
            """, (rule_id,))

    def apply_rule_change(self, rule_id: int):
        """标记规则已应用"""
        with self._brain_conn() as conn:
            conn.execute("""
                UPDATE rule_changes SET status='applied' WHERE id=?
            """, (rule_id,))

    def _record_event(self, event_type: str, source: str,
                      content: dict, confidence: float) -> int:
        with self._brain_conn() as conn:
            cur = conn.execute("""
                INSERT INTO knowledge_events (event_type, source, content_json, confidence)
                VALUES (?, ?, ?, ?)
            """, (event_type, source, json.dumps(content, ensure_ascii=False), confidence))
            return cur.lastrowid

    # ═══════════════════════════════════════════
    #  QUERY — 特定查询
    # ═══════════════════════════════════════════

    def get_anti_patterns(self, min_confidence: float = 0.6) -> list[dict]:
        """获取所有反模式"""
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT content_json, confidence, created_at FROM knowledge_events
                WHERE event_type = 'anti_pattern' AND confidence >= ?
                ORDER BY confidence DESC
            """, (min_confidence,)).fetchall()
            return [{"content": json.loads(r['content_json']),
                     "confidence": r['confidence'], "created_at": r['created_at']}
                    for r in rows]

    def get_submit_patterns(self, min_count: int = 3) -> dict:
        """分析提交结果的模式（用于驱动规则进化）"""
        with self._brain_conn() as conn:
            rows = conn.execute("""
                SELECT submit_status, sharpe, fitness, ppc, margin, turnover, reject_reason
                FROM alphas WHERE submit_status IS NOT NULL
            """).fetchall()
            if not rows:
                return {"total": 0, "patterns": []}

            accepted = [dict(r) for r in rows if r['submit_status'] == 'accepted']
            rejected = [dict(r) for r in rows if r['submit_status'] == 'rejected']

            patterns = {
                "total": len(rows),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "accepted_sharpe_range": self._range_stats(accepted, 'sharpe'),
                "rejected_sharpe_range": self._range_stats(rejected, 'sharpe'),
                "rejection_reasons": self._count_reasons(rejected),
            }
            return patterns

    def get_knowledge_events_since(self, since: str, event_type: str = None) -> list[dict]:
        """获取某时间后的所有知识事件"""
        with self._brain_conn() as conn:
            if event_type:
                rows = conn.execute("""
                    SELECT * FROM knowledge_events
                    WHERE created_at > ? AND event_type = ?
                    ORDER BY created_at DESC
                """, (since, event_type)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM knowledge_events WHERE created_at > ?
                    ORDER BY created_at DESC
                """, (since,)).fetchall()
            return [{"id": r['id'], "type": r['event_type'], "source": r['source'],
                     "content": json.loads(r['content_json']),
                     "confidence": r['confidence'], "created_at": r['created_at']}
                    for r in rows]

    @staticmethod
    def _range_stats(items: list[dict], field: str) -> dict:
        if not items:
            return {"min": 0, "max": 0, "avg": 0}
        values = [i[field] for i in items if i.get(field) is not None]
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


# ─── Schema 扩展 SQL（幂等）───

SCHEMA_EXTENSIONS = """
-- 提交结果追踪（给 alphas 表加列，忽略已存在的错误）
CREATE TABLE IF NOT EXISTS _migration_check (id INTEGER PRIMARY KEY);

-- 知识事件日志
CREATE TABLE IF NOT EXISTS knowledge_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    content_json TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ke_type ON knowledge_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ke_created ON knowledge_events(created_at);
CREATE INDEX IF NOT EXISTS idx_ke_confidence ON knowledge_events(confidence);

-- 规则变更历史
CREATE TABLE IF NOT EXISTS rule_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    evidence_ids TEXT DEFAULT '[]',
    status TEXT DEFAULT 'proposed',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rc_status ON rule_changes(status);
"""

# alphas 表的列扩展需要单独处理（SQLite 不支持 IF NOT EXISTS 对列）
ALPHAS_COLUMN_MIGRATIONS = [
    "ALTER TABLE alphas ADD COLUMN submit_status TEXT",
    "ALTER TABLE alphas ADD COLUMN submit_date TEXT",
    "ALTER TABLE alphas ADD COLUMN reject_reason TEXT",
]
