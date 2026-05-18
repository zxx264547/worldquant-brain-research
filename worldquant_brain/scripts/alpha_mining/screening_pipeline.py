#!/usr/bin/env python3
"""
Alpha Screening Pipeline - 多轮筛选Pipeline
根据PPA标准进行多轮筛选，支持API集成
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json

from ..core import RetryableBrainClient, BrainAPIError, setup_logging

logger = setup_logging(__name__)


# ============ PPA筛选标准 ============
PPA_STANDARDS = {
    "ppc_max": 0.5,           # PPC必须小于0.5
    "sharpe_min": 1.0,        # Sharpe建议>=1.05
    "sharpe_target": 1.58,    # 目标Sharpe
    "fitness_min": 0.5,        # Fitness必须大于0.5
    "margin_gt_turnover": True,  # Margin必须大于Turnover
    "turnover_min": 0.01,      # Turnover最小值
}


@dataclass
class ScreeningResult:
    """筛选结果"""
    alpha_id: str
    expression: str
    passed: bool
    sharpe: float
    fitness: float
    ppc: float
    margin: float
    turnover: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'alpha_id': self.alpha_id,
            'expression': self.expression,
            'passed': self.passed,
            'sharpe': self.sharpe,
            'fitness': self.fitness,
            'ppc': self.ppc,
            'margin': self.margin,
            'turnover': self.turnover,
            'reasons': self.reasons
        }


class ScreeningPipeline:
    """多轮筛选Pipeline，支持API集成"""

    def __init__(
        self,
        credentials: Dict = None,
        standards: dict = None,
        client: RetryableBrainClient = None
    ):
        self.standards = standards or PPA_STANDARDS
        self.history: List[ScreeningResult] = []
        self.client = client or (RetryableBrainClient(credentials) if credentials else None)

    async def fetch_alpha(self, alpha_id: str) -> Optional[Dict]:
        """从API获取Alpha数据"""
        if not self.client:
            logger.error("No API client configured")
            return None

        try:
            return await self.client.get_alpha_with_retry(alpha_id)
        except BrainAPIError as e:
            logger.error(f"Failed to fetch alpha {alpha_id}: {e}")
            return None

    def screen(self, alpha_data: dict) -> ScreeningResult:
        """
        筛选单个Alpha（本地模式）

        alpha_data格式:
        {
            "alpha_id": "xxx",
            "ppc": 0.3,
            "sharpe": 1.2,
            "fitness": 0.6,
            "turnover": 0.1,
            "margin": 0.15,
            "expression": "...",
        }
        """
        reasons = []
        passed = True

        # 1. PPC检查（核心门槛）
        ppc = alpha_data.get("ppc", 1.0)
        if ppc >= self.standards["ppc_max"]:
            passed = False
            reasons.append(f"PPC {ppc:.3f} >= {self.standards['ppc_max']}")

        # 2. Sharpe检查
        sharpe = alpha_data.get("sharpe", 0)
        if sharpe < self.standards["sharpe_min"]:
            passed = False
            reasons.append(f"Sharpe {sharpe:.2f} < {self.standards['sharpe_min']}")

        # 3. Fitness检查
        fitness = alpha_data.get("fitness", 0)
        if fitness < self.standards["fitness_min"]:
            passed = False
            reasons.append(f"Fitness {fitness:.2f} < {self.standards['fitness_min']}")

        # 4. Margin > Turnover
        margin = alpha_data.get("margin", 0)
        turnover = alpha_data.get("turnover", 0)
        if self.standards.get("margin_gt_turnover") and margin <= turnover:
            passed = False
            reasons.append(f"Margin {margin:.4f} <= Turnover {turnover:.4f}")

        # 5. Turnover检查
        if turnover < self.standards.get("turnover_min", 0):
            passed = False
            reasons.append(f"Turnover {turnover:.4f} < {self.standards['turnover_min']}")

        result = ScreeningResult(
            alpha_id=alpha_data.get("alpha_id", ""),
            expression=alpha_data.get("expression", ""),
            passed=passed,
            sharpe=sharpe,
            fitness=fitness,
            ppc=ppc,
            margin=margin,
            turnover=turnover,
            reasons=reasons
        )

        self.history.append(result)
        return result

    async def screen_alpha(self, alpha_id: str) -> ScreeningResult:
        """从API获取并筛选Alpha（API模式）"""
        alpha_data = await self.fetch_alpha(alpha_id)

        if not alpha_data:
            return ScreeningResult(
                alpha_id=alpha_id,
                expression="",
                passed=False,
                sharpe=0, fitness=0, ppc=1, margin=0, turnover=0,
                reasons=["Failed to fetch alpha data"]
            )

        return self.screen(alpha_data)

    async def screen_batch(
        self,
        alpha_ids: List[str],
        concurrency: int = 5
    ) -> Tuple[List[ScreeningResult], List[ScreeningResult]]:
        """批量筛选（并发控制）

        Returns:
            (通过列表, 未通过列表)
        """
        passed = []
        rejected = []

        semaphore = asyncio.Semaphore(concurrency)

        async def screen_with_limit(alpha_id: str):
            async with semaphore:
                return await self.screen_alpha(alpha_id)

        tasks = [screen_with_limit(aid) for aid in alpha_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Screening error: {result}")
                continue

            if result.passed:
                passed.append(result)
            else:
                rejected.append(result)

        self.history.extend(passed + rejected)
        return passed, rejected

    def screen_local_batch(
        self,
        alphas: List[dict]
    ) -> Tuple[List[ScreeningResult], List[ScreeningResult]]:
        """批量筛选（本地模式）"""
        passed = []
        rejected = []

        for alpha in alphas:
            result = self.screen(alpha)
            if result.passed:
                passed.append(result)
            else:
                rejected.append(result)

        return passed, rejected

    def get_report(self) -> dict:
        """生成筛选报告"""
        total = len(self.history)
        passed = [r for r in self.history if r.passed]

        rejection_reasons = {}
        for r in self.history:
            if not r.passed:
                for reason in r.reasons:
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        return {
            "total": total,
            "passed": len(passed),
            "rejected": total - len(passed),
            "pass_rate": len(passed) / total if total > 0 else 0,
            "top_rejection_reasons": sorted(
                rejection_reasons.items(),
                key=lambda x: -x[1]
            )[:10],
            "avg_metrics": {
                "sharpe": sum(r.sharpe for r in self.history) / total if total > 0 else 0,
                "fitness": sum(r.fitness for r in self.history) / total if total > 0 else 0,
                "ppc": sum(r.ppc for r in self.history) / total if total > 0 else 0,
            }
        }

    def save_report(self, output_path: str):
        """保存筛选报告"""
        report = self.get_report()

        results = {
            'report': report,
            'passed': [r.to_dict() for r in self.history if r.passed],
            'rejected': [r.to_dict() for r in self.history if not r.passed],
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"报告已保存到: {output_path}")

    def get_submittable(self) -> List[ScreeningResult]:
        """获取满足PPA所有条件的Alpha"""
        return [r for r in self.history if r.passed and r.sharpe >= self.standards.get("sharpe_target", 1.58)]


async def main():
    """测试"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    pipeline = ScreeningPipeline()

    # 测试数据
    test_alphas = [
        {
            "alpha_id": "alpha001",
            "expression": "winsorize(pv87_field)",
            "ppc": 0.3,
            "sharpe": 1.2,
            "fitness": 0.6,
            "turnover": 0.1,
            "margin": 0.15,
        },
        {
            "alpha_id": "alpha002",
            "expression": "ts_mean(pv87_field, 20)",
            "ppc": 0.6,  # 超过0.5
            "sharpe": 1.5,
            "fitness": 0.7,
            "turnover": 0.1,
            "margin": 0.2,
        },
        {
            "alpha_id": "alpha003",
            "expression": "rank(pv87_field)",
            "ppc": 0.4,
            "sharpe": 1.8,
            "fitness": 0.8,
            "turnover": 0.05,
            "margin": 0.08,  # margin > turnover
        },
    ]

    passed, rejected = pipeline.screen_local_batch(test_alphas)

    print(f"通过: {len(passed)}")
    print(f"拒绝: {len(rejected)}")

    for r in passed:
        print(f"  ✅ {r.alpha_id}: Sharpe={r.sharpe:.2f}")

    for r in rejected:
        print(f"  ❌ {r.alpha_id}: {r.reasons}")

    report = pipeline.get_report()
    print(f"\n报告: {json.dumps(report, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())