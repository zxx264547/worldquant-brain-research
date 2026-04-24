"""实验跟踪器 - 记录实验进度和结果"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """实验结果"""
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
    is_submittable: bool = False
    margin_ratio: float = 0.0

    def __post_init__(self):
        if self.turnover > 0:
            self.margin_ratio = self.margin / self.turnover

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Experiment:
    """实验"""
    iteration: int
    strategy_name: str
    timestamp: str
    tested_count: int
    candidates_count: int
    results: List[ExperimentResult]
    best_alpha: Optional[ExperimentResult] = None

    def to_dict(self) -> dict:
        return {
            'iteration': self.iteration,
            'strategy_name': self.strategy_name,
            'timestamp': self.timestamp,
            'tested_count': self.tested_count,
            'candidates_count': self.candidates_count,
            'best_alpha': self.best_alpha.to_dict() if self.best_alpha else None,
            'results': [r.to_dict() for r in self.results]
        }


class ExperimentTracker:
    """跟踪实验进度和结果"""

    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.experiments: List[Experiment] = []
        self.current_iteration = 0

    def record(self, strategy_name: str, results: List[ExperimentResult]) -> Experiment:
        """记录一轮实验"""
        self.current_iteration += 1

        # 找最优Alpha
        best_alpha = None
        if results:
            # 按综合评分排序
            sorted_results = sorted(results, key=lambda x: x.sharpe * 0.5 + x.margin_ratio * 0.5, reverse=True)
            best_alpha = sorted_results[0]

        candidates = [r for r in results if r.is_submittable]

        experiment = Experiment(
            iteration=self.current_iteration,
            strategy_name=strategy_name,
            timestamp=datetime.now().isoformat(),
            tested_count=len(results),
            candidates_count=len(candidates),
            results=results,
            best_alpha=best_alpha
        )

        self.experiments.append(experiment)

        logger.info(f"实验 #{self.current_iteration}: {strategy_name}, "
                   f"测试{len(results)}个, 候选{len(candidates)}个")

        return experiment

    def get_all_candidates(self) -> List[ExperimentResult]:
        """获取所有候选Alpha"""
        candidates = []
        for exp in self.experiments:
            candidates.extend([r for r in exp.results if r.is_submittable])
        return candidates

    def get_best_overall(self, top_k: int = 10) -> List[ExperimentResult]:
        """获取最佳的Alpha"""
        all_results = []
        for exp in self.experiments:
            all_results.extend(exp.results)

        # 按综合评分排序
        sorted_results = sorted(
            all_results,
            key=lambda x: x.sharpe * 0.5 + x.margin_ratio * 0.5,
            reverse=True
        )
        return sorted_results[:top_k]

    def save(self, filepath: str = None):
        """保存实验记录"""
        if filepath is None:
            filepath = self.output_dir / "experiment_tracker.json"

        data = {
            'experiments': [e.to_dict() for e in self.experiments],
            'summary': self.summarize()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"实验记录已保存到 {filepath}")

    def summarize(self) -> dict:
        """生成实验摘要"""
        total_tested = sum(e.tested_count for e in self.experiments)
        total_candidates = sum(e.candidates_count for e in self.experiments)
        best_alphas = self.get_best_overall(5)

        return {
            'total_experiments': len(self.experiments),
            'total_tested': total_tested,
            'total_candidates': total_candidates,
            'best_sharpe': max((a.sharpe for a in best_alphas), default=0) if best_alphas else 0,
            'best_margin_ratio': max((a.margin_ratio for a in best_alphas), default=0) if best_alphas else 0,
            'strategies_tried': list(set(e.strategy_name for e in self.experiments))
        }

    def print_progress_report(self):
        """打印进度报告"""
        summary = self.summarize()
        best = self.get_best_overall(3)

        print("\n" + "=" * 60)
        print("研究进度报告")
        print("=" * 60)
        print(f"实验轮次: {summary['total_experiments']}")
        print(f"测试Alpha总数: {summary['total_tested']}")
        print(f"候选Alpha总数: {summary['total_candidates']}")
        print(f"策略尝试: {len(summary['strategies_tried'])}")

        if best:
            print("\n当前最佳Alpha:")
            for i, alpha in enumerate(best, 1):
                status = "✅ 可提交" if alpha.is_submittable else "❌ 未达标"
                print(f"  {i}. Sharpe={alpha.sharpe:.2f}, M/T={alpha.margin_ratio:.2f}, "
                     f"Dataset={alpha.dataset}, Template={alpha.template} {status}")

        if summary['total_candidates'] == 0:
            print("\n⚠️  尚未找到可提交的Alpha，继续研究...")
            print("\n最佳Alpha详情:")
            for i, alpha in enumerate(best[:3], 1) if best else []:
                checks = []
                if alpha.sharpe >= 1.58: checks.append("Sharpe✅")
                else: checks.append(f"Sharpe❌({alpha.sharpe:.2f})")
                if alpha.margin_ratio > 1: checks.append("M/T✅")
                else: checks.append(f"M/T❌({alpha.margin_ratio:.2f})")
                if alpha.fitness > 0.5: checks.append("Fitness✅")
                if alpha.ppc < 0.5: checks.append("PPC✅")
                print(f"  {''.join(checks)}")

        print("\n" + "=" * 60)