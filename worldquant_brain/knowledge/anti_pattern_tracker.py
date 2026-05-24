"""反模式追踪器 — 记录失败模式，防止重复尝试已知死胡同"""
import re
import json
from pathlib import Path
from typing import Optional

from worldquant_brain.db.json_store import knowledge_events_store


class AntiPatternTracker:
    """追踪和检测反模式（已知会失败的表达式结构）

    反模式来源：
    1. 多次回测失败的表达式结构聚类
    2. AI 手动标记的死胡同
    3. 提交被拒绝的模式
    """

    def __init__(self, project_root: str | Path = None):
        pass

    def record_failure(self, expression: str, dataset: str,
                       sharpe: float, failure_type: str,
                       context: dict = None):
        """记录一次失败（自动检测是否形成反模式）"""
        pattern = self._extract_pattern(expression, dataset)
        data = knowledge_events_store.load()
        eid = data["_meta"]["next_id"]
        data["items"].append({
            "id": eid,
            "event_type": "failure",
            "source": "anti_pattern_tracker",
            "content": {
                "expression": expression,
                "dataset": dataset,
                "sharpe": sharpe,
                "failure_type": failure_type,
                "pattern": pattern,
                **(context or {}),
            },
            "confidence": 0.3,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        })
        data["_meta"]["next_id"] = eid + 1
        knowledge_events_store.save()

        self._check_pattern_threshold(pattern)

    def should_skip(self, expression: str, dataset: str = None) -> bool:
        """检查候选表达式是否匹配已知反模式"""
        patterns = self._get_active_patterns()
        candidate_sig = self._extract_pattern(expression, dataset)

        for ap in patterns:
            content = ap.get("content", {})
            ap_pattern = content.get("pattern", "")
            if self._matches_pattern(candidate_sig, ap_pattern):
                return True
        return False

    def get_skip_reason(self, expression: str, dataset: str = None) -> Optional[str]:
        """返回跳过原因（如果匹配反模式）"""
        patterns = self._get_active_patterns()
        candidate_sig = self._extract_pattern(expression, dataset)

        for ap in patterns:
            content = ap.get("content", {})
            ap_pattern = content.get("pattern", "")
            if self._matches_pattern(candidate_sig, ap_pattern):
                return f"匹配反模式: {ap_pattern} (confidence={ap.get('confidence', 0):.2f})"
        return None

    def get_all_patterns(self) -> list[dict]:
        """获取所有活跃的反模式"""
        return self._get_active_patterns()

    def add_manual_pattern(self, pattern: str, reason: str,
                           confidence: float = 0.9):
        """AI手动添加反模式（如已知的API限制、无效字段等）"""
        data = knowledge_events_store.load()
        eid = data["_meta"]["next_id"]
        data["items"].append({
            "id": eid,
            "event_type": "anti_pattern",
            "source": "manual",
            "content": {
                "pattern": pattern,
                "reason": reason,
                "evidence": ["manual_observation"],
                "evidence_count": 1,
            },
            "confidence": confidence,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        })
        data["_meta"]["next_id"] = eid + 1
        knowledge_events_store.save()

    def _get_active_patterns(self) -> list[dict]:
        """获取所有置信度>=0.6的反模式"""
        data = knowledge_events_store.load()
        patterns = [e for e in data["items"]
                    if e.get("event_type") == "anti_pattern" and e.get("confidence", 0) >= 0.6]
        return [{"content": e.get("content", {}), "confidence": e.get("confidence", 0)}
                for e in patterns]

    def _check_pattern_threshold(self, pattern: str):
        """检查某模式的失败次数是否达到阈值（5次），如果是则升级为反模式"""
        data = knowledge_events_store.load()
        failures = [e for e in data["items"] if e.get("event_type") == "failure"]
        failures = failures[-200:]

        pattern_count = 0
        evidence = []
        for f in failures:
            content = f.get("content", {})
            if content.get("pattern") == pattern:
                pattern_count += 1
                evidence.append(content.get("expression", "")[:60])

        if pattern_count >= 5:
            existing = self._get_active_patterns()
            for ap in existing:
                if ap["content"].get("pattern") == pattern:
                    return

            confidence = min(0.6 + (pattern_count - 5) * 0.05, 0.95)
            eid = data["_meta"]["next_id"]
            data["items"].append({
                "id": eid,
                "event_type": "anti_pattern",
                "source": "auto_detection",
                "content": {
                    "pattern": pattern,
                    "evidence": evidence[:10],
                    "evidence_count": pattern_count,
                    "reason": f"连续{pattern_count}次失败",
                },
                "confidence": confidence,
                "created_at": __import__("datetime").datetime.now().isoformat(),
            })
            data["_meta"]["next_id"] = eid + 1
            knowledge_events_store.save()

    def _extract_pattern(self, expression: str, dataset: str = None) -> str:
        """从表达式中提取结构性模式签名"""
        sig = expression
        sig = re.sub(r'\b[a-z][a-z_]*[0-9]*(?:_[a-z]+)*\b(?=\s*[,)])',
                     '{field}', sig)

        def classify_window(m):
            val = int(m.group(1))
            if val <= 10:
                return 'short'
            elif val <= 66:
                return 'medium'
            elif val <= 252:
                return 'long'
            else:
                return 'very_long'

        sig = re.sub(r'\b(\d+)\b', lambda m: classify_window(m) if int(m.group(1)) > 2 else m.group(0), sig)

        if dataset:
            sig = f"{dataset}::{sig}"

        return sig

    @staticmethod
    def _matches_pattern(candidate_sig: str, anti_pattern: str) -> bool:
        """检查候选签名是否匹配反模式"""
        if not anti_pattern:
            return False
        if candidate_sig == anti_pattern:
            return True
        if "::" in anti_pattern:
            ap_dataset = anti_pattern.split("::")[0]
            cand_dataset = candidate_sig.split("::")[0] if "::" in candidate_sig else ""
            if ap_dataset == cand_dataset:
                ap_struct = anti_pattern.split("::", 1)[1]
                cand_struct = candidate_sig.split("::", 1)[1] if "::" in candidate_sig else candidate_sig
                if ap_struct in cand_struct or cand_struct in ap_struct:
                    return True
        return False
