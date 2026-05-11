#!/usr/bin/env python3
"""参数优化策略 — 在最佳Alpha上测试不同decay/truncation/neutralization"""

from worldquant_brain.strategies.base import MiningStrategy


class SettingsOptimizeStrategy(MiningStrategy):
    name = "settings_optimize"
    description = "参数网格搜索: decay × truncation × neutralization"

    def generate_candidates(self, context: dict):
        alphas = context.get('optimize_alphas', [])
        decays = [0, 2, 3, 5]
        truncs = [0.05, 0.08, 0.10, 0.12, 0.15]
        neuts = ['NONE', 'INDUSTRY', 'SECTOR']

        for name, expr in alphas:
            for decay in decays:
                for trunc in truncs:
                    for neut in neuts:
                        settings = {
                            'decay': decay,
                            'truncation': trunc,
                            'neutralization': neut
                        }
                        opt_name = f"{name}_d{decay}_t{int(trunc*100)}_n{neut[:3]}"
                        yield expr, settings, opt_name
