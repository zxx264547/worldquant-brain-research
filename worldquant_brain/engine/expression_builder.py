#!/usr/bin/env python3
"""声明式Alpha表达式构建器 — 替代if-else硬编码和字符串拼接"""

from typing import Optional


class ExpressionBuilder:
    """链式API构建Alpha表达式

    用法:
        builder = ExpressionBuilder()
        expr = (builder
            .field('actual_eps_value_quarterly')
            .ts_sum(252)
            .signed_power(0.9)
            .ts_backfill(3)
            .build())
        # → "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3)"
    """

    def __init__(self):
        self.reset()

    def reset(self) -> 'ExpressionBuilder':
        self._field = None       # 数据字段名
        self._ops = []           # (算子名, 参数) 栈
        self._combo_type = None  # mul/add/neg/rank
        self._combo_parts = []   # 组合的部分
        self._combo_weights = [] # 组合权重
        return self

    # ─── 字段 ───

    def field(self, name: str) -> 'ExpressionBuilder':
        self._field = name
        return self

    # ─── 一元算子 (无参数或单参数) ───

    def rank(self) -> 'ExpressionBuilder':
        self._ops.append(('rank',))
        return self

    def zscore(self) -> 'ExpressionBuilder':
        self._ops.append(('zscore',))
        return self

    def signed_power(self, exponent: float) -> 'ExpressionBuilder':
        self._ops.append(('signed_power', exponent))
        return self

    # ─── 二元算子 (窗口参数) ───

    def ts_mean(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_mean', window))
        return self

    def ts_sum(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_sum', window))
        return self

    def ts_delta(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_delta', window))
        return self

    def ts_delay(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_delay', window))
        return self

    def ts_std_dev(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_std_dev', window))
        return self

    def ts_corr(self, other: str, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_corr', (other, window)))
        return self

    def ts_backfill(self, days: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_backfill', days))
        return self

    def ts_decay_linear(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_decay_linear', window))
        return self

    def ts_arg_max(self, window: int) -> 'ExpressionBuilder':
        self._ops.append(('ts_arg_max', window))
        return self

    # ─── 组合操作 (在build()中展开) ───

    def add(self, other_expr: str, weight: float) -> 'ExpressionBuilder':
        self._combo_type = 'add'
        self._combo_parts = [other_expr]
        self._combo_weights = [weight]
        return self

    def subtract(self, other_expr: str, weight: float) -> 'ExpressionBuilder':
        self._combo_type = 'neg'
        self._combo_parts = [other_expr]
        self._combo_weights = [weight]
        return self

    def multiply(self, other_expr: str, weight: float) -> 'ExpressionBuilder':
        self._combo_type = 'mul'
        self._combo_parts = [other_expr]
        self._combo_weights = [weight]
        return self

    def multi_add(self, *parts: tuple) -> 'ExpressionBuilder':
        """多部分加法: (expr, weight) 元组"""
        self._combo_type = 'multi_add'
        self._combo_parts = [p[0] for p in parts]
        self._combo_weights = [p[1] for p in parts]
        return self

    def multi_mul(self, *parts: tuple) -> 'ExpressionBuilder':
        """多部分乘法: (expr, weight) 元组"""
        self._combo_type = 'multi_mul'
        self._combo_parts = [p[0] for p in parts]
        self._combo_weights = [p[1] for p in parts]
        return self

    # ─── 构建 ───

    def build(self) -> str:
        """构建最终表达式字符串"""
        if not self._field and not self._combo_parts:
            raise ValueError("必须设置 field() 或使用组合操作")

        if self._combo_type:
            return self._build_combo()
        return self._build_single(self._field)

    def _build_single(self, field: str) -> str:
        """构建单字段表达式: 从内到外展开算子栈"""
        expr = field
        for op_spec in self._ops:
            op_name = op_spec[0]
            if op_name == 'rank':
                expr = f"rank({expr})"
            elif op_name == 'zscore':
                expr = f"zscore({expr})"
            elif op_name == 'signed_power':
                expr = f"signed_power({expr}, {op_spec[1]})"
            elif op_name == 'ts_corr':
                other, window = op_spec[1]
                expr = f"ts_corr({expr}, {other}, {window})"
            elif op_name == 'group_neutralize':
                expr = f"group_neutralize({expr}, {op_spec[1]})"
            else:
                expr = f"{op_name}({expr}, {op_spec[1]})"
        return expr

    def _build_combo(self) -> str:
        """构建组合表达式"""
        base = self._build_single(self._field or "0")

        if self._combo_type == 'mul':
            part = self._combo_parts[0]
            w = self._combo_weights[0]
            return f"(({base})) * (1 + (({part})) * {w})"

        elif self._combo_type == 'add':
            part = self._combo_parts[0]
            w = self._combo_weights[0]
            return f"(({base})) + (({part})) * {w}"

        elif self._combo_type == 'neg':
            part = self._combo_parts[0]
            w = self._combo_weights[0]
            return f"(({base})) * 0.6 - (({part})) * {w}"

        elif self._combo_type == 'multi_add':
            parts = [f"(({base})) * {1 - sum(self._combo_weights)}"]
            for part, w in zip(self._combo_parts, self._combo_weights):
                parts.append(f"(({part})) * {w}")
            return " + ".join(parts)

        elif self._combo_type == 'multi_mul':
            parts = [f"(({base}))"]
            for part, w in zip(self._combo_parts, self._combo_weights):
                parts.append(f"(1 + (({part})) * {w})")
            return " * ".join(parts)

        return base


# ─── 预定义表达式模板 ───

class ExpressionTemplates:
    """常用表达式模板 — 替代硬编码字符串"""

    @staticmethod
    def eps_basic(window: int = 252, exponent: float = 0.9,
                  backfill: int = 3) -> str:
        return (ExpressionBuilder()
                .field('actual_eps_value_quarterly')
                .ts_sum(window)
                .signed_power(exponent)
                .ts_backfill(backfill)
                .build())

    @staticmethod
    def eps_with_momentum(window: int = 252,
                          momentum_window: int = 66) -> str:
        return (ExpressionBuilder()
                .field(f'actual_eps_value_quarterly + ts_mean(returns, {momentum_window})')
                .ts_sum(window)
                .signed_power(1.05)
                .ts_backfill(3)
                .build())

    @staticmethod
    def eps_with_dividend(window: int = 252) -> str:
        return (ExpressionBuilder()
                .field('actual_eps_value_quarterly + actual_dividend_value_quarterly')
                .ts_sum(window)
                .signed_power(1.05)
                .ts_backfill(3)
                .build())

    @staticmethod
    def eps_mul_tech(tech_expr: str, eps_expr: str = None,
                     weight: float = 0.2) -> str:
        if eps_expr is None:
            eps_expr = ExpressionTemplates.eps_basic()
        return f"(({eps_expr})) * (1 + (({tech_expr})) * {weight})"

    @staticmethod
    def tech_beta(window: int = 120) -> str:
        return f"rank(ts_corr(returns, ts_mean(close, {window}), {window}))"

    @staticmethod
    def tech_vol(window: int = 120) -> str:
        return f"rank(-ts_std_dev(returns, {window}))"

    @staticmethod
    def tech_momentum(window: int = 60) -> str:
        return f"rank(ts_delta(close, {window}))"

    @staticmethod
    def tech_rsi(window: int = 14) -> str:
        return f"rank(ts_mean(close / ts_mean(close, {window}) - 1, 20))"

    @staticmethod
    def tech_volume_trend() -> str:
        return "rank(ts_mean(volume, 20) / ts_mean(volume, 120))"


# ─── 测试: 验证与现有表达式一致 ───

if __name__ == "__main__":
    # 构建已知最佳alpha
    builder = ExpressionBuilder()
    expr = (builder
            .field('actual_eps_value_quarterly')
            .ts_sum(252)
            .signed_power(0.9)
            .ts_backfill(3)
            .multiply('rank(ts_corr(returns, ts_mean(close, 120), 120))', 0.2)
            .build())

    expected = ("((ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 0.9), 3)))"
                " * (1 + ((rank(ts_corr(returns, ts_mean(close, 120), 120)))) * 0.2)")
    print(f"构建结果: {expr}")
    print(f"预期结果: {expected}")
    print(f"匹配: {expr == expected}")

    # 测试模板
    print(f"\nEPS基础: {ExpressionTemplates.eps_basic()}")
    print(f"EPS+动量: {ExpressionTemplates.eps_with_momentum()}")
    print(f"Beta120: {ExpressionTemplates.tech_beta()}")
