#!/usr/bin/env python3
"""Repository 测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.db.repository import (
    init_db, save_alpha, find_by_expression, get_best_alphas,
    count_alphas, hash_expression
)


def test_save_and_find():
    """测试保存和查询"""
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
    h1 = hash_expression('rank(close)')
    h2 = hash_expression('rank(close)')
    assert h1 == h2
    assert len(h1) == 16


def test_best_alphas():
    """测试最佳查询"""
    best = get_best_alphas(5)
    assert len(best) <= 5
    for a in best:
        assert a['sharpe'] >= 1.0


if __name__ == "__main__":
    test_save_and_find()
    test_hash_consistency()
    test_best_alphas()
    print("All repository tests passed!")
