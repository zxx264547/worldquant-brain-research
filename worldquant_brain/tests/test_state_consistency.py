#!/usr/bin/env python3
"""框架状态一致性测试 — 验证 2026-08 感知链路修复

覆盖：
1. status 语义：'ok'（历史）/ 'done'（当前）兼容读取，写入归一化
2. unified_store.perceive() 统计正确性（不再返回全 0）
3. result_store 统一走 JSON 后端（不再读废弃的 SQLite brain.db）
4. 任务队列：崩溃恢复（running→queued）+ 清理

隔离策略：每个测试把全部 JsonStore 实例重定向到临时目录，
测试结束后恢复真实路径，不污染 state/*.json。
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.db import repository
from worldquant_brain.db.json_store import (
    alphas_store, tasks_store, workers_store, knowledge_events_store,
    experiments_store, datasets_store, valid_fields_store,
    rule_changes_store, research_ledger_store, failure_log_store,
)
from worldquant_brain.db.repository import (
    save_alpha, get_best_alphas, get_submittable, count_alphas,
    recover_stale_tasks, clean_tasks, push_task, STATUS_DONE, STATUS_OK,
)
from worldquant_brain.engine.result_store import store
from worldquant_brain.knowledge.unified_store import UnifiedKnowledgeStore

_ALL_STORES = [
    alphas_store, tasks_store, workers_store, knowledge_events_store,
    experiments_store, datasets_store, valid_fields_store,
    rule_changes_store, research_ledger_store, failure_log_store,
]
_ORIGINAL_PATHS = {}


def _make_alpha(expr: str, sharpe: float, status: str = STATUS_DONE) -> dict:
    return {
        'alpha_id': f'ID_{abs(hash(expr)) % 100000}',
        'expression': expr,
        'sharpe': sharpe,
        'fitness': 1.0,
        'ppc': 0.1,
        'margin': 0.05,
        'turnover': 0.02,
        'name': f'alpha_{sharpe:.2f}',
        'status': status,
    }


def setup_function():
    """重定向所有 store 到临时目录"""
    tmp = Path(tempfile.mkdtemp(prefix="wq_test_"))
    for s in _ALL_STORES:
        _ORIGINAL_PATHS[s] = s.filepath  # store 对象本身作 key
        s.filepath = tmp / s.filepath.name
        s.invalidate()
    repository.ensure_state_dir()


def teardown_function():
    """恢复真实路径"""
    for obj, path in _ORIGINAL_PATHS.items():
        obj.filepath = path
        obj.invalidate()
    _ORIGINAL_PATHS.clear()


# ─── 1. status 语义 ───

def test_save_alpha_normalizes_status_ok_to_done():
    """写入 status='ok' 的旧式数据应归一化为 'done'"""
    assert save_alpha(_make_alpha('rank(close)', 0.5, status=STATUS_OK))
    data = alphas_store.load()
    entry = list(data["entries"].values())[0]
    assert entry["status"] == STATUS_DONE
    assert count_alphas() == 1


def test_get_best_alphas_accepts_legacy_ok():
    """读取端必须兼容历史 status='ok' 条目"""
    save_alpha(_make_alpha('rank(close)', 1.0, status=STATUS_OK))
    save_alpha(_make_alpha('zscore(close)', 2.0, status=STATUS_DONE))
    best = get_best_alphas(10)
    assert len(best) == 2
    assert best[0]["sharpe"] == 2.0  # done 且更高


# ─── 2. perceive 统计 ───

def test_perceive_reports_real_stats():
    """perceive 必须返回真实统计（修复前返回全 0）"""
    save_alpha(_make_alpha('a', 1.6, status=STATUS_OK))    # 旧式 → 可提交
    save_alpha(_make_alpha('b', 0.8, status=STATUS_DONE))
    save_alpha(_make_alpha('c', 2.5, status=STATUS_DONE))  # 可提交

    state = UnifiedKnowledgeStore().perceive()
    prog = state["research_progress"]
    assert prog["total_tested"] == 3
    assert prog["best_sharpe"] == 2.5
    assert prog["submittable_count"] == 2  # 1.6 和 2.5
    assert prog["avg_sharpe"] == round((1.6 + 0.8 + 2.5) / 3, 3)


# ─── 3. result_store 统一 JSON 后端 ───

def test_result_store_uses_json_backend():
    """result_store 必须与 repository 读同一份 JSON 数据"""
    save_alpha(_make_alpha('d', 1.9, status=STATUS_DONE))
    save_alpha(_make_alpha('e', 1.7, status=STATUS_DONE))

    assert store.count == count_alphas() == 2
    assert [a["id"] for a in store.best(5)] == \
           [a["id"] for a in get_best_alphas(5)]
    assert len(store.submittable()) == len(get_submittable()) == 2
    assert store.exists('d', {}) is not None  # 哈希去重基于表达式


# ─── 4. 任务队列恢复与清理 ───

def test_recover_stale_tasks_resets_running():
    """崩溃恢复：running → queued，worker_id 清空"""
    tid = push_task('test_strategy', 'rank(close)')
    tasks = tasks_store.load()
    tasks["items"][0]["status"] = "running"
    tasks["items"][0]["worker_id"] = "worker_1"
    tasks_store.save()

    recovered = recover_stale_tasks()
    assert recovered == 1
    t = tasks_store.load()["items"][0]
    assert t["status"] == "queued"
    assert t["worker_id"] is None


def test_clean_tasks_keeps_done_only():
    """清理 failed+running，保留 done（queued 也不删）"""
    tid1 = push_task('s', 'expr1')
    tid2 = push_task('s', 'expr2')
    tid3 = push_task('s', 'expr3')
    tasks = tasks_store.load()
    by_id = {t["id"]: t for t in tasks["items"]}
    by_id[tid1]["status"] = "running"   # 僵尸
    by_id[tid2]["status"] = "failed"    # 失败
    by_id[tid3]["status"] = "done"      # 保留
    tasks_store.save()

    removed = clean_tasks(("failed", "running"))
    assert removed == 2
    remaining = [t["status"] for t in tasks_store.load()["items"]]
    assert remaining == ["done"]


if __name__ == "__main__":
    # 手动运行入口
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        setup_function()
        fn()
        teardown_function()
        print(f"  ✓ {fn.__name__}")
    print("All state consistency tests passed!")
