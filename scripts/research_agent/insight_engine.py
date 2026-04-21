"""洞察引擎 - 从挖掘结果提取规律"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AlphaMetrics:
    """Alpha指标"""
    alpha_id: str
    expression: str
    dataset: str
    template: str
    field_id: str
    sharpe: float
    fitness: float
    turnover: float
    margin: float
    ppc: float

    @property
    def margin_ratio(self) -> float:
        """Margin/Turnover比"""
        return self.margin / max(self.turnover, 0.001)

    def is_submittable(self) -> bool:
        return (
            self.sharpe >= 1.58 and
            self.fitness > 0.5 and
            self.ppc < 0.5 and
            self.margin > self.turnover and
            self.turnover > 0.01
        )


@dataclass
class Insight:
    """洞察"""
    description: str
    confidence: float
    source: str
    category: str  # 'dataset', 'template', 'field', 'combination'


class InsightEngine:
    """从挖掘结果提取洞察"""

    def __init__(self):
        self.patterns = defaultdict(list)

    def analyze_batch_results(self, results: List[AlphaMetrics]) -> List[Insight]:
        """分析一批结果，提取洞察"""
        if not results:
            return []

        insights = []

        # 1. 分析数据集特性
        insights.extend(self._analyze_dataset_patterns(results))

        # 2. 分析模板效果
        insights.extend(self._analyze_template_effects(results))

        # 3. 分析字段类型
        insights.extend(self._analyze_field_patterns(results))

        # 4. 分析Sharpe-Margin权衡
        insights.extend(self._analyze_sharpe_margin_tradeoff(results))

        logger.info(f"从 {len(results)} 个结果中提取了 {len(insights)} 个洞察")
        return insights

    def _analyze_dataset_patterns(self, results: List[AlphaMetrics]) -> List[Insight]:
        """分析数据集模式"""
        insights = []
        by_dataset = defaultdict(list)

        for r in results:
            by_dataset[r.dataset].append(r)

        for dataset, alphas in by_dataset.items():
            avg_sharpe = sum(a.sharpe for a in alphas) / len(alphas)
            avg_margin_ratio = sum(a.margin_ratio for a in alphas) / len(alphas)

            if avg_sharpe >= 1.5 and avg_margin_ratio < 0.1:
                insight = Insight(
                    description=f"{dataset}数据集Sharpe高({avg_sharpe:.2f})但Margin/Turnover低({avg_margin_ratio:.2f})",
                    confidence=0.9,
                    source=f"batch_{dataset}",
                    category='dataset'
                )
                insights.append(insight)
                logger.info(f"洞察: {dataset} -> Sharpe高但M/T低")

            elif avg_sharpe < 0.8 and avg_margin_ratio > 2:
                insight = Insight(
                    description=f"{dataset}数据集Margin/Turnover好({avg_margin_ratio:.2f})但Sharpe低({avg_sharpe:.2f})",
                    confidence=0.9,
                    source=f"batch_{dataset}",
                    category='dataset'
                )
                insights.append(insight)

        return insights

    def _analyze_template_effects(self, results: List[AlphaMetrics]) -> List[Insight]:
        """分析模板效果"""
        insights = []
        by_template = defaultdict(list)

        for r in results:
            by_template[r.template].append(r)

        template_stats = {}
        for template, alphas in by_template.items():
            avg_sharpe = sum(a.sharpe for a in alphas) / len(alphas)
            avg_margin_ratio = sum(a.margin_ratio for a in alphas) / len(alphas)
            template_stats[template] = {
                'sharpe': avg_sharpe,
                'margin_ratio': avg_margin_ratio,
                'count': len(alphas)
            }

        # 找出最优模板
        if template_stats:
            best_sharpe_template = max(template_stats.items(), key=lambda x: x[1]['sharpe'])
            best_margin_template = max(template_stats.items(), key=lambda x: x[1]['margin_ratio'])

            if best_sharpe_template[0] != best_margin_template[0]:
                insights.append(Insight(
                    description=f"模板{best_sharpe_template[0]} Sharpe最高({best_sharpe_template[1]['sharpe']:.2f})，"
                               f"模板{best_margin_template[0]} M/T最好({best_margin_template[1]['margin_ratio']:.2f})",
                    confidence=0.7,
                    source="template_analysis",
                    category='template'
                ))

        return insights

    def _analyze_field_patterns(self, results: List[AlphaMetrics]) -> List[Insight]:
        """分析字段模式"""
        insights = []

        # 按字段前缀分组
        by_prefix = defaultdict(list)
        for r in results:
            prefix = r.field_id.split('_')[0] if '_' in r.field_id else r.field_id[:4]
            by_prefix[prefix].append(r)

        for prefix, alphas in by_prefix.items():
            if len(alphas) >= 3:  # 至少3个样本
                sharpe_variance = sum((a.sharpe - sum(a.sharpe for a in alphas)/len(alphas))**2 for a in alphas) / len(alphas)
                if sharpe_variance > 0.1:
                    insights.append(Insight(
                        description=f"字段前缀{prefix}的Sharpe差异大(variance={sharpe_variance:.3f})，"
                                   f"不同字段表现差异显著",
                        confidence=0.6,
                        source=f"field_analysis_{prefix}",
                        category='field'
                    ))

        return insights

    def _analyze_sharpe_margin_tradeoff(self, results: List[AlphaMetrics]) -> List[Insight]:
        """分析Sharpe-Margin权衡"""
        insights = []

        # 计算相关性
        sharpes = [r.sharpe for r in results]
        margin_ratios = [r.margin_ratio for r in results]

        if len(results) >= 3:
            # 简单的相关性判断
            high_sharpe = [r for r in results if r.sharpe >= 1.0]
            low_sharpe = [r for r in results if r.sharpe < 0.8]

            if high_sharpe and low_sharpe:
                avg_high_mr = sum(r.margin_ratio for r in high_sharpe) / len(high_sharpe)
                avg_low_mr = sum(r.margin_ratio for r in low_sharpe) / len(low_sharpe)

                if avg_high_mr < avg_low_mr * 0.5:
                    insights.append(Insight(
                        description=f"Sharpe>=1.0的Alpha平均M/T={avg_high_mr:.2f}，"
                                   f"远低于Sharpe<0.8的{avg_low_mr:.2f}",
                        confidence=0.85,
                        source="tradeoff_analysis",
                        category='combination'
                    ))
                    insights.append(Insight(
                        description="Sharpe和Margin/Turnover存在强负相关，需要找到平衡点",
                        confidence=0.8,
                        source="tradeoff_analysis",
                        category='combination'
                    ))

        return insights

    def identify_best_candidates(self, results: List[AlphaMetrics],
                               min_sharpe: float = 0.8,
                               min_margin_ratio: float = 1.0) -> List[AlphaMetrics]:
        """识别最佳候选Alpha"""
        candidates = [
            r for r in results
            if r.sharpe >= min_sharpe and r.margin_ratio >= min_margin_ratio
        ]
        # 按综合评分排序
        candidates.sort(key=lambda x: x.sharpe * 0.6 + x.margin_ratio * 0.4, reverse=True)
        return candidates[:10]

    def generate_next_hypothesis(self, results: List[AlphaMetrics],
                               memory_insights: List[Insight]) -> Optional[str]:
        """基于结果和历史洞察生成下一个假设"""
        if not results:
            return "探索新数据集"

        best = max(results, key=lambda x: x.sharpe)
        worst_margin = min(results, key=lambda x: x.margin_ratio)

        # 检查历史洞察
        high_confidence_insights = [i for i in memory_insights if i.confidence >= 0.7]

        if any('mdl136' in i.description for i in high_confidence_insights):
            return "尝试mdl136和pv87字段组合"

        if best.margin_ratio < 1.0:
            return "寻找Margin/Turnover天然更好的数据集"

        if best.sharpe < 1.0:
            return "尝试更激进的预处理或组合多个Alpha"

        return "继续当前策略并微调参数"