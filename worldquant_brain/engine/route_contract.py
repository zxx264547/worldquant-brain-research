#!/usr/bin/env python3
"""Route Contract — 把研究任务写成可审计的实验协议

基于 JW52291 的 Alpha Harness 模板:
    "人负责设定方向和约束，agent/工具负责执行和验证"
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum


class Gate(Enum):
    IS_CHECK = "is_check"           # IS指标检查
    SELF_CORR = "self_corr"         # 自相关性检查
    PROD_CORR = "prod_corr"         # 产品相关性检查
    PRE_SUBMIT = "pre_submit"       # 提交前检查


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RouteContract:
    """研究合约 — 替代模糊prompt的明确实验协议"""

    # ─── 市场约束 ───
    region: str = "USA"
    universe: str = "TOP3000"
    delay: int = 1
    instrument_type: str = "EQUITY"

    # ─── 数据集/字段范围 ───
    dataset_id: Optional[str] = None
    field_constraints: List[str] = field(default_factory=list)
    # 允许的字段列表, 为空则不限制

    # ─── 硬门槛 ───
    min_sharpe: float = 1.0
    min_fitness: float = 0.5
    max_ppc: float = 0.5
    max_turnover: float = 0.10
    min_margin: float = 0.005

    # ─── 相关性门槛 ───
    max_self_corr: float = 0.7
    max_prod_corr: float = 0.70  # >0.70 判RED
    max_prod_corr_neargate: float = 0.73  # 0.70-0.73 near-gate rescue

    # ─── 执行约束 ───
    max_concurrent: int = 3            # 每轮最大并发
    max_per_shell: int = 5             # 同壳最多几个变体
    max_retries: int = 3               # 失败重试次数

    # ─── Neutralization策略 ───
    neutralization: str = "NONE"       # NONE/MARKET/SECTOR/INDUSTRY
    allowed_neutralizations: List[str] = field(default_factory=lambda: ["NONE"])

    # ─── 风险管理 ───
    # 哪些warning可以接受
    acceptable_warnings: List[str] = field(default_factory=list)
    # 哪些必须修复
    required_gates: List[Gate] = field(default_factory=lambda: [
        Gate.IS_CHECK, Gate.SELF_CORR, Gate.PROD_CORR
    ])

    # ─── 结构问题 ───
    structural_questions: List[str] = field(default_factory=list)
    # 每轮要回答的结构性问题, 例如:
    # "star_eq_rank 是否有原始信号？"
    # "MARKET neutralization 是否压掉了信号？"

    # ─── 合约元数据 ───
    contract_id: str = ""
    description: str = ""
    owner: str = "AI"
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d['required_gates'] = [g.value for g in self.required_gates]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'RouteContract':
        gates_data = data.pop('required_gates', [])
        contract = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        contract.required_gates = [Gate(g) for g in gates_data]
        return contract

    # ─── 预定义模板 ───
    @classmethod
    def template_eps_usa(cls) -> 'RouteContract':
        """EPS + 技术信号 组合探索 (USA)"""
        return cls(
            region="USA", universe="TOP3000", delay=1,
            min_sharpe=1.0, min_fitness=0.5, max_ppc=0.5,
            max_self_corr=0.7, max_prod_corr=0.70,
            neutralization="NONE",
            max_concurrent=3, max_per_shell=5,
            description="EPS基础信号 + 技术信号乘法组合",
            structural_questions=[
                "EPS signed_power指数0.9 vs 1.05 哪个更好？",
                "Beta120 vs RSI14 谁是更优的技术信号？",
                "多信号叠加比单信号提升多少？",
                "NONE neutralization是否最优？",
            ]
        )

    @classmethod
    def template_breakthrough(cls) -> 'RouteContract':
        """突破EPS天花板"""
        return cls(
            region="USA", universe="TOP3000", delay=1,
            min_sharpe=1.2, min_fitness=1.0, max_ppc=0.5,
            max_self_corr=0.7, max_prod_corr=0.70,
            neutralization="NONE",
            allowed_neutralizations=["NONE", "MARKET", "SECTOR"],
            max_concurrent=2, max_per_shell=3,
            description="突破EPS天花板: 非EPS基础 + 多信号 + 结构变化",
            structural_questions=[
                "cashflow/dividend/sales 哪个有原始信号？",
                "NEUTRALIZATION=NONE vs MARKET vs SECTOR 谁压掉了信号？",
                "trade_when稀疏化能否改善turnover同时保持Sharpe？",
                "哪些非EPS字段组合能达到Sharpe≥1.2？",
            ]
        )

    @classmethod
    def template_china(cls) -> 'RouteContract':
        """中国市场探索"""
        return cls(
            region="CHN", universe="TOP3000", delay=1,
            min_sharpe=1.0, min_fitness=0.5, max_ppc=0.5,
            max_self_corr=0.7, max_prod_corr=0.70,
            neutralization="NONE",
            description="中国市场Alpha探索",
            structural_questions=[
                "中国市场EPS信号强度是否弱于USA？",
                "中国市场价格动量比USA更有效吗？",
            ]
        )


# ─── Contract评估器 ───

class ContractEvaluator:
    """根据Contract评估Alpha是否通过各道Gate"""

    def __init__(self, contract: RouteContract):
        self.contract = contract

    def evaluate(self, alpha: dict) -> dict:
        """评估Alpha, 返回各Gate的状态"""
        gates = {}

        # IS Gate
        sharpe = alpha.get('sharpe', 0)
        fitness = alpha.get('fitness', 0)
        margin = alpha.get('margin', 0)
        turnover = alpha.get('turnover', 0)
        ppc = alpha.get('ppc', 1)

        is_pass = (sharpe >= self.contract.min_sharpe and
                   fitness >= self.contract.min_fitness and
                   ppc <= self.contract.max_ppc and
                   turnover <= self.contract.max_turnover and
                   margin >= self.contract.min_margin)

        gates['is_check'] = {
            'passed': is_pass,
            'details': {
                'sharpe': {'value': sharpe, 'threshold': self.contract.min_sharpe, 'ok': sharpe >= self.contract.min_sharpe},
                'fitness': {'value': fitness, 'threshold': self.contract.min_fitness, 'ok': fitness >= self.contract.min_fitness},
                'ppc': {'value': ppc, 'threshold': self.contract.max_ppc, 'ok': ppc <= self.contract.max_ppc},
                'turnover': {'value': turnover, 'threshold': self.contract.max_turnover, 'ok': turnover <= self.contract.max_turnover},
                'margin': {'value': margin, 'threshold': self.contract.min_margin, 'ok': margin >= self.contract.min_margin},
            }
        }

        # Self-Corr Gate (如果有数据)
        self_corr = alpha.get('self_correlation', alpha.get('self_corr'))
        if self_corr is not None:
            gates['self_corr'] = {
                'passed': self_corr <= self.contract.max_self_corr,
                'details': {'value': self_corr, 'threshold': self.contract.max_self_corr}
            }

        # Prod-Corr Gate (如果有数据)
        prod_corr = alpha.get('prod_correlation', alpha.get('prod_corr'))
        if prod_corr is not None:
            prod_pass = prod_corr <= self.contract.max_prod_corr
            is_near_gate = (not prod_pass and
                          prod_corr <= self.contract.max_prod_corr_neargate)
            gates['prod_corr'] = {
                'passed': prod_pass,
                'near_gate': is_near_gate,
                'details': {'value': prod_corr, 'threshold': self.contract.max_prod_corr}
            }

        # Pre-Submit Gate
        all_gates_pass = all(g.get('passed', False) for g in gates.values())
        gates['pre_submit'] = {
            'passed': all_gates_pass and is_pass,
            'ready': all_gates_pass and is_pass and sharpe >= 1.58
        }

        return gates

    def classify_failure(self, alpha: dict) -> str:
        """三分法分类失败"""
        evaluation = self.evaluate(alpha)

        # 基础设施问题
        if alpha.get('status') == 'error':
            return 'infrastructure'

        is_check = evaluation.get('is_check', {})
        if not is_check.get('passed', False):
            # 质量失败
            details = is_check.get('details', {})
            if details.get('sharpe', {}).get('value', 0) < self.contract.min_sharpe:
                return 'quality_low_sharpe'
            if details.get('fitness', {}).get('value', 0) < self.contract.min_fitness:
                return 'quality_low_fitness'
            if details.get('turnover', {}).get('value', 0) > self.contract.max_turnover:
                return 'quality_high_turnover'
            return 'quality_failure'

        # 相关性失败
        self_corr = evaluation.get('self_corr', {})
        prod_corr = evaluation.get('prod_corr', {})

        if not self_corr.get('passed', True):
            return 'correlation_self_high'
        if not prod_corr.get('passed', True):
            if prod_corr.get('near_gate', False):
                return 'correlation_prod_neargate'
            return 'correlation_prod_high'

        # 门槛边缘
        sharpe = alpha.get('sharpe', 0)
        if 1.4 <= sharpe < 1.58:
            return 'threshold_near_submit'
        if 1.0 <= sharpe < 1.4:
            return 'threshold_promising'

        return 'unknown'
