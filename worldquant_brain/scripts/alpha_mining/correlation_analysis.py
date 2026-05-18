#!/usr/bin/env python3
"""
Correlation Analysis - 相关性分族与组内排序
根据PnL序列进行相关性分析，去重筛选，支持API集成
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import json
import numpy as np

from ..core import RetryableBrainClient, BrainAPIError, setup_logging

logger = setup_logging(__name__)


@dataclass
class AlphaInfo:
    """Alpha信息"""
    alpha_id: str
    pnl: List[float]  # PnL序列
    sharpe: float
    fitness: float
    expression: str
    margin: float = 0
    turnover: float = 0

    def to_dict(self) -> dict:
        return {
            'alpha_id': self.alpha_id,
            'sharpe': self.sharpe,
            'fitness': self.fitness,
            'expression': self.expression,
            'margin': self.margin,
            'turnover': self.turnover,
            'pnl_len': len(self.pnl) if self.pnl else 0,
        }


class CorrelationFamily:
    """相关性分族"""

    def __init__(self, correlation_threshold: float = 0.8):
        self.threshold = correlation_threshold
        self.families: Dict[int, List[AlphaInfo]] = {}
        self.alpha_to_family: Dict[str, int] = {}

    def fit(self, alphas: List[AlphaInfo]) -> None:
        """
        执行分族

        步骤：
        1. 计算相关矩阵
        2. 基于阈值构建连通图
        3. 使用并查集找连通分量
        """
        if len(alphas) < 2:
            self.families = {0: alphas}
            for a in alphas:
                self.alpha_to_family[a.alpha_id] = 0
            return

        # 1. 计算相关矩阵
        corr_matrix = self._compute_correlation_matrix(alphas)

        # 2. 构建邻接关系
        n = len(alphas)
        adj = defaultdict(set)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(corr_matrix[i][j]) >= self.threshold:
                    adj[i].add(j)
                    adj[j].add(i)

        # 3. BFS找连通分量
        visited = set()
        family_id = 0

        for start in range(n):
            if start in visited:
                continue

            members = []
            queue = [start]

            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue

                visited.add(node)
                members.append(node)

                for neighbor in adj[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            # 分配family_id
            for member_idx in members:
                self.alpha_to_family[alphas[member_idx].alpha_id] = family_id
            self.families[family_id] = [alphas[m] for m in members]
            family_id += 1

    def _compute_correlation_matrix(self, alphas: List[AlphaInfo]) -> np.ndarray:
        """计算Pearson相关系数矩阵"""
        n = len(alphas)
        matrix = np.zeros((n, n))

        pnls = [np.array(a.pnl) for a in alphas if a.pnl]

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    matrix[i][j] = 1.0
                elif pnls and i < len(pnls) and j < len(pnls):
                    corr = np.corrcoef(pnls[i], pnls[j])[0, 1]
                    matrix[i][j] = corr
                    matrix[j][i] = corr
                else:
                    matrix[i][j] = 0
                    matrix[j][i] = 0

        return matrix

    def get_representatives(self, top_k: int = 1, sort_by: str = 'sharpe') -> List[AlphaInfo]:
        """
        获取每族代表

        每族取评分最高的top_k个Alpha
        """
        representatives = []

        for family_id, members in self.families.items():
            # 按Sharpe降序排序
            sorted_members = sorted(members, key=lambda x: getattr(x, sort_by, 0), reverse=True)
            representatives.extend(sorted_members[:top_k])

        return representatives

    def get_family_stats(self) -> dict:
        """获取分族统计"""
        return {
            "total_families": len(self.families),
            "family_sizes": {
                fid: len(members)
                for fid, members in self.families.items()
            },
            "alpha_to_family": self.alpha_to_family
        }


class CorrelationScreening:
    """基于相关性的筛选，支持API集成"""

    def __init__(
        self,
        credentials: Dict = None,
        correlation_threshold: float = 0.8,
        client: RetryableBrainClient = None
    ):
        self.threshold = correlation_threshold
        self.client = client or (RetryableBrainClient(credentials) if credentials else None)

    async def fetch_pnl(self, alpha_id: str) -> List[float]:
        """从API获取PnL序列

        如果PnL不可用，返回空列表而非None
        """
        if not self.client:
            logger.warning("No API client configured for PnL fetch")
            return []

        try:
            pnl = await self.client.get_pnl_with_retry(alpha_id)
            return pnl if pnl else []
        except AttributeError:
            logger.warning(f"PnL fetch not supported by API client")
            return []
        except BrainAPIError as e:
            logger.warning(f"Failed to fetch PnL for {alpha_id}: {e}")
            return []

    async def load_alpha_with_pnl(self, alpha_data: dict) -> AlphaInfo:
        """加载Alpha数据并获取PnL"""
        alpha_id = alpha_data.get('alpha_id')

        pnl = alpha_data.get('pnl', [])
        if not pnl and self.client:
            pnl = await self.fetch_pnl(alpha_id) or []

        return AlphaInfo(
            alpha_id=alpha_id,
            pnl=pnl,
            sharpe=alpha_data.get('sharpe', 0),
            fitness=alpha_data.get('fitness', 0),
            expression=alpha_data.get('expression', ''),
            margin=alpha_data.get('margin', 0),
            turnover=alpha_data.get('turnover', 0),
        )

    async def screen(
        self,
        alphas: List[dict],
        top_k_per_family: int = 2,
        fetch_pnl: bool = False
    ) -> Tuple[List[AlphaInfo], Dict]:
        """
        筛选Alpha

        流程：
        1. 加载Alpha数据（可选获取PnL）
        2. 相关性分族
        3. 族内按Sharpe排序
        4. 每族取top_k代表

        Returns:
            (筛选结果, 分族统计)
        """
        # 加载Alpha数据
        if fetch_pnl and self.client:
            alpha_infos = await asyncio.gather(*[
                self.load_alpha_with_pnl(a) for a in alphas
            ])
        else:
            alpha_infos = [
                AlphaInfo(
                    alpha_id=a.get('alpha_id', ''),
                    pnl=a.get('pnl', []),
                    sharpe=a.get('sharpe', 0),
                    fitness=a.get('fitness', 0),
                    expression=a.get('expression', ''),
                    margin=a.get('margin', 0),
                    turnover=a.get('turnover', 0),
                )
                for a in alphas
            ]

        # 分族
        family_model = CorrelationFamily(self.threshold)
        family_model.fit(alpha_infos)

        # 取代表
        representatives = family_model.get_representatives(top_k_per_family)

        # 统计
        stats = family_model.get_family_stats()

        return representatives, stats

    def screen_local(
        self,
        alphas: List[AlphaInfo],
        top_k_per_family: int = 2
    ) -> Tuple[List[AlphaInfo], Dict]:
        """
        本地模式筛选（已有PnL数据）
        """
        family_model = CorrelationFamily(self.threshold)
        family_model.fit(alphas)
        representatives = family_model.get_representatives(top_k_per_family)
        stats = family_model.get_family_stats()
        return representatives, stats

    def deduplicate(
        self,
        alphas: List[AlphaInfo],
        threshold: float = None
    ) -> List[AlphaInfo]:
        """
        去重：基于相关性分族，每族保留Sharpe最高的

        Args:
            alphas: Alpha列表
            threshold: 相关性阈值（默认使用初始化时的值）
        """
        if threshold:
            self.threshold = threshold

        family_model = CorrelationFamily(self.threshold)
        family_model.fit(alphas)
        return family_model.get_representatives(top_k=1)


def main():
    """测试"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    screener = CorrelationScreening(threshold=0.8)

    # 模拟数据（带PnL）
    alphas = [
        AlphaInfo("a1", [0.1, 0.2, 0.15, 0.18, 0.12], 1.2, 0.6, "exp1", 0.05, 0.02),
        AlphaInfo("a2", [0.11, 0.19, 0.16, 0.17, 0.13], 1.1, 0.5, "exp2", 0.04, 0.02),
        AlphaInfo("a3", [0.05, -0.1, 0.08, 0.12, 0.09], 0.8, 0.4, "exp3", 0.03, 0.02),
        AlphaInfo("a4", [-0.05, 0.1, -0.08, -0.12, -0.07], 0.7, 0.3, "exp4", 0.02, 0.02),
    ]

    results, stats = screener.screen_local(alphas, top_k_per_family=1)

    print(f"输入: {len(alphas)} 个Alpha")
    print(f"输出: {len(results)} 个Alpha（去重后）")
    print(f"分族统计: {json.dumps(stats, indent=2)}")

    for r in results:
        print(f"  - {r.alpha_id}: Sharpe={r.sharpe}, Fitness={r.fitness}")


if __name__ == "__main__":
    main()