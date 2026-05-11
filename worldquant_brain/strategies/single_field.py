#!/usr/bin/env python3
"""单字段挖掘策略 — 字段 + 算子探测"""

from worldquant_brain.strategies.base import MiningStrategy
from worldquant_brain.engine import ExpressionBuilder

VALID_WINDOWS = [5, 22, 66, 120, 252, 504]
OPERATORS = ['ts_mean', 'ts_delta', 'ts_sum', 'ts_std_dev']


class SingleFieldStrategy(MiningStrategy):
    name = "single_field"
    description = "单字段 × 算子 × 窗口全排列"

    def generate_candidates(self, context: dict):
        fields = context.get('fields', [])
        ops = context.get('operators', OPERATORS)
        windows = context.get('windows', VALID_WINDOWS)

        for field_name in fields:
            for op_name in ops:
                for window in windows:
                    builder = ExpressionBuilder()
                    expr = (builder
                            .field(field_name)
                            .__getattribute__(op_name)(window)
                            .rank()
                            .build())
                    name = f"{field_name}_{op_name}_{window}"
                    yield expr, {}, name
