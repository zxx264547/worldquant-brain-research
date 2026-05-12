#!/usr/bin/env python3
"""编排化挖掘 — 调用Orchestrator, 激活全部新架构模块

替代 robust_mining.py, 使用:
  Orchestrator → WorkerPool → Strategies → BacktestRunner → SQLite → AlphaHarness
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.scheduler import Orchestrator
from worldquant_brain.engine.alpha_harness import AlphaHarness
from worldquant_brain.engine.route_contract import RouteContract


async def main():
    contract = RouteContract.template_breakthrough()
    harness = AlphaHarness(contract)

    orch = Orchestrator(
        strategy_names=['combination', 'knowledge_guided'],
        worker_count=4
    )

    # 注入harness到Runner
    from worldquant_brain.engine.backtest_runner import BacktestRunner
    BacktestRunner._shared_harness = harness

    # 开始一轮
    round_ = harness.start_round("哪些非EPS字段组合能突破Sharpe 1.17？")
    harness.current_round = round_

    await orch.run()

    harness.finish_round(round_, "分析结果, 确定下一步方向")
    print(harness.get_summary())


if __name__ == "__main__":
    asyncio.run(main())