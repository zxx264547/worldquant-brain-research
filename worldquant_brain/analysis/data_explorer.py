"""数据探索器 — 通用数据分析能力

提供数据集探索、字段分析、模式发现等能力，
分析结果通过 ReportGenerator 自动沉淀为知识。
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter


class DataExplorer:
    """通用数据分析工具（基于本地历史数据）"""

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.brain_db = self.root / "worldquant_brain" / "data" / "brain.db"

    def analyze_experiment_trends(self, last_n: int = 50) -> dict:
        """分析最近N次实验的趋势

        Returns:
            策略表现趋势、Sharpe分布、成功率变化
        """
        if not self.brain_db.exists():
            return {"status": "no_data"}

        conn = sqlite3.connect(str(self.brain_db))
        conn.row_factory = sqlite3.Row

        # 实验趋势
        experiments = conn.execute("""
            SELECT strategy, best_sharpe, started_at, total_tasks, completed_tasks
            FROM experiments WHERE status='done'
            ORDER BY started_at DESC LIMIT ?
        """, (last_n,)).fetchall()

        # Alpha 分布
        alphas = conn.execute("""
            SELECT sharpe, fitness, ppc, margin, turnover, combo_type, created_at
            FROM alphas WHERE status='done'
            ORDER BY created_at DESC LIMIT ?
        """, (last_n * 8,)).fetchall()

        conn.close()

        if not experiments:
            return {"status": "no_experiments"}

        # 策略表现统计
        strategy_stats = {}
        for exp in experiments:
            s = exp['strategy']
            if s not in strategy_stats:
                strategy_stats[s] = {"runs": 0, "sharpes": [], "total_tasks": 0}
            strategy_stats[s]["runs"] += 1
            strategy_stats[s]["sharpes"].append(exp['best_sharpe'] or 0)
            strategy_stats[s]["total_tasks"] += exp['total_tasks'] or 0

        for s, stats in strategy_stats.items():
            sharpes = stats["sharpes"]
            stats["avg_sharpe"] = round(sum(sharpes) / len(sharpes), 3) if sharpes else 0
            stats["max_sharpe"] = round(max(sharpes), 3) if sharpes else 0
            stats["trend"] = self._compute_trend(sharpes)
            del stats["sharpes"]

        # Sharpe 分布
        all_sharpes = [a['sharpe'] for a in alphas if a['sharpe'] is not None]
        sharpe_dist = self._distribution_stats(all_sharpes)

        # PPA 通过率
        ppa_pass = sum(1 for a in alphas
                       if (a['sharpe'] or 0) >= 1.58 and
                       (a['fitness'] or 0) > 0.5 and
                       (a['ppc'] or 1) < 0.5 and
                       (a['margin'] or 0) > (a['turnover'] or 1))

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
        """基于历史结果发现高潜力的模式

        分析维度：
        - 哪些 combo_type 表现最好
        - 高Sharpe Alpha 的共同特征
        """
        if not self.brain_db.exists():
            return []

        conn = sqlite3.connect(str(self.brain_db))
        conn.row_factory = sqlite3.Row

        # 按 combo_type 统计
        combos = conn.execute("""
            SELECT combo_type, COUNT(*) as cnt, AVG(sharpe) as avg_sharpe,
                   MAX(sharpe) as max_sharpe
            FROM alphas WHERE status='done' AND combo_type != ''
            GROUP BY combo_type HAVING cnt >= 3
            ORDER BY avg_sharpe DESC
        """).fetchall()

        # 高Sharpe表达式的算子分析
        top_alphas = conn.execute("""
            SELECT expression, sharpe FROM alphas
            WHERE status='done' AND sharpe >= 0.8
            ORDER BY sharpe DESC LIMIT 50
        """).fetchall()

        conn.close()

        patterns = []

        # 模式1: 最佳组合类型
        for c in combos:
            patterns.append({
                "type": "combo_type",
                "pattern": c['combo_type'],
                "avg_sharpe": round(c['avg_sharpe'], 3),
                "max_sharpe": round(c['max_sharpe'], 3),
                "sample_size": c['cnt']
            })

        # 模式2: 算子频率分析
        operator_counter = Counter()
        for alpha in top_alphas:
            expr = alpha['expression'] or ""
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
        if not self.brain_db.exists():
            return []

        conn = sqlite3.connect(str(self.brain_db))
        conn.row_factory = sqlite3.Row

        alphas = conn.execute("""
            SELECT expression, sharpe FROM alphas
            WHERE status='done' AND sharpe > 0
            ORDER BY sharpe DESC LIMIT 200
        """).fetchall()
        conn.close()

        # 提取字段名模式
        import re
        field_sharpes = {}
        for a in alphas:
            expr = a['expression'] or ""
            # 匹配可能的字段名（通常在函数调用的第一个参数位置）
            fields = re.findall(r'\b([a-z][a-z_]+(?:_[a-z]+)+)\b', expr)
            for f in fields:
                if f not in ['ts_mean', 'ts_delta', 'ts_std_dev', 'ts_sum',
                             'ts_decay_linear', 'ts_corr', 'ts_arg_max',
                             'ts_backfill', 'ts_delay']:
                    field_sharpes.setdefault(f, []).append(a['sharpe'])

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
        """计算简单趋势"""
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
