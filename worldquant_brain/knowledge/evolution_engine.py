"""自进化引擎 — 基于累积证据自动调整策略和提议规则修改

三级进化通道：
- L1（自动）：策略效果分数、优先级、模板列表
- L2（提议）：CLAUDE.md 规则、PPA 阈值、时间窗口
- L3（记录）：代码结构改进建议
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional

from .unified_store import UnifiedKnowledgeStore


class EvolutionEngine:
    """自进化引擎"""

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.store = UnifiedKnowledgeStore(self.root)
        self.config_path = self.root / "worldquant_brain" / "strategies" / "strategy_config.yaml"

    # ═══════════════════════════════════════════
    #  L1: 自动进化 — 策略配置
    # ═══════════════════════════════════════════

    def load_strategy_config(self) -> dict:
        """加载策略配置（不存在则返回默认）"""
        if self.config_path.exists():
            return yaml.safe_load(self.config_path.read_text())
        return self._default_config()

    def save_strategy_config(self, config: dict):
        """保存策略配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False))

    def update_effectiveness(self, strategy_name: str, sharpe_result: float):
        """根据回测结果更新策略效果分数（L1自动）"""
        config = self.load_strategy_config()
        for s in config.get("strategies", []):
            if s["name"] == strategy_name:
                old = s.get("effectiveness", 0.5)
                if sharpe_result >= 1.0:
                    s["effectiveness"] = min(old + 0.1, 1.0)
                elif sharpe_result < 0.3:
                    s["effectiveness"] = max(old - 0.05, 0.0)
                s["last_tested"] = datetime.now().strftime("%Y-%m-%d")
                break
        self.save_strategy_config(config)

    def reorder_strategies(self):
        """根据效果分数自动重排策略优先级（L1自动）"""
        config = self.load_strategy_config()
        strategies = config.get("strategies", [])
        strategies.sort(key=lambda s: s.get("effectiveness", 0.5), reverse=True)
        for i, s in enumerate(strategies):
            s["priority"] = i + 1
        config["strategies"] = strategies
        self.save_strategy_config(config)

    def add_template(self, strategy_name: str, template: str):
        """给策略添加新模板（L1自动）"""
        config = self.load_strategy_config()
        for s in config.get("strategies", []):
            if s["name"] == strategy_name:
                if template not in s.get("templates", []):
                    s.setdefault("templates", []).append(template)
                break
        self.save_strategy_config(config)

    # ═══════════════════════════════════════════
    #  L2: 提议进化 — 规则/阈值修改
    # ═══════════════════════════════════════════

    def propose_threshold_change(self, metric: str, current: float,
                                 proposed: float, evidence: str) -> int:
        """提议修改PPA阈值（需人工审批）"""
        return self.store.propose_rule_change(
            rule_type="threshold",
            old_value=f"{metric}={current}",
            new_value=f"{metric}={proposed}",
            reason=evidence
        )

    def propose_window_addition(self, window: int, evidence: str) -> int:
        """提议添加新的时间窗口"""
        config = self.load_strategy_config()
        current_windows = config.get("allowed_windows", [5, 22, 66, 120, 252, 504])
        return self.store.propose_rule_change(
            rule_type="workflow",
            old_value=f"allowed_windows={current_windows}",
            new_value=f"allowed_windows={sorted(current_windows + [window])}",
            reason=evidence
        )

    def propose_rule_update(self, rule_section: str, description: str,
                            evidence: str) -> int:
        """提议更新CLAUDE.md中的规则"""
        return self.store.propose_rule_change(
            rule_type="workflow",
            old_value=f"section={rule_section}",
            new_value=description,
            reason=evidence
        )

    # ═══════════════════════════════════════════
    #  L3: 记录 — 架构改进建议
    # ═══════════════════════════════════════════

    def record_improvement_proposal(self, title: str, description: str,
                                    category: str = "architecture") -> int:
        """记录代码/架构改进建议（不自动执行）"""
        return self.store._record_event(
            event_type="proposal",
            source="evolution_engine",
            content={"title": title, "description": description,
                     "category": category, "status": "proposed"},
            confidence=0.7
        )

    # ═══════════════════════════════════════════
    #  综合进化分析
    # ═══════════════════════════════════════════

    def analyze_and_evolve(self) -> dict:
        """综合分析所有证据，执行L1自动进化，生成L2提议

        Returns:
            {"l1_changes": [...], "l2_proposals": [...], "l3_proposals": [...]}
        """
        result = {"l1_changes": [], "l2_proposals": [], "l3_proposals": []}

        # L1: 基于实验结果自动调整
        effectiveness = self.store._get_strategy_effectiveness()
        if effectiveness:
            self.reorder_strategies()
            result["l1_changes"].append("策略优先级已按效果重排")

        # L2: 基于提交结果提议阈值修改
        submit_patterns = self.store.get_submit_patterns()
        if submit_patterns["total"] >= 5:
            accepted_range = submit_patterns.get("accepted_sharpe_range", {})
            if accepted_range.get("min", 999) < 1.58:
                pid = self.propose_threshold_change(
                    "sharpe_min", 1.58,
                    round(accepted_range["min"] - 0.02, 2),
                    f"有Alpha以Sharpe<1.58被接受(最低{accepted_range['min']})"
                )
                result["l2_proposals"].append(
                    f"提议降低Sharpe阈值 (rule_change_id={pid})")

        # L2: 基于反模式提议规避规则
        anti_patterns = self.store.get_anti_patterns(min_confidence=0.8)
        if len(anti_patterns) >= 3:
            patterns_summary = [ap["content"].get("pattern", "") for ap in anti_patterns[:5]]
            pid = self.propose_rule_update(
                "故障排查表",
                f"新增反模式规避: {', '.join(patterns_summary)}",
                f"基于{len(anti_patterns)}条高置信度反模式记录"
            )
            result["l2_proposals"].append(f"提议更新故障排查表 (rule_change_id={pid})")

        return result

    @staticmethod
    def _default_config() -> dict:
        return {
            "strategies": [
                {
                    "name": "analyst4_eps",
                    "priority": 1,
                    "effectiveness": 0.5,
                    "datasets": ["analyst4"],
                    "templates": [
                        "rank(ts_mean({data}, 22))",
                        "rank(ts_delta({data}, 22))",
                        "zscore(ts_mean({data}, 66))",
                    ],
                    "last_tested": None,
                },
                {
                    "name": "pv87_momentum",
                    "priority": 2,
                    "effectiveness": 0.5,
                    "datasets": ["pv87"],
                    "templates": [
                        "rank(ts_mean({data}, 5))",
                        "rank(ts_delta({data}, 22))",
                        "rank(ts_std_dev({data}, 22))",
                    ],
                    "last_tested": None,
                },
                {
                    "name": "fundamental_value",
                    "priority": 3,
                    "effectiveness": 0.5,
                    "datasets": ["fundamental6"],
                    "templates": [
                        "rank({data})",
                        "rank(ts_mean({data}, 66))",
                        "zscore(ts_mean({data}, 252))",
                    ],
                    "last_tested": None,
                },
            ],
            "thresholds": {
                "sharpe_min": 1.58,
                "fitness_min": 0.5,
                "ppc_max": 0.5,
                "margin_gt_turnover": True,
            },
            "allowed_windows": [5, 22, 66, 120, 252, 504],
            "last_evolved": None,
        }
