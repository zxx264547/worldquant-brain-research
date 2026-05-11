#!/usr/bin/env python3
"""字段交叉策略 — 两个字段的组合"""

from worldquant_brain.strategies.base import MiningStrategy
from worldquant_brain.engine import ExpressionBuilder

COMBOS = [(' + ', 'add'), (' * ', 'mul')]
WINDOWS = [66, 120, 252]


class FieldCrossStrategy(MiningStrategy):
    name = "field_cross"
    description = "两字段交叉组合"

    def generate_candidates(self, context: dict):
        fields = context.get('fields', [])[:8]

        for i, f1 in enumerate(fields):
            for f2 in fields[i+1:]:
                for combo_op, combo_name in COMBOS:
                    for wrapper in ['rank', 'zscore']:
                        for window in WINDOWS:
                            combined = f"{f1}{combo_op}{f2}"
                            builder = ExpressionBuilder()
                            expr = (builder
                                    .field(combined)
                                    .ts_mean(window)
                                    .__getattribute__(wrapper)()
                                    .build())
                            name = f"cross_{f1}_{f2}_{combo_name}_w{window}"
                            yield expr, {}, name
