"""通用 JSON 文件存储引擎 — 替代 SQLite 的轻量级持久化层"""
import json
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Any


_lock = threading.Lock()


class JsonStore:
    """单个 JSON 文件的读写管理器

    特性：
    - 内存缓存（首次 load 后驻留内存）
    - 原子写入（tmp + rename）
    - 线程安全（threading.Lock）
    """

    def __init__(self, filepath: Path | str, default_factory=None):
        self.filepath = Path(filepath)
        self._default_factory = default_factory or (lambda: {"_meta": {"version": 1, "updated_at": ""}, "entries": {}})
        self._cache: dict | None = None

    def load(self) -> dict:
        if self._cache is not None:
            return self._cache
        if self.filepath.exists():
            text = self.filepath.read_text(encoding="utf-8")
            self._cache = json.loads(text) if text.strip() else self._default_factory()
        else:
            self._cache = self._default_factory()
        return self._cache

    def save(self):
        with _lock:
            data = self._cache if self._cache is not None else self._default_factory()
            if "_meta" in data:
                data["_meta"]["updated_at"] = datetime.now().isoformat()
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.filepath.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.rename(str(tmp), str(self.filepath))

    def invalidate(self):
        self._cache = None

    def reload(self) -> dict:
        self._cache = None
        return self.load()


STATE_DIR = Path(__file__).parent.parent / "state"
RUNTIME_DIR = STATE_DIR / "_runtime"


def _default_dict():
    return {"_meta": {"version": 1, "updated_at": ""}, "entries": {}}


def _default_list():
    return {"_meta": {"version": 1, "next_id": 1, "updated_at": ""}, "items": []}


def _default_rounds():
    return {"_meta": {"version": 1, "updated_at": ""}, "rounds": {}}


# 预定义的全局 store 实例
alphas_store = JsonStore(STATE_DIR / "alphas.json", _default_dict)
experiments_store = JsonStore(STATE_DIR / "experiments.json", _default_list)
knowledge_events_store = JsonStore(STATE_DIR / "knowledge_events.json", _default_list)
rule_changes_store = JsonStore(STATE_DIR / "rule_changes.json", _default_list)
research_ledger_store = JsonStore(STATE_DIR / "research_ledger.json", _default_rounds)
failure_log_store = JsonStore(STATE_DIR / "failure_log.json", _default_list)
datasets_store = JsonStore(STATE_DIR / "datasets.json", _default_dict)
valid_fields_store = JsonStore(STATE_DIR / "valid_fields.json", _default_dict)
tasks_store = JsonStore(RUNTIME_DIR / "tasks.json", _default_list)
workers_store = JsonStore(RUNTIME_DIR / "workers.json", _default_dict)


def ensure_state_dir():
    """确保 state 目录和所有文件存在"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    for store in [alphas_store, experiments_store, knowledge_events_store,
                  rule_changes_store, research_ledger_store, failure_log_store,
                  datasets_store, valid_fields_store, tasks_store, workers_store]:
        if not store.filepath.exists():
            store.load()
            store.save()
