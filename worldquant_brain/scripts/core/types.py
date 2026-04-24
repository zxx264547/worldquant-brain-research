"""共享类型定义

统一定义 AlphaResult 等数据结构，避免重复定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class AlphaResult:
    """标准Alpha结果"""
    alpha_id: str
    expression: str
    sharpe: float
    fitness: float
    turnover: float
    ppc: float
    margin: float

    def to_dict(self) -> dict:
        return {
            'alpha_id': self.alpha_id,
            'expression': self.expression,
            'sharpe': self.sharpe,
            'fitness': self.fitness,
            'turnover': self.turnover,
            'ppc': self.ppc,
            'margin': self.margin,
        }


@dataclass
class AlphaResultExtended(AlphaResult):
    """扩展Alpha结果（用于挖掘引擎）"""
    field_id: str = ''
    template: str = ''
    dataset: str = ''
    pnl: List[float] = field(default_factory=list)

    def is_submittable(self) -> bool:
        """检查是否满足PPA提交条件"""
        return (
            self.sharpe >= 1.58 and
            self.fitness > 0.5 and
            self.ppc < 0.5 and
            self.margin > self.turnover and
            self.turnover > 0.01
        )

    def get_checks(self) -> Dict[str, bool]:
        """获取各项检查结果"""
        return {
            'sharpe >= 1.58': self.sharpe >= 1.58,
            'fitness > 0.5': self.fitness > 0.5,
            'ppc < 0.5': self.ppc < 0.5,
            'margin > turnover': self.margin > self.turnover,
            'turnover > 0.01': self.turnover > 0.01,
        }

    def to_dict(self) -> dict:
        result = super().to_dict()
        result.update({
            'field_id': self.field_id,
            'template': self.template,
            'dataset': self.dataset,
            'is_submittable': self.is_submittable(),
            'checks': self.get_checks(),
        })
        return result


@dataclass
class AlphaInfo:
    """Alpha信息（用于相关性分析）"""
    alpha_id: str
    pnl: List[float]
    sharpe: float
    fitness: float
    expression: str
    margin: float = 0
    turnover: float = 0

    def to_dict(self) -> dict:
        return {
            'alpha_id': self.alpha_id,
            'sharpe': self.sharpe,
            'fitness': self.fitness,
            'expression': self.expression,
            'margin': self.margin,
            'turnover': self.turnover,
            'pnl_len': len(self.pnl) if self.pnl else 0,
        }


@dataclass
class MiningConfig:
    """挖掘配置

    注意: templates 和 settings 在运行时从 templates.py 导入
    """
    datasets: List[str] = field(default_factory=lambda: ['pv87', 'mdl136'])
    max_fields_per_dataset: int = 10
    max_combinations: int = 300
    poll_timeout: int = 300
    poll_interval: int = 2