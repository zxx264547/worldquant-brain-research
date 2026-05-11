"""WorldQuant BRAIN 挖掘策略插件"""
from worldquant_brain.strategies.base import MiningStrategy
from worldquant_brain.strategies.single_field import SingleFieldStrategy
from worldquant_brain.strategies.combination import CombinationStrategy
from worldquant_brain.strategies.operator_explore import OperatorExploreStrategy
from worldquant_brain.strategies.settings_optimize import SettingsOptimizeStrategy
from worldquant_brain.strategies.field_cross import FieldCrossStrategy
from worldquant_brain.strategies.knowledge_guided import KnowledgeGuidedStrategy

ALL_STRATEGIES = {
    'single_field': SingleFieldStrategy,
    'combination': CombinationStrategy,
    'operator_explore': OperatorExploreStrategy,
    'settings_optimize': SettingsOptimizeStrategy,
    'field_cross': FieldCrossStrategy,
    'knowledge_guided': KnowledgeGuidedStrategy,
}

def get_strategy(name: str) -> MiningStrategy:
    return ALL_STRATEGIES[name]()
