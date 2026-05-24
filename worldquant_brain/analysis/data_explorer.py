"""数据探索器 — 通用数据分析能力

提供数据集探索、字段分析、模式发现等能力，
分析结果通过 ReportGenerator 自动沉淀为知识。
"""
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter

from worldquant_brain.db.json_store import alphas_store, experiments_store


class DataExplorer:
    """通用数据分析工具（基于本地历史数据）"""

    def __init__(self, project_root: str | Path = None):
        pass

    def analyze_experiment_trends(self, last_n: int = 50) -> dict:
        """分析最近N次实验的趋势

        Returns:
            策略表现趋势、Sharpe分布、成功率变化
        """
        exp_data = experiments_store.load()
        experiments = [e for e in exp_data["items"] if e.get("status") == "done"]
        experiments.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        experiments = experiments[:last_n]

        alpha_data = alphas_store.load()
        alphas = [e for e in alpha_data["entries"].values() if e.get("status") == "done"]
        alphas.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        alphas = alphas[:last_n * 8]

        if not experiments:
            return {"status": "no_experiments"}

        strategy_stats = {}
        for exp in experiments:
            s = exp.get('strategy', 'unknown')
            if s not in strategy_stats:
                strategy_stats[s] = {"runs": 0, "sharpes": [], "total_tasks": 0}
            strategy_stats[s]["runs"] += 1
            strategy_stats[s]["sharpes"].append(exp.get('best_sharpe', 0) or 0)
            strategy_stats[s]["total_tasks"] += exp.get('total_tasks', 0) or 0

        for s, stats in strategy_stats.items():
            sharpes = stats["sharpes"]
            stats["avg_sharpe"] = round(sum(sharpes) / len(sharpes), 3) if sharpes else 0
            stats["max_sharpe"] = round(max(sharpes), 3) if sharpes else 0
            stats["trend"] = self._compute_trend(sharpes)
            del stats["sharpes"]

        all_sharpes = [a.get('sharpe', 0) for a in alphas if a.get('sharpe') is not None]
        sharpe_dist = self._distribution_stats(all_sharpes)

        ppa_pass = sum(1 for a in alphas
                       if (a.get('sharpe', 0) or 0) >= 1.58 and
                       (a.get('fitness', 0) or 0) > 0.5 and
                       (a.get('ppc', 1) or 1) < 0.5 and
                       (a.get('margin', 0) or 0) > (a.get('turnover', 1) or 1))

        return {
            "status": "ok",
            "experiment_count": len(experiments),
            "alpha_count": len(alphas),
            "strategy_stats": strategy_stats,
            "sharpe_distribution": sharpe_dist,
            "ppa_pass_rate": round(ppa_pass / max(len(alphas), 1), 4),
            "analysis_time": datetime.now().isoformat()
        }

    def find_promising_patterns(self) -> list[dict]:
        """基于历史结果发现高潜力的模式"""
        alpha_data = alphas_store.load()
        all_alphas = [e for e in alpha_data["entries"].values() if e.get("status") == "done"]

        combos = {}
        for a in all_alphas:
            ct = a.get('combo_type', '')
            if ct:
                if ct not in combos:
                    combos[ct] = {"sharpes": []}
                combos[ct]["sharpes"].append(a.get('sharpe', 0))

        top_alphas = [a for a in all_alphas if (a.get('sharpe', 0) or 0) >= 0.8]
        top_alphas.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
        top_alphas = top_alphas[:50]

        patterns = []

        for ct, stats in combos.items():
            if len(stats["sharpes"]) >= 3:
                sharpes = stats["sharpes"]
                patterns.append({
                    "type": "combo_type",
                    "pattern": ct,
                    "avg_sharpe": round(sum(sharpes) / len(sharpes), 3),
                    "max_sharpe": round(max(sharpes), 3),
                    "sample_size": len(sharpes),
                })

        operator_counter = Counter()
        for alpha in top_alphas:
            expr = alpha.get('expression', '') or ""
            for op in ['ts_mean', 'ts_delta', 'ts_std_dev', 'ts_decay_linear',
                       'ts_sum', 'ts_corr', 'rank', 'zscore', 'winsorize',
                       'signed_power', 'ts_arg_max']:
                if op in expr:
                    operator_counter[op] += 1

        if operator_counter:
            total = len(top_alphas)
            patterns.append({
                "type": "operator_frequency_in_top",
                "operators": {op: round(cnt / total, 2)
                              for op, cnt in operator_counter.most_common(8)},
                "sample_size": total
            })

        return patterns

    def analyze_field_performance(self, dataset: str = None) -> list[dict]:
        """分析哪些字段在历史回测中表现最好"""
        alpha_data = alphas_store.load()
        all_alphas = [e for e in alpha_data["entries"].values()
                      if e.get("status") == "done" and (e.get("sharpe", 0) or 0) > 0]
        all_alphas.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
        all_alphas = all_alphas[:200]

        field_sharpes = {}
        for a in all_alphas:
            expr = a.get('expression', '') or ""
            fields = re.findall(r'\b([a-z][a-z_]+(?:_[a-z]+)+)\b', expr)
            for f in fields:
                if f not in ['ts_mean', 'ts_delta', 'ts_std_dev', 'ts_sum',
                             'ts_decay_linear', 'ts_corr', 'ts_arg_max',
                             'ts_backfill', 'ts_delay']:
                    field_sharpes.setdefault(f, []).append(a.get('sharpe', 0))

        results = []
        for field, sharpes in field_sharpes.items():
            if len(sharpes) >= 3:
                results.append({
                    "field": field,
                    "avg_sharpe": round(sum(sharpes) / len(sharpes), 3),
                    "max_sharpe": round(max(sharpes), 3),
                    "count": len(sharpes)
                })

        results.sort(key=lambda x: x['avg_sharpe'], reverse=True)
        return results[:20]

    @staticmethod
    def _compute_trend(values: list[float]) -> str:
        if len(values) < 3:
            return "insufficient_data"
        recent = sum(values[:len(values)//2]) / max(len(values)//2, 1)
        earlier = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
        if recent > earlier * 1.1:
            return "improving"
        elif recent < earlier * 0.9:
            return "declining"
        return "stable"

    @staticmethod
    def _distribution_stats(values: list[float]) -> dict:
        if not values:
            return {}
        values_sorted = sorted(values)
        n = len(values_sorted)
        return {
            "count": n,
            "min": round(values_sorted[0], 3),
            "p25": round(values_sorted[n//4], 3),
            "median": round(values_sorted[n//2], 3),
            "p75": round(values_sorted[3*n//4], 3),
            "max": round(values_sorted[-1], 3),
            "mean": round(sum(values) / n, 3),
        }
