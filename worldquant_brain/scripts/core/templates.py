"""共享模板定义

统一定义 Alpha 模板，避免重复定义
"""

from typing import List, Tuple

# 基础模板（已验证有效）
BASE_TEMPLATES: List[Tuple[str, str]] = [
    ('winsorize({data})', 'winsorize'),
    ('ts_mean({data}, 20)', 'ts_mean_20'),
    ('ts_mean(winsorize({data}), 20)', 'mean_winsorize'),
    ('rank({data})', 'rank'),
    ('rank(ts_mean({data}, 20))', 'rank_ts_mean'),
    ('ts_zscore({data}, 20)', 'ts_zscore'),
]

# 高级模板（需要更多测试）
ADVANCED_TEMPLATES: List[Tuple[str, str]] = [
    ('ts_mean(winsorize(ts_backfill({data})), 10)', 'mean_winsorize_backfill'),
    ('ts_decay_linear({data}, 10)', 'decay_10'),
    ('ts_decay_linear({data}, 20)', 'decay_20'),
    ('signed_power({data}, 1.3)', 'signed_power'),
    ('ts_rank({data}, 20)', 'ts_rank'),
    ('ts_max({data}, 20)', 'ts_max'),
    ('ts_min({data}, 20)', 'ts_min'),
]

# 组合模板
COMPOSITE_TEMPLATES: List[Tuple[str, str]] = [
    ('rank(winsorize({data}))', 'rank_winsorize'),
    ('winsorize(rank({data}))', 'winsorize_rank'),
    ('rank(ts_zscore({data}, 20))', 'rank_zscore'),
    ('ts_mean(rank({data}), 10)', 'mean_rank'),
]

# 所有模板
ALL_TEMPLATES = BASE_TEMPLATES + ADVANCED_TEMPLATES + COMPOSITE_TEMPLATES

# 默认设置
DEFAULT_SETTINGS = {
    'instrumentType': 'EQUITY',
    'region': 'USA',
    'universe': 'TOP3000',
    'delay': 1,
    'decay': 0.0,
    'neutralization': 'NONE',
    'truncation': 0.0,
    'pasteurization': 'ON',
    'unitHandling': 'VERIFY',
    'nanHandling': 'OFF',
    'language': 'FASTEXPR',
    'visualization': False
}


def get_template_count(include_advanced: bool = False) -> int:
    """获取模板总数"""
    if include_advanced:
        return len(ALL_TEMPLATES)
    return len(BASE_TEMPLATES)


def generate_expression(field_id: str, template: Tuple[str, str]) -> Tuple[str, str]:
    """生成完整表达式"""
    expr = template[0].format(data=field_id)
    return (expr, template[1])