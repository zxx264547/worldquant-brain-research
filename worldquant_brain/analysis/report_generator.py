"""报告生成器 — 将分析结果生成Markdown报告并自动沉淀为知识

核心思想：所有数据分析的结论都应该变成AI的长期记忆。
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from worldquant_brain.knowledge.unified_store import UnifiedKnowledgeStore


class ReportGenerator:
    """生成分析报告并自动沉淀为知识"""

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.store = UnifiedKnowledgeStore(self.root)
        self.reports_dir = self.root / "worldquant_brain" / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_experiment_report(self, analysis: dict) -> str:
        """生成实验趋势报告"""
        lines = [
            f"# 实验分析报告",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**实验数**: {analysis.get('experiment_count', 0)}",
            f"**Alpha数**: {analysis.get('alpha_count', 0)}",
            f"**PPA通过率**: {analysis.get('ppa_pass_rate', 0):.2%}",
            f"",
            f"## 策略表现",
            f"",
            f"| 策略 | 运行次数 | 平均Sharpe | 最高Sharpe | 趋势 |",
            f"|------|----------|-----------|-----------|------|",
        ]

        for name, stats in analysis.get("strategy_stats", {}).items():
            lines.append(
                f"| {name} | {stats['runs']} | {stats['avg_sharpe']} | "
                f"{stats['max_sharpe']} | {stats['trend']} |"
            )

        # Sharpe分布
        dist = analysis.get("sharpe_distribution", {})
        if dist:
            lines.extend([
                f"",
                f"## Sharpe分布",
                f"",
                f"- 最小: {dist.get('min', 0)}",
                f"- 25%: {dist.get('p25', 0)}",
                f"- 中位数: {dist.get('median', 0)}",
                f"- 75%: {dist.get('p75', 0)}",
                f"- 最大: {dist.get('max', 0)}",
                f"- 均值: {dist.get('mean', 0)}",
            ])

        return "\n".join(lines)

    def generate_pattern_report(self, patterns: list[dict]) -> str:
        """生成模式发现报告"""
        lines = [
            f"# 模式发现报告",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**发现模式数**: {len(patterns)}",
            f"",
        ]

        combo_patterns = [p for p in patterns if p['type'] == 'combo_type']
        if combo_patterns:
            lines.extend([
                "## 组合类型表现",
                "",
                "| 类型 | 平均Sharpe | 最高Sharpe | 样本数 |",
                "|------|-----------|-----------|--------|",
            ])
            for p in combo_patterns:
                lines.append(
                    f"| {p['pattern']} | {p['avg_sharpe']} | "
                    f"{p['max_sharpe']} | {p['sample_size']} |")

        op_patterns = [p for p in patterns if p['type'] == 'operator_frequency_in_top']
        if op_patterns:
            lines.extend(["", "## 高Sharpe Alpha中的算子频率", ""])
            for p in op_patterns:
                for op, freq in p['operators'].items():
                    lines.append(f"- `{op}`: {freq:.0%} 的高Sharpe Alpha 使用")

        return "\n".join(lines)

    def save_report(self, report: str, name: str) -> Path:
        """保存报告到文件"""
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{name}.md"
        path = self.reports_dir / filename
        path.write_text(report, encoding='utf-8')
        return path

    def deposit_to_knowledge(self, report: str, title: str,
                             confidence: float = 0.6) -> int:
        """将报告的关键结论沉淀为知识事件"""
        # 提取前500字符作为摘要
        summary = report[:500].replace('\n', ' ').strip()
        event_id = self.store.record_insight(
            insight=f"[分析报告] {title}: {summary}",
            source="report_generator",
            confidence=confidence,
            metadata={"title": title, "report_length": len(report)}
        )
        return event_id

    def full_analysis_cycle(self) -> dict:
        """完整分析→报告→沉淀循环"""
        from worldquant_brain.analysis.data_explorer import DataExplorer
        explorer = DataExplorer(self.root)

        results = {"reports": [], "knowledge_events": []}

        # 实验趋势分析
        trends = explorer.analyze_experiment_trends()
        if trends.get("status") == "ok":
            report = self.generate_experiment_report(trends)
            path = self.save_report(report, "experiment_trends")
            eid = self.deposit_to_knowledge(report, "实验趋势分析",
                                            confidence=0.65)
            results["reports"].append(str(path))
            results["knowledge_events"].append(eid)

        # 模式发现
        patterns = explorer.find_promising_patterns()
        if patterns:
            report = self.generate_pattern_report(patterns)
            path = self.save_report(report, "patterns")
            eid = self.deposit_to_knowledge(report, "模式发现",
                                            confidence=0.7)
            results["reports"].append(str(path))
            results["knowledge_events"].append(eid)

        return results
