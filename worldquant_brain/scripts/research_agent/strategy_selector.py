"""策略选择器 - 决定下一步尝试什么"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """策略"""
    name: str
    description: str
    datasets: List[str]
    templates: List[tuple]  # [(expression_template, template_name), ...]
    priority: int = 1  # 1=最高
    hypothesis_id: str = None  # 关联的假设ID

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'datasets': self.datasets,
            'templates': [(t[0], t[1]) for t in self.templates],
            'priority': self.priority,
            'hypothesis_id': self.hypothesis_id
        }


# 预定义策略
PREDEFINED_STRATEGIES = [
    Strategy(
        name="短窗口ts_mean_pv87",
        description="pv87字段 + 短回溯期ts_mean(5)",
        datasets=['pv87'],
        templates=[
            ('ts_mean({data}, 5)', 'ts_mean_5'),
            ('winsorize(ts_mean({data}, 5))', 'winsorize_tsmean5'),
            ('ts_mean(winsorize({data}), 5)', 'tsmean_winsorize5'),
        ],
        priority=1
    ),
    Strategy(
        name="标准模板_analyst10",
        description="analyst10数据集 + 分组相对化模板",
        datasets=['analyst10'],
        templates=[
            ('industry_relative({data})', 'industry_rel'),
            ('industry_relative(ts_mean({data}, 20))', 'ind_rel_tsmean20'),
            ('rank(industry_relative({data}))', 'rank_ind_rel'),
            ('ts_mean(industry_relative({data}), 20)', 'ind_rel_tsmean20'),
        ],
        priority=2
    ),
    Strategy(
        name="短窗口ts_mean_mdl136",
        description="mdl136字段 + 短回溯期ts_mean",
        datasets=['mdl136'],
        templates=[
            ('ts_mean({data}, 5)', 'ts_mean_5'),
            ('ts_mean(winsorize({data}), 5)', 'mean_winsorize5'),
            ('winsorize(ts_mean({data}, 10))', 'winsorize_tsmean10'),
        ],
        priority=2
    ),
    Strategy(
        name="pv1标准模板",
        description="pv1价格数据 + 标准模板",
        datasets=['pv1'],
        templates=[
            ('winsorize({data})', 'winsorize'),
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            ('rank({data})', 'rank'),
        ],
        priority=3
    ),
    Strategy(
        name="pv13价格数据",
        description="pv13价格/成交量数据 + 标准模板",
        datasets=['pv13'],
        templates=[
            ('winsorize({data})', 'winsorize'),
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            ('ts_mean(winsorize({data}), 20)', 'mean_winsorize'),
        ],
        priority=3
    ),
    Strategy(
        name="fundamental6基本面",
        description="fundamental6基本面数据 + 标准模板",
        datasets=['fundamental6'],
        templates=[
            ('winsorize({data})', 'winsorize'),
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            ('rank({data})', 'rank'),
        ],
        priority=3
    ),
    Strategy(
        name="wds全球数据",
        description="wds全球市场数据 + 标准模板",
        datasets=['wds'],
        templates=[
            ('winsorize({data})', 'winsorize'),
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            ('rank(ts_mean({data}, 20))', 'rank_ts_mean'),
        ],
        priority=3
    ),
    Strategy(
        name="激进预处理",
        description="多步预处理组合",
        datasets=['pv87', 'mdl136'],
        templates=[
            ('ts_mean(winsorize(ts_backfill({data})), 10)', 'complex_1'),
            ('ts_decay_linear(winsorize({data}), 10)', 'decay_winsorize'),
            ('signed_power(winsorize({data}), 1.5)', 'signed_power'),
        ],
        priority=3
    ),
]


class StrategySelector:
    """基于历史和洞察选择最佳策略"""

    def __init__(self, memory):
        self.memory = memory
        self.used_strategies = set()
        self.current_strategy_index = 0

    def select_next_strategy(self) -> Strategy:
        """选择下一个要执行的策略"""
        # 1. 检查未验证的高置信假设
        hypotheses = self.memory.get_high_confidence_hypotheses()
        if hypotheses:
            # 基于假设选择策略
            hypothesis = hypotheses[0]
            strategy = self._strategy_from_hypothesis(hypothesis)
            if strategy:
                logger.info(f"基于假设选择策略: {strategy.name}")
                return strategy

        # 2. 从未使用的策略中选择最优先的
        untested = [s for s in PREDEFINED_STRATEGIES if s.name not in self.used_strategies]
        if untested:
            # 按优先级排序，选择优先级最高的
            untested.sort(key=lambda x: x.priority)
            strategy = untested[0]
            self.used_strategies.add(strategy.name)
            idx = PREDEFINED_STRATEGIES.index(strategy)
            logger.info(f"选择策略 [{idx+1}/{len(PREDEFINED_STRATEGIES)}]: {strategy.name} (优先级:{strategy.priority})")
            return strategy

        # 3. 所有策略都测试过了，按有效性重新排序并选择最有效的未充分测试的
        effectiveness = self.memory.strategy_effectiveness
        # 选择有效性最低的策略（给更多机会）
        strategies_with_scores = [
            (s, effectiveness.get(s.name, 0.5)) for s in PREDEFINED_STRATEGIES
        ]
        # 排除有效性太高的（已充分测试且效果好）
        candidates = [(s, score) for s, score in strategies_with_scores if score < 0.8]
        if not candidates:
            candidates = strategies_with_scores  # 如果都充分测试了，就随便选

        candidates.sort(key=lambda x: x[1])  # 按有效性排序，越低越优先
        strategy = candidates[0][0]
        idx = PREDEFINED_STRATEGIES.index(strategy)
        logger.info(f"重新选择策略 [{idx+1}/{len(PREDEFINED_STRATEGIES)}]: {strategy.name} (有效性:{candidates[0][1]:.2f})")
        return strategy

    def _strategy_from_hypothesis(self, hypothesis) -> Optional[Strategy]:
        """从假设生成策略"""
        desc = hypothesis.description.lower()

        if "analyst10" in desc or "分析师" in desc:
            return Strategy(name=f"假设验证_{hypothesis.id}", description=hypothesis.description,
                         datasets=['analyst10'], templates=[], priority=1, hypothesis_id=hypothesis.id)
        elif "组合" in desc or "combine" in desc:
            return Strategy(name=f"假设验证_{hypothesis.id}", description=hypothesis.description,
                         datasets=['pv87', 'mdl136'], templates=[], priority=1, hypothesis_id=hypothesis.id)

        return None

    def mark_strategy_tested(self, strategy: Strategy, results: dict):
        """标记策略已测试并更新记忆"""
        self.memory.record_experiment(
            strategy=strategy.to_dict(),
            results=results.get('alphas', []),
            metrics={
                'tested_count': results.get('tested', 0),
                'found_candidates': results.get('candidates', 0)
            }
        )

        # 如果策略关联了假设，更新假设状态
        if strategy.hypothesis_id:
            self.memory.mark_hypothesis_tested(
                strategy.hypothesis_id,
                {'passed': results.get('candidates', 0) > 0}
            )

    def get_available_datasets(self) -> List[str]:
        """获取可用的数据集列表"""
        return ['pv87', 'mdl136', 'analyst10', 'pv1', 'pv13', 'fundamental6', 'wds']

    def suggest_next_steps(self) -> List[str]:
        """建议下一步"""
        suggestions = self.memory.get_actionable_strategies()

        # 添加默认建议
        if len(suggestions) < 3:
            suggestions.append("探索新的数据集组合")
            suggestions.append("尝试不同的预处理序列")

        return suggestions[:5]