#!/usr/bin/env python3
"""表达式自动修复 — 降低40% token和API浪费

基于论坛文章: 一键降低40%的token使用量——自动修复alpha表达式
在回测前自动修复AI生成的常见表达式错误。
"""

import ast
import re
from pathlib import Path
from typing import Dict, List

OPERATORS_PATH = Path(__file__).parent.parent / "data" / "operators.md"


def split_def_args(s: str) -> List[str]:
    """智能参数拆分 — 处理中英文引号、嵌套括号"""
    args, curr, depth, in_str, quote = [], [], 0, False, ''
    for c in s:
        if in_str:
            curr.append(c)
            if (quote in "\"'" and c == quote) or \
               (quote == '"' and c == '"') or \
               (quote == "'" and c == "'"):
                in_str = False
        else:
            if c in "\"'":
                in_str, quote = True, c
                curr.append(c)
            elif c in '([{':
                depth += 1
                curr.append(c)
            elif c in ')]}':
                depth -= 1
                curr.append(c)
            elif c == ',' and depth == 0:
                args.append(''.join(curr).strip())
                curr = []
            else:
                curr.append(c)
    if curr:
        args.append(''.join(curr).strip())
    return args


def parse_operator_definitions(file_path: str) -> Dict:
    """解析 operators.md 获取算子定义"""
    func_specs = {}
    func_pattern = re.compile(r'\*\*([a-zA-Z_]\w*)\((.*?)\)\*\*')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for match in func_pattern.finditer(content):
        func_name = match.group(1)
        params_str = match.group(2).strip()

        positional: List[str] = []
        keyword: List[str] = []
        defaults: Dict[str, str] = {}

        if params_str:
            params = split_def_args(params_str)
            for param in params:
                if '=' in param:
                    kw_name, kw_val = param.split('=', 1)
                    kw_name = kw_name.strip()
                    keyword.append(kw_name)
                    defaults[kw_name] = kw_val.strip()
                else:
                    positional.append(param)

        func_specs[func_name] = {
            "positional": positional,
            "keyword": keyword,
            "defaults": defaults,
            "all_args": set(positional + keyword)
        }
    return func_specs


def correct_expression(expr: str, func_specs: Dict,
                       fill_defaults: bool = True) -> str:
    """修正表达式中的函数调用

    Args:
        expr: 原始表达式
        func_specs: 算子定义字典
        fill_defaults: 是否自动补全缺失的默认参数
    """
    # 1. 前置语法校验
    try:
        ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"语法错误: {e}")

    # 2. 等价参数组 (不同AI可能犯不同错)
    alias_groups = [
        {"d", "d1", "day", "days", "lookback", "window", "time"},
        {"p", "power", "y", "exp", "exponent", "a"},
        {"factor", "hump"},
        {"rettype", "ret"},
        {"target_tvr", "target"},
    ]

    # 3. 函数别名映射
    func_alias_map = {
        "ts_decay_exponential": "ts_decay_exp_window",
        "ts_moving_average": "ts_mean",
        "ts_avg": "ts_mean",
        "ts_decay_exp": "ts_decay_exp_window",
        "decay_linear": "ts_decay_linear",
        "moving_average": "ts_mean",
        "standard_deviation": "ts_std_dev",
        "ts_correlation": "ts_corr",
    }

    # 4. 智能参数拆分
    def split_args(s):
        args, curr, depth, in_str, quote = [], [], 0, False, ''
        for c in s:
            if in_str:
                curr.append(c)
                if c == quote:
                    in_str = False
            else:
                if c in "\"'":
                    in_str, quote = True, c
                    curr.append(c)
                elif c in '([{':
                    depth += 1
                    curr.append(c)
                elif c in ')]}':
                    depth -= 1
                    curr.append(c)
                elif c == ',' and depth == 0:
                    args.append(''.join(curr).strip())
                    curr = []
                else:
                    curr.append(c)
        if curr:
            args.append(''.join(curr).strip())
        return args

    # 5. 提取函数调用
    def get_calls(s):
        calls = []
        for m in re.finditer(r'\b([a-zA-Z_]\w*)\s*\(', s):
            func_name = m.group(1)
            start = m.end()
            depth = 1
            in_str = False
            quote = ''
            for i in range(start, len(s)):
                c = s[i]
                if in_str:
                    if c == quote and s[i - 1] != '\\':
                        in_str = False
                else:
                    if c in "\"'":
                        in_str, quote = True, c
                    elif c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                        if depth == 0:
                            calls.append((func_name, s[start:i], m.start(), i + 1))
                            break
        return calls

    # 6. 核心递归处理
    def process(s: str) -> str:
        calls = get_calls(s)
        outermost = []
        for c in calls:
            func_name, args_str, start, end = c
            is_inner = any(
                other_start < start and other_end > end
                for _, _, other_start, other_end in calls
            )
            if not is_inner:
                outermost.append(c)

        if not outermost:
            return s

        res = s
        for func_name, args_str, start, end in reversed(outermost):
            # 处理嵌套参数
            processed_args = []
            raw_args = split_args(args_str)
            for arg in raw_args:
                processed_args.append(process(arg))

            # 跳过非算子函数 (如字段名、内置函数)
            if func_name in ('int', 'float', 'str', 'len', 'max', 'min',
                             'round', 'abs', 'sum', 'type', 'isinstance',
                             'True', 'False', 'None', 'range', 'list',
                             'dict', 'set', 'tuple', 'print', 'input'):
                continue

            # 检查是否需要别名替换
            mapped_func = func_alias_map.get(func_name, func_name)

            # 如果是字段名或自定义变量，不是算子函数
            if mapped_func not in func_specs:
                continue  # 不做修改，保留原样

            spec = func_specs[mapped_func]
            pos_params = spec["positional"]
            kw_order = spec["keyword"]
            all_valid = spec.get("all_args", set(pos_params + kw_order))
            req_pos = len(pos_params)

            # 分离位置参数和关键字参数
            raw_pos = []
            raw_kw = {}
            for arg in processed_args:
                m = re.match(r'^([a-zA-Z_]\w*)\s*=\s*(.+)', arg)
                if m:
                    raw_kw[m.group(1)] = m.group(2)
                else:
                    raw_pos.append(arg)

            # 填充位置参数
            pos_slots = [None] * max(req_pos, len(raw_pos))
            for i, val in enumerate(raw_pos):
                pos_slots[i] = val

            # 解析关键字参数 (含别名处理)
            resolved_kw = {}
            for k, v in raw_kw.items():
                actual = k
                if actual not in all_valid:
                    for group in alias_groups:
                        if actual in group:
                            matches = group.intersection(all_valid)
                            if matches:
                                actual = list(matches)[0]
                                break
                if actual not in all_valid:
                    raise ValueError(
                        f"函数 {mapped_func} 未定义关键字参数 {k}")
                if actual in pos_params:
                    idx = pos_params.index(actual)
                    while len(pos_slots) <= idx:
                        pos_slots.append(None)
                    if pos_slots[idx] is not None:
                        raise ValueError(
                            f"函数 {mapped_func} 收到重复参数: {k}")
                    pos_slots[idx] = v
                else:
                    if actual in resolved_kw:
                        raise ValueError(
                            f"函数 {mapped_func} 收到重复关键字参数: {k}")
                    resolved_kw[actual] = v

            # 验证必选位置参数
            for i in range(req_pos):
                if pos_slots[i] is None:
                    raise ValueError(
                        f"函数 {mapped_func} 缺失必选位置参数 "
                        f"'{pos_params[i]}'")

            # 构建修复后的参数列表
            fixed_args = pos_slots[:req_pos]
            extra_args = [x for x in pos_slots[req_pos:] if x is not None]
            final_kw = []
            extra_idx = 0

            for kw_name in kw_order:
                if kw_name in resolved_kw:
                    final_kw.append(f"{kw_name}={resolved_kw[kw_name]}")
                elif extra_idx < len(extra_args):
                    final_kw.append(f"{kw_name}={extra_args[extra_idx]}")
                    extra_idx += 1
                else:
                    if fill_defaults and kw_name in spec["defaults"]:
                        default_val = spec["defaults"][kw_name]
                        final_kw.append(f"{kw_name}={default_val}")

            if extra_idx < len(extra_args):
                raise ValueError(f"函数 {mapped_func} 传入多余参数")

            new_call = f"{mapped_func}({', '.join(fixed_args + final_kw)})"
            res = res[:start] + new_call + res[end:]

        return res

    return process(expr)


# ─── 便捷接口 ───

class ExpressionFixer:
    """表达式自动修复器"""

    def __init__(self, operators_path: str = None):
        path = operators_path or str(OPERATORS_PATH)
        self.specs = parse_operator_definitions(path)
        self.fix_count = 0
        self.error_count = 0

    def fix(self, expr: str, fill_defaults: bool = False) -> str:
        """修复表达式, 返回修复后的表达式"""
        try:
            fixed = correct_expression(expr, self.specs, fill_defaults)
            if fixed != expr:
                self.fix_count += 1
            return fixed
        except Exception:
            self.error_count += 1
            return expr  # 无法修复则返回原文

    def fix_batch(self, expressions: list) -> list:
        """批量修复"""
        results = []
        for expr in expressions:
            results.append(self.fix(expr))
        return results


# 全局实例
fixer = ExpressionFixer()


# ─── 测试 ───

if __name__ == "__main__":
    specs = parse_operator_definitions(str(OPERATORS_PATH))
    print(f"已加载 {len(specs)} 个算子定义\n")

    tests = [
        # 关键字→位置参数
        ("signed_power(data, power=2)",
         "signed_power(data, 2)", "关键字→位置"),
        # 函数名纠正
        ("ts_moving_average(close, 60)",
         "ts_mean(close, 60)", "函数名纠正"),
        # 参数别名
        ("ts_mean(close, day=20)",
         "ts_mean(close, 20)", "参数别名 day→d"),
        # 默认值填充
        ("ts_decay_exp_window(returns, 60)",
         "ts_decay_exp_window(returns, 60, factor=1.0)", "默认值填充"),
        # 不影响已有表达式
        ("rank(ts_mean(close, 20))",
         "rank(ts_mean(close, 20))", "无变化"),
    ]

    passed = 0
    for expr, expected, desc in tests:
        try:
            result = correct_expression(expr, specs, fill_defaults=True)
            ok = result.strip() == expected.strip()
            print(f'  {"✅" if ok else "❌"} {desc}')
            if not ok:
                print(f'     期望: {expected}')
                print(f'     实际: {result}')
            passed += ok
        except Exception as e:
            print(f'  ❌ {desc}: {e}')

    print(f"\n通过: {passed}/{len(tests)}")
