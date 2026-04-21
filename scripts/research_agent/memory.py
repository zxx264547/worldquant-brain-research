"""研究记忆 - 持久化洞察和假设"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """洞察"""
    insight: str
    source: str  # 实验来源
    confidence: float  # 置信度 0-1
    hypothesis: str  # 衍生假设
    tested: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Hypothesis:
    """可行动的假设"""
    id: str
    description: str
    confidence: float
    strategy: str  # 推荐的策略
    tested: bool = False
    results: List[dict] = field(default_factory=list)

    def add_result(self, result: dict):
        self.results.append(result)
        # 根据结果更新置信度
        if result.get('passed'):
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.confidence = max(0.0, self.confidence - 0.1)

    def to_dict(self) -> dict:
        return asdict(self)


class ResearchMemory:
    """持久化研究记忆

    管理洞察、假设和历史实验结果
    """

    def __init__(self, memory_file: str = "research_memory.json"):
        self.memory_file = Path(memory_file)
        self.insights: List[Insight] = []
        self.hypotheses: List[Hypothesis] = []
        self.experiments: List[dict] = []
        self.strategy_effectiveness: Dict[str, float] = {}  # 策略有效性评分
        self.load()

    def load(self):
        """从文件加载记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.insights = [Insight(**i) for i in data.get('insights', [])]
                    self.hypotheses = [Hypothesis(**h) for h in data.get('hypotheses', [])]
                    self.experiments = data.get('experiments', [])
                    self.strategy_effectiveness = data.get('strategy_effectiveness', {})
                    logger.info(f"加载了 {len(self.insights)} 个洞察, {len(self.hypotheses)} 个假设")
            except Exception as e:
                logger.warning(f"加载记忆失败: {e}")

    def save(self):
        """保存记忆到文件"""
        data = {
            'insights': [i.to_dict() for i in self.insights],
            'hypotheses': [h.to_dict() for h in self.hypotheses],
            'experiments': self.experiments[-100:],  # 只保留最近100个
            'strategy_effectiveness': self.strategy_effectiveness,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"记忆已保存到 {self.memory_file}")

    def add_insight(self, insight: str, source: str, metrics: dict = None,
                    confidence: float = 0.5, hypothesis: str = ""):
        """添加新洞察"""
        # 检查是否已存在相似洞察
        for existing in self.insights:
            if existing.insight == insight and existing.source == source:
                logger.debug(f"洞察已存在: {insight[:50]}...")
                return existing

        new_insight = Insight(
            insight=insight,
            source=source,
            confidence=confidence,
            hypothesis=hypothesis or self._generate_hypothesis(insight)
        )
        self.insights.append(new_insight)
        logger.info(f"新增洞察: {insight[:60]}...")
        return new_insight

    def add_hypothesis(self, description: str, strategy: str, confidence: float = 0.5) -> Hypothesis:
        """添加新假设"""
        # 生成ID
        h_id = f"h_{len(self.hypotheses) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        hypothesis = Hypothesis(
            id=h_id,
            description=description,
            confidence=confidence,
            strategy=strategy
        )
        self.hypotheses.append(hypothesis)
        logger.info(f"新增假设 [{h_id}]: {description[:60]}...")
        return hypothesis

    def get_untested_hypotheses(self) -> List[Hypothesis]:
        """获取未验证的假设"""
        return [h for h in self.hypotheses if not h.tested]

    def get_high_confidence_hypotheses(self, threshold: float = 0.6) -> List[Hypothesis]:
        """获取高置信假设"""
        return [h for h in self.hypotheses if h.confidence >= threshold and not h.tested]

    def mark_hypothesis_tested(self, hypothesis_id: str, result: dict):
        """标记假设已测试并更新结果"""
        for h in self.hypotheses:
            if h.id == hypothesis_id:
                h.tested = True
                h.add_result(result)
                logger.info(f"假设 [{h.id}] 已测试, 结果: {result.get('passed', False)}")
                return

    def record_experiment(self, strategy: dict, results: List[dict], metrics: dict):
        """记录实验"""
        experiment = {
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy,
            'results_count': len(results),
            'metrics': metrics,
            'best_sharpe': max((r.get('sharpe', 0) for r in results), default=0),
            'best_margin_ratio': max((r.get('margin', 0) / max(r.get('turnover', 0.001), 0.001) for r in results), default=0)
        }
        self.experiments.append(experiment)

        # 更新策略有效性
        strategy_name = strategy.get('name', 'unknown')
        if strategy_name not in self.strategy_effectiveness:
            self.strategy_effectiveness[strategy_name] = 0.5

        # 根据结果调整评分
        if metrics.get('found_candidates'):
            self.strategy_effectiveness[strategy_name] = min(1.0, self.strategy_effectiveness[strategy_name] + 0.1)
        elif metrics.get('tested_count', 0) > 0:
            self.strategy_effectiveness[strategy_name] = max(0.0, self.strategy_effectiveness[strategy_name] - 0.05)

    def get_best_strategy(self) -> str:
        """获取最高效的策略"""
        if not self.strategy_effectiveness:
            return "explore_new_datasets"
        return max(self.strategy_effectiveness.items(), key=lambda x: x[1])[0]

    def get_actionable_strategies(self) -> List[str]:
        """获取可执行的策略建议"""
        strategies = []

        # 基于有效性评分
        best = self.get_best_strategy()
        if best != "explore_new_datasets":
            strategies.append(f"继续{best}策略（当前最佳）")

        # 基于高置信假设
        for h in self.get_high_confidence_hypotheses():
            strategies.append(f"验证假设: {h.description[:50]}")

        return strategies[:5]  # 最多返回5个

    def _generate_hypothesis(self, insight: str) -> str:
        """从洞察生成假设"""
        # 简单的启发式规则
        if "降低Turnover" in insight:
            return "尝试更激进的预处理组合"
        elif "Sharpe" in insight and "低" in insight:
            return "尝试不同数据集"
        elif "Margin" in insight:
            return "验证Margin改善是否能持续"
        return "基于洞察设计新实验"

    def summarize(self) -> str:
        """生成研究总结"""
        untested = len(self.get_untested_hypotheses())
        high_conf = len(self.get_high_confidence_hypotheses())
        experiments = len(self.experiments)

        lines = [
            "=" * 60,
            "研究记忆总结",
            "=" * 60,
            f"实验次数: {experiments}",
            f"洞察数量: {len(self.insights)}",
            f"假设数量: {len(self.hypotheses)}",
            f"  - 未测试: {untested}",
            f"  - 高置信: {high_conf}",
            "",
            "策略有效性:",
        ]

        for name, score in sorted(self.strategy_effectiveness.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {name}: {score:.2f}")

        return "\n".join(lines)