#!/usr/bin/env python3
"""Alpha组合策略 — EPS + 技术信号乘法/加法"""

from worldquant_brain.strategies.base import MiningStrategy


class CombinationStrategy(MiningStrategy):
    name = "combination"
    description = "Alpha组合: 基础Alpha × 技术信号"

    def generate_candidates(self, context: dict):
        bases = context.get('base_alphas', [])
        techs = context.get('technicals', [])
        weights = [0.15, 0.2, 0.25, 0.3]
        combo_types = ['mul', 'add']

        for base_name, base_expr in bases:
            for tech_name, tech_expr in techs:
                for weight in weights:
                    for combo in combo_types:
                        if combo == 'mul':
                            expr = (f"(({base_expr})) * (1 + (({tech_expr})) * {weight})")
                        else:
                            expr = (f"(({base_expr})) + (({tech_expr})) * {weight}")
                        name = f"{base_name}_{tech_name}_{combo}{int(weight*100)}"
                        yield expr, {}, name
