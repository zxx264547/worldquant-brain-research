#!/usr/bin/env python3
"""算子探索策略 — 在已有Alpha基础上叠加不同算子"""

from worldquant_brain.strategies.base import MiningStrategy
from worldquant_brain.engine import ExpressionBuilder

VALID_WINDOWS = [5, 22, 66, 120, 252]
OPS = ['ts_mean', 'ts_delta', 'ts_backfill', 'ts_decay_linear']
WRAPPERS = ['rank', 'zscore']


class OperatorExploreStrategy(MiningStrategy):
    name = "operator_explore"
    description = "在已验证字段上探索算子组合"

    def generate_candidates(self, context: dict):
        fields = context.get('validated_fields', [])
        if not fields:
            fields = context.get('fields', [])[:5]

        for field_name in fields:
            for op1_name in OPS:
                for w1 in VALID_WINDOWS:
                    for op2_name in OPS:
                        if op1_name == op2_name:
                            continue
                        for w2 in VALID_WINDOWS:
                            for wrapper in WRAPPERS:
                                try:
                                    builder = ExpressionBuilder()
                                    expr = (builder
                                            .field(field_name)
                                            .__getattribute__(op1_name)(w1)
                                            .__getattribute__(op2_name)(w2)
                                            .__getattribute__(wrapper)()
                                            .build())
                                    name = f"{field_name}_{op1_name}{w1}_{op2_name}{w2}_{wrapper}"
                                    yield expr, {}, name
                                except Exception:
                                    continue
