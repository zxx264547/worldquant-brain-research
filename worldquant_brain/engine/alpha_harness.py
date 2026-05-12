#!/usr/bin/env python3
"""Alpha Harness — 反馈回路系统

基于 JW52291 + JR57542 两篇文章:
    人负责设定方向和约束
    Agent负责执行和验证
    Ledger负责保留事实
    Gate负责防止自欺
    记忆负责避免重复失败

整合:
    - RouteContract (合约)
    - ResearchLedger (记账)
    - TrafficLight (信号灯)
    - ContractEvaluator (Gate检查)
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.engine.route_contract import (
    RouteContract, ContractEvaluator
)
from worldquant_brain.engine.ledger import ResearchRound, ResearchLedger, ledger
from worldquant_brain.engine.traffic_light import (
    evaluate_direction, get_light_emoji
)
from worldquant_brain.engine.result_store import store


class AlphaHarness:
    """Alpha研究反馈回路"""

    def __init__(self, contract: RouteContract = None):
        self.contract = contract or RouteContract.template_eps_usa()
        self.evaluator = ContractEvaluator(self.contract)
        self.ledger = ledger
        self.rounds = []

    def start_round(self, structural_question: str) -> ResearchRound:
        """开始新一轮研究"""
        round_id = f"R{len(self.rounds)+1:03d}-{datetime.now().strftime('%m%d-%H%M')}"
        round_ = ResearchRound(
            round_id=round_id,
            contract_id=self.contract.contract_id or "default",
            structural_question=structural_question,
            started_at=datetime.now().isoformat()
        )
        self.rounds.append(round_)
        return round_

    def feed_result(self, round_: ResearchRound, alpha: dict):
        """向当前轮喂入一个Alpha结果"""
        round_.total_tested += 1

        # Gate评估
        evaluation = self.evaluator.evaluate(alpha)
        failure_type = self.evaluator.classify_failure(alpha)

        # 更新统计
        if evaluation.get('is_check', {}).get('passed'):
            round_.passed_is += 1
        if evaluation.get('self_corr', {}).get('passed'):
            round_.passed_self += 1

        # 失败分类
        if failure_type.startswith('quality'):
            round_.quality_failures += 1
        elif failure_type.startswith('correlation'):
            round_.correlation_failures += 1
        elif failure_type.startswith('threshold'):
            round_.threshold_failures += 1
        elif failure_type == 'infrastructure':
            round_.infrastructure_failures += 1

        # 记录失败
        if failure_type != 'threshold_promising':
            self.ledger.log_failure(round_.round_id, alpha, failure_type)

        # 更新 winner/nearline/closed/blocker
        sharpe = alpha.get('sharpe', 0)
        if evaluation.get('pre_submit', {}).get('ready'):
            # 可提交: 设为winner
            round_.winner = alpha
            round_.decision = 'green'
            round_.decision_reason = f"Sharpe={sharpe:.2f} 达标, 可提交"
        elif evaluation.get('is_check', {}).get('passed'):
            # IS通过但不是submittable: nearline
            round_.nearline.append({
                'alpha_id': alpha.get('alpha_id', ''),
                'sharpe': sharpe,
                'failure_type': failure_type
            })
        elif failure_type.startswith('correlation_prod'):
            # prod-corr失败: blocker
            round_.blocker.append({
                'alpha_id': alpha.get('alpha_id', ''),
                'sharpe': sharpe,
                'prod_corr': alpha.get('prod_correlation'),
                'reason': 'prod-corr 红灯'
            })
        elif sharpe < 0:
            round_.closed.append({
                'alpha_id': alpha.get('alpha_id', ''),
                'sharpe': sharpe,
                'reason': '负Sharpe, 关闭此分支'
            })

    def finish_round(self, round_: ResearchRound,
                     next_question: str = "", decision: str = None):
        """结束当前轮"""
        round_.finished_at = datetime.now().isoformat()

        if decision:
            round_.decision = decision

        # 如果没有人为指定decision，用信号灯自动判断
        if round_.decision == 'unknown' and round_.total_tested >= 3:
            results_for_light = []
            if round_.winner:
                results_for_light.append({'sharpe': round_.winner.get('sharpe', 0)})
            for n in round_.nearline:
                results_for_light.append({'sharpe': n.get('sharpe', 0)})
            if results_for_light:
                light_result = evaluate_direction(results_for_light)
                round_.decision = light_result['light']
                round_.decision_reason = light_result.get('reason', '')

        if next_question:
            round_.next_question = next_question

        # 保存到Ledger
        self.ledger.save_round(round_)
        return round_

    def get_summary(self) -> dict:
        """获取研究总结"""
        rounds = self.ledger.get_rounds(20)
        ledger_summary = self.ledger.get_summary()

        return {
            "contract": self.contract.to_dict(),
            "rounds": rounds,
            "ledger_summary": ledger_summary,
            "best_alpha": store.best(1)[0] if store.best(1) else None,
            "total_alphas": store.count,
        }


# ─── CLI ───

if __name__ == "__main__":
    harness = AlphaHarness(RouteContract.template_breakthrough())

    # 模拟一轮
    round_ = harness.start_round("cashflow字段有原始信号吗？")

    # 喂入模拟结果
    mock_results = [
        {"alpha_id": "TEST1", "sharpe": 0.93, "fitness": 1.3, "ppc": 0.3,
         "margin": 0.08, "turnover": 0.01},
        {"alpha_id": "TEST2", "sharpe": 1.16, "fitness": 1.91, "ppc": 0.15,
         "margin": 0.053, "turnover": 0.013},
        {"alpha_id": "TEST3", "sharpe": -0.5, "fitness": -0.7, "ppc": 0.8,
         "margin": -0.05, "turnover": 0.06},
    ]
    for r in mock_results:
        harness.feed_result(round_, r)

    harness.finish_round(round_, "Beta120+252多信号叠加能突破吗？")
    print("Ledger 摘要:", harness.ledger.get_summary())
