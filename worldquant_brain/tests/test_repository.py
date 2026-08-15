#!/usr/bin/env python3
"""Repository 测试（隔离：重定向到临时 state，不污染真实数据）"""

import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.db.json_store import (
    alphas_store, tasks_store, workers_store, knowledge_events_store,
    experiments_store, datasets_store, valid_fields_store,
    rule_changes_store, research_ledger_store, failure_log_store,
)
from worldquant_brain.db.repository import (
    init_db, save_alpha, find_by_expression, get_best_alphas,
    count_alphas, hash_expression
)

_ALL_STORES = [
    alphas_store, tasks_store, workers_store, knowledge_events_store,
    experiments_store, datasets_store, valid_fields_store,
    rule_changes_store, research_ledger_store, failure_log_store,
]
_ORIGINAL_PATHS = {}


def _isolate_state():
    """把全部 store 重定向到临时目录（幂等：首次调用）"""
    if _ORIGINAL_PATHS:
        return
    tmp = Path(tempfile.mkdtemp(prefix="wq_test_repo_"))
    for s in _ALL_STORES:
        _ORIGINAL_PATHS[s] = s.filepath
        s.filepath = tmp / s.filepath.name
        s.invalidate()


def _restore_state():
    for obj, path in _ORIGINAL_PATHS.items():
        obj.filepath = path
        obj.invalidate()
    _ORIGINAL_PATHS.clear()


def test_save_and_find():
    """测试保存和查询"""
    _isolate_state()
    init_db()

    alpha = {
        'alpha_id': 'TEST001',
        'expression': 'rank(ts_mean(close, 20))',
        'sharpe': 1.5,
        'fitness': 2.0,
        'ppc': 0.3,
        'margin': 0.1,
        'turnover': 0.05,
        'name': 'test_alpha',
        'status': 'done',
    }

    # 保存
    assert save_alpha(alpha)

    # 查重
    assert save_alpha(alpha) == False  # duplicate

    # 查询
    found = find_by_expression('rank(ts_mean(close, 20))')
    assert found is not None
    assert found['sharpe'] == 1.5
    assert found['name'] == 'test_alpha'


def test_hash_consistency():
    """测试哈希一致性"""
    _isolate_state()
    h1 = hash_expression('rank(close)')
    h2 = hash_expression('rank(close)')
    assert h1 == h2
    assert len(h1) == 16


def test_best_alphas():
    """测试最佳查询"""
    _isolate_state()
    best = get_best_alphas(5)
    assert len(best) <= 5
    for a in best:
        assert a['sharpe'] >= 1.0


if __name__ == "__main__":
    try:
        test_save_and_find()
        test_hash_consistency()
        test_best_alphas()
        print("All repository tests passed!")
    finally:
        _restore_state()
