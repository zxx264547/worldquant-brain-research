#!/usr/bin/env python3
"""
PnL Scoring Calculator - Alpha续航力评分
根据PnL曲线计算Alpha的OS预期表现
"""

import json
import logging
import math
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """评分结果"""
    alpha_id: str
    d1: float  # 近期K-Ratio
    d2: float  # 趋势轨迹
    d3: float  # Hurst指数
    d4: float  # 近期健康度
    total_score: float  # 总分 0-100
    label: str  # STRONG BUY/BUY/HOLD/AVOID


class PnlScoringCalculator:
    """
    Alpha续航力评分计算器

    四维度评分：
    - D1 近期K-Ratio (30%)
    - D2 趋势轨迹 (25%)
    - D3 Hurst指数 (20%)
    - D4 近期健康度 (25%)
    """

    def __init__(self):
        self.weights = {
            "d1": 0.30,
            "d2": 0.25,
            "d3": 0.20,
            "d4": 0.25
        }

    def calculate(
        self,
        alpha_id: str,
        pnl: List[float],
        window_short: int = 126,
        window_long: int = 504
    ) -> ScoringResult:
        """
        计算续航力评分

        pnl: 每日PnL序列
        window_short: 短期窗口（默认126天）
        window_long: 长期窗口（默认504天=2年）
        """
        pnl_array = np.array(pnl)

        # 计算净值曲线
        nav = np.cumsum(pnl_array)

        # D1: 近期K-Ratio
        d1 = self._calc_k_ratio(nav, window_short)

        # D2: 趋势轨迹
        d2 = self._calc_trend(nav, window_long)

        # D3: Hurst指数
        d3 = self._calc_hurst(pnl_array, window_long)

        # D4: 近期健康度
        d4 = self._calc_recent_health(pnl_array, window_short, window_long)

        # 加权求和
        total = (
            self.weights["d1"] * d1 +
            self.weights["d2"] * d2 +
            self.weights["d3"] * d3 +
            self.weights["d4"] * d4
        )

        # 映射到0-100
        total_score = min(100, max(0, total * 100))

        # 标签
        label = self._get_label(total_score)

        return ScoringResult(
            alpha_id=alpha_id,
            d1=d1,
            d2=d2,
            d3=d3,
            d4=d4,
            total_score=total_score,
            label=label
        )

    def _calc_k_ratio(self, nav: np.ndarray, window: int) -> float:
        """
        计算K-Ratio

        对log(净值)做线性回归，斜率/标准误 × √252/n
        """
        if len(nav) < window:
            return 0.0

        recent_nav = nav[-window:]
        log_nav = np.log(recent_nav)

        # 线性回归
        x = np.arange(len(log_nav))
        y = log_nav

        # 最小二乘法
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        y_pred = slope * x
        residuals = y - y_pred
        std_err = np.std(residuals)

        if std_err == 0:
            return 0.0

        k_ratio = slope / std_err * math.sqrt(252 / n)

        # 归一化到0-1
        # K >= 2 为满分
        return min(1.0, k_ratio / 2.0)

    def _calc_trend(self, nav: np.ndarray, window: int) -> float:
        """
        计算趋势轨迹

        后两段斜率一致性 + 尾段强度 + 整体R²
        """
        if len(nav) < window:
            return 0.0

        recent_nav = nav[-window:]

        # 分4段
        n = len(recent_nav)
        segment_size = n // 4

        segments = [
            recent_nav[i * segment_size:(i + 1) * segment_size]
            for i in range(4)
        ]

        # 计算每段斜率
        slopes = []
        for seg in segments:
            if len(seg) > 1:
                slope = (seg[-1] - seg[0]) / (len(seg) - 1)
                slopes.append(slope)

        if len(slopes) < 2:
            return 0.0

        # 后两段一致性
        consistency = 1.0 if slopes[-1] * slopes[-2] > 0 else 0.0

        # 尾段强度
        tail_strength = min(1.0, max(0, slopes[-1] / 0.01))

        # 整体R²
        x = np.arange(len(recent_nav))
        y = recent_nav
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        y_pred = slope * x
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        score = (consistency * 0.4 + tail_strength * 0.3 + r_squared * 0.3)

        return min(1.0, max(0, score))

    def _calc_hurst(self, returns: np.ndarray, window: int) -> float:
        """
        计算Hurst指数

        R/S分析
        """
        if len(returns) < window:
            return 0.0

        recent_returns = returns[-window:]

        # 不同窗口计算极差/标准差
        window_sizes = [10, 20, 50, 100]
        hurst_values = []

        for ws in window_sizes:
            if ws > len(recent_returns) // 2:
                continue

            rs_samples = []
            for start in range(0, len(recent_returns) - ws, ws):
                segment = recent_returns[start:start + ws]
                mean = np.mean(segment)
                cumdev = np.cumsum(segment - mean)
                R = np.max(cumdev) - np.min(cumdev)
                S = np.std(segment, ddof=1)
                if S > 0:
                    rs_samples.append(R / S)

            if rs_samples:
                hurst_values.append(np.mean(rs_samples))

        if not hurst_values:
            return 0.0

        # 回归取斜率（简化版）
        hurst = np.mean(hurst_values)
        hurst = min(1.0, hurst / 2.0)  # 归一化

        return hurst

    def _calc_recent_health(
        self,
        returns: np.ndarray,
        window_short: int,
        window_long: int
    ) -> float:
        """
        计算近期健康度

        近3月日均PnL/两年日均 + 最后1月Sharpe + 滚动Sharpe斜率
        """
        if len(returns) < window_long:
            return 0.0

        # 近3月/两年日均
        recent_3m = returns[-window_short:]
        avg_recent = np.mean(recent_3m)
        avg_long = np.mean(returns[-window_long:])
        ratio = avg_recent / avg_long if avg_long > 0 else 0

        # 最后1月Sharpe
        month_size = window_short // 3
        last_month = returns[-month_size:]
        if len(last_month) > 1:
            sharpe_last = np.mean(last_month) / np.std(last_month) * np.sqrt(252 / month_size)
        else:
            sharpe_last = 0

        # 归一化
        score = min(1.0, ratio / 2.0 + sharpe_last / 2.0)

        return score

    def _get_label(self, score: float) -> str:
        """根据分数返回标签"""
        if score >= 75:
            return "STRONG BUY"
        elif score >= 55:
            return "BUY"
        elif score >= 35:
            return "HOLD"
        else:
            return "AVOID"


def main():
    """测试"""
    calculator = PnlScoringCalculator()

    # 模拟PnL数据
    np.random.seed(42)
    pnl = np.random.randn(600) * 0.01 + 0.0005  # 平均日收益0.05%

    result = calculator.calculate("test_alpha", pnl.tolist())

    print(f"Alpha: {result.alpha_id}")
    print(f"D1 (K-Ratio): {result.d1:.3f}")
    print(f"D2 (趋势): {result.d2:.3f}")
    print(f"D3 (Hurst): {result.d3:.3f}")
    print(f"D4 (健康度): {result.d4:.3f}")
    print(f"总分: {result.total_score:.1f}")
    print(f"标签: {result.label}")


if __name__ == "__main__":
    main()
