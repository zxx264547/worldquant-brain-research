#!/usr/bin/env python3
"""ExpressionBuilder 测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.engine.expression_builder import (
    ExpressionBuilder, ExpressionTemplates
)


def test_eps_basic():
    """测试EPS基础表达式"""
    expr = ExpressionTemplates.eps_basic()
    expected = ("ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252)"
                ", 0.9), 3)")
    assert expr == expected, f"{expr} != {expected}"


def test_eps_momentum():
    """测试EPS+动量表达式"""
    expr = ExpressionTemplates.eps_with_momentum()
    assert "ts_mean(returns, 66)" in expr
    assert "actual_eps_value_quarterly" in expr


def test_builder_single_field():
    """测试单字段链式构建"""
    builder = ExpressionBuilder()
    expr = (builder.field('close').ts_mean(20).rank().build())
    assert expr == "rank(ts_mean(close, 20))"


def test_builder_nested():
    """测试嵌套算子"""
    builder = ExpressionBuilder()
    expr = (builder.field('returns')
            .ts_std_dev(66)
            .ts_mean(120)
            .rank()
            .build())
    assert expr == "rank(ts_mean(ts_std_dev(returns, 66), 120))"


def test_builder_multiply():
    """测试乘法组合"""
    builder = ExpressionBuilder()
    expr = (builder.field('actual_eps_value_quarterly')
            .ts_sum(252)
            .signed_power(0.9)
            .ts_backfill(3)
            .multiply('rank(ts_corr(returns, ts_mean(close, 120), 120))', 0.2)
            .build())
    # 验证与已知最佳alpha表达式一致
    known = ("((ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252)"
             ", 0.9), 3))) * (1 + ((rank(ts_corr(returns, ts_mean(close, 120), 120)"
             "))) * 0.2)")
    assert expr == known, f"\nBuilt:  {expr}\nKnown: {known}"


def test_tech_signals():
    """测试技术信号模板"""
    assert 'rank(ts_corr' in ExpressionTemplates.tech_beta(120)
    assert 'rank(-ts_std_dev' in ExpressionTemplates.tech_vol(252)
    assert 'rank(ts_delta' in ExpressionTemplates.tech_momentum(60)


def test_builder_add():
    """测试加法组合"""
    builder = ExpressionBuilder()
    expr = (builder.field('eps').ts_mean(20)
            .add('rank(close)', 0.5).build())
    assert '+ ((rank(close))) * 0.5' in expr


def test_reset():
    """测试重置"""
    builder = ExpressionBuilder()
    builder.field('close').ts_mean(20).rank().build()
    builder.reset()
    expr = builder.field('volume').ts_delta(5).build()
    assert 'close' not in expr
    assert 'volume' in expr


if __name__ == "__main__":
    test_eps_basic()
    test_eps_momentum()
    test_builder_single_field()
    test_builder_nested()
    test_builder_multiply()
    test_tech_signals()
    test_builder_add()
    test_reset()
    print("All 8 tests passed!")
