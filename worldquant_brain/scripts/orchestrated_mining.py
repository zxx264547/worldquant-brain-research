#!/usr/bin/env python3
"""编排化挖掘 — 使用Orchestrator进行持续Alpha挖掘"""
import asyncio, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.scheduler.orchestrator import Orchestrator
from worldquant_brain.engine.alpha_harness import AlphaHarness
from worldquant_brain.engine.route_contract import RouteContract
from worldquant_brain.engine import ExpressionTemplates


async def main():
    contract = RouteContract.template_breakthrough()
    harness = AlphaHarness(contract)

    strategies = ['combination', 'single_field', 'settings_optimize']
    worker_count = 4
    rounds = 0

    while True:
        rounds += 1
        print(f"\n{'='*50}")
        print(f"  Round {rounds}")
        print(f"{'='*50}")

        # 每轮更新上下文
        context = {
            "base_alphas": [
                ("eps_252_09", ExpressionTemplates.eps_basic()),
                ("eps_mom", ExpressionTemplates.eps_with_momentum()),
                ("eps_div", ExpressionTemplates.eps_with_dividend()),
            ],
            "technicals": [
                ("beta_120", ExpressionTemplates.tech_beta(120)),
                ("beta_252", ExpressionTemplates.tech_beta(252)),
                ("vol_120", ExpressionTemplates.tech_vol(120)),
                ("vol_252", ExpressionTemplates.tech_vol(252)),
                ("rsi_14", ExpressionTemplates.tech_rsi(14)),
                ("mom_60", ExpressionTemplates.tech_momentum(60)),
            ],
            "regions": ["USA"],
        }

        # 开始记账轮
        round_ = harness.start_round(f"Round {rounds}: 探索EPS+技术信号组合")
        harness.current_round = round_

        # 每轮换一批策略
        current_strats = [strategies[rounds % len(strategies)]]

        orch = Orchestrator(current_strats, worker_count)
        await orch.run(context)

        # 结束记账
        harness.finish_round(round_, f"Round {rounds+1}: 继续探索")

        # 短暂休息
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())