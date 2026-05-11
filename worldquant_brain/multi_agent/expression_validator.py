#!/usr/bin/env python3
"""
Alpha表达式验证器
在提交回测前检查表达式有效性
"""

import re
from typing import List, Tuple, Optional

# 有效算子映射（已知可用的）
VALID_OPERATORS = {
    # 时间序列算子
    'ts_mean', 'ts_sum', 'ts_rank', 'ts_delta', 'ts_decay_linear',
    'ts_corr', 'ts_std_dev', 'ts_max', 'ts_min', 'ts_argmax', 'ts_argmin',
    'ts_skew', 'ts_kurt', 'ts_zscore', 'ts_scale',
    # 算子
    'rank', 'zscore', 'signed_power', 'abs', 'log', 'sign',
    'winsorize', 'delay', 'correlation',
    # 组合算子
    'ts_backfill', 'ts_av_diff', 'ts_percentile',
    # 布尔算子
    'greater_than', 'less_than', 'equal_to',
}

# 无效算子（常见错误）
INVALID_OPERATORS = {
    'ts_std': 'ts_std_dev',  # 正确写法
    'std': 'ts_std_dev',
    'std_dev': 'ts_std_dev',
    'decay_exponential': 'ts_decay_linear',
    'ema': 'ts_mean with decay',  # 没有独立的EMA算子
}

# 有效时间窗口
VALID_WINDOWS = {5, 22, 66, 120, 252, 504}

# EPS相关字段
EPS_FIELDS = {
    'actual_eps_value_quarterly',
    'actual_dividend_value_quarterly',
    'actual_cashflow_per_share_value_quarterly',
    'actual_sales_value_quarterly',
    'actual_revenue_value_quarterly',
}

# 常用有效字段
VALID_FIELDS = {
    # Price
    'close', 'open', 'high', 'low', 'vwap', 'volume', 'amount',
    'market_cap', 'price', 'returns',
    # EPS
    'actual_eps_value_quarterly', 'estimate_eps_quarterly',
    # Analyst
    'analyst4_afv4_eps_mean', 'analyst10_afv4_eps_mean',
    # Fundamenta
    'fundamental6_operating_earnings_per_share_quarterly',
    # AIAC
    'anl4_afv4_cfps_mean', 'anl4_afv4_ebitda_mean',
    'anl4_afv4_ebit_mean', 'anl4_afv4_ni_mean',
    'anl4_ady_mean', 'anl4_arq_mean',
    # VECTOR
    'pv87_2_bps_af_matrix_all_chngratio_mean',
    'pv87_2_eps_af_matrix_all_chngratio_mean',
}

# 已知的无效字段
INVALID_FIELDS = {
    'spx': 'use market indices through proper dataset',
    'vix': 'use anl4_ady_mean or similar',
    'market_return': 'use returns field',
    'interest_rate_10y': 'use proper rate fields in dataset',
    'fundamental6_operating_earnings_per_share_quarterly': 'field name too long, try shorter aliases',
    'model109_net_income_annual': 'check exact field name in dataset',
    'price_earnings_ratio': 'check dataset fields',
    'price_book_ratio': 'check dataset fields',
}


class ExpressionValidator:
    """Alpha表达式验证器"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate(self, expression: str) -> Tuple[bool, List[str], List[str]]:
        """
        验证表达式
        Returns: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        if not expression or not expression.strip():
            self.errors.append("Empty expression")
            return False, self.errors, self.warnings

        # 检查无效算子
        self._check_invalid_operators(expression)

        # 检查算子配对
        self._check_operator_pairing(expression)

        # 检查字段
        self._check_fields(expression)

        # 检查窗口参数
        self._check_windows(expression)

        # 检查括号配对
        self._check_parentheses(expression)

        return len(self.errors) == 0, self.errors, self.warnings

    def _check_invalid_operators(self, expr: str):
        """检查无效算子"""
        expr_lower = expr.lower()
        for invalid, suggestion in INVALID_OPERATORS.items():
            if invalid in expr_lower:
                self.errors.append(
                    f"Invalid operator '{invalid}'. Did you mean '{suggestion}'?"
                )

    def _check_operator_pairing(self, expr: str):
        """检查算子配对"""
        # 常见的需要配对的算子
        pairing_rules = [
            (r'ts_mean\s*\(', r'ts_mean\([^)]+\)'),  # ts_mean需要配对
            (r'ts_sum\s*\(', r'ts_sum\([^)]+\)'),
            (r'ts_rank\s*\(', r'ts_rank\([^)]+\)'),
            (r'ts_delta\s*\(', r'ts_delta\([^)]+,\s*\d+\)'),
            (r'signed_power\s*\(', r'signed_power\([^,]+,\s*[\d.]+\)'),
            (r'ts_backfill\s*\(', r'ts_backfill\([^,]+,\s*\d+\)'),
            (r'ts_corr\s*\(', r'ts_corr\([^,]+,\s*[^,]+,\s*\d+\)'),
            (r'rank\s*\(', r'rank\([^)]+\)'),
            (r'zscore\s*\(', r'zscore\([^)]+\)'),
        ]

        for pattern, replacement in pairing_rules:
            if re.search(pattern, expr) and not re.search(replacement, expr):
                self.warnings.append(f"Incomplete operator pattern: {pattern}")

    def _check_fields(self, expr: str):
        """检查字段"""
        # 提取可能的字段名
        # 字段通常是逗号分隔的最后一个参数或在括号内
        field_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)'

        # 检查已知无效字段
        expr_lower = expr.lower()
        for invalid_field, suggestion in INVALID_FIELDS.items():
            if invalid_field in expr_lower:
                self.errors.append(
                    f"Invalid field '{invalid_field}'. {suggestion}"
                )

    def _check_windows(self, expr: str):
        """检查时间窗口"""
        # 提取数字作为可能的窗口值
        numbers = re.findall(r',\s*(\d+)\s*\)', expr)
        for num in numbers:
            try:
                window = int(num)
                if window > 0 and window not in VALID_WINDOWS:
                    self.warnings.append(
                        f"Non-standard window value: {window}. "
                        f"Consider using: {VALID_WINDOWS}"
                    )
            except ValueError:
                pass

    def _check_parentheses(self, expr: str):
        """检查括号配对"""
        count = 0
        for char in expr:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            if count < 0:
                self.errors.append("Unmatched closing parenthesis")
                return

        if count > 0:
            self.errors.append(f"Missing {count} closing parenthesis(es)")
        elif count < 0:
            self.errors.append(f"Extra {abs(count)} closing parenthesis(es)")


def validate_expression(expression: str) -> Tuple[bool, List[str], List[str]]:
    """
    验证Alpha表达式的便捷函数

    Returns:
        (is_valid, errors, warnings)
    """
    validator = ExpressionValidator()
    return validator.validate(expression)


# 测试
if __name__ == "__main__":
    test_expressions = [
        "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)",  # 有效
        "ts_std(returns, 20)",  # 无效算子
        "ts_backfill(signed_power(ts_sum(actual_eps_value_quarterly, 252), 1.05), 3)",  # 有效
        "rank(ts_mean(close, 22))",  # 有效
        "ts_delta(close, 20",  # 括号不配对
        "rank(spx)",  # 无效字段
    ]

    print("Expression Validation Test")
    print("=" * 60)

    for expr in test_expressions:
        is_valid, errors, warnings = validate_expression(expr)
        print(f"\nExpression: {expr[:50]}...")
        print(f"  Valid: {is_valid}")
        if errors:
            print(f"  Errors: {errors}")
        if warnings:
            print(f"  Warnings: {warnings}")