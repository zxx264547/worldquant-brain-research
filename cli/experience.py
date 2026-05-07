#!/usr/bin/env python3
"""
经验管理CLI - wq-experience
用法:
  记录: wq-experience --record --problem fitness_low --action group_rank --result success
  检索: wq-experience --search --problem fitness_low
  统计: wq-experience --stats
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 经验存储路径
EXPERIENCE_FILE = Path("/tmp/multi_agent/experiences.json")


def load_experiences() -> Dict:
    """加载经验数据"""
    if EXPERIENCE_FILE.exists():
        with open(EXPERIENCE_FILE) as f:
            return json.load(f)
    return {"experiences": [], "metadata": {"created": datetime.now().isoformat()}}


def save_experiences(data: Dict):
    """保存经验数据"""
    EXPERIENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPERIENCE_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_experience(
    problem_type: str,
    fitness: Optional[float] = None,
    turnover: Optional[float] = None,
    sharpe: Optional[float] = None,
    expression: str = "",
    action_type: str = "",
    action_details: str = "",
    sharpe_before: Optional[float] = None,
    sharpe_after: Optional[float] = None,
    fitness_before: Optional[float] = None,
    fitness_after: Optional[float] = None,
    turnover_before: Optional[float] = None,
    turnover_after: Optional[float] = None,
    success: bool = False,
    notes: str = ""
) -> str:
    """记录一条经验"""
    data = load_experiences()

    experience = {
        "id": f"exp_{len(data['experiences']) + 1:04d}",
        "timestamp": datetime.now().isoformat(),
        "problem": {
            "type": problem_type,
            "fitness": fitness,
            "turnover": turnover,
            "sharpe": sharpe,
            "expression": expression
        },
        "action": {
            "type": action_type,
            "details": action_details
        },
        "result": {
            "sharpe_before": sharpe_before,
            "sharpe_after": sharpe_after,
            "fitness_before": fitness_before,
            "fitness_after": fitness_after,
            "turnover_before": turnover_before,
            "turnover_after": turnover_after,
            "success": success,
            "notes": notes
        }
    }

    data["experiences"].append(experience)
    save_experiences(data)

    return experience["id"]


def search_experiences(
    problem_type: Optional[str] = None,
    fitness_max: Optional[float] = None,
    fitness_min: Optional[float] = None,
    turnover_max: Optional[float] = None,
    turnover_min: Optional[float] = None,
    sharpe_min: Optional[float] = None,
    success_only: bool = False,
    limit: int = 5
) -> List[Dict]:
    """检索类似经验"""
    data = load_experiences()
    results = []

    for exp in data["experiences"]:
        if not exp:
            continue

        problem = exp.get("problem", {})
        result = exp.get("result", {})

        # 筛选条件
        if problem_type and problem.get("type") != problem_type:
            continue

        if success_only and not result.get("success"):
            continue

        if fitness_max is not None:
            f = problem.get("fitness")
            if f is None or f > fitness_max:
                continue

        if fitness_min is not None:
            f = problem.get("fitness")
            if f is None or f < fitness_min:
                continue

        if turnover_max is not None:
            t = problem.get("turnover")
            if t is None or t > turnover_max:
                continue

        if turnover_min is not None:
            t = problem.get("turnover")
            if t is None or t < turnover_min:
                continue

        if sharpe_min is not None:
            s = problem.get("sharpe")
            if s is None or s < sharpe_min:
                continue

        results.append(exp)

    # 按时间倒序，限制数量
    results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

    return results


def get_stats() -> Dict:
    """获取统计信息"""
    data = load_experiences()
    experiences = data.get("experiences", [])

    if not experiences:
        return {"total": 0, "success_rate": 0, "by_problem_type": {}}

    # 计算成功率
    success_count = sum(1 for e in experiences if e.get("result", {}).get("success"))
    success_rate = success_count / len(experiences) * 100

    # 按问题类型统计
    by_type = {}
    for e in experiences:
        ptype = e.get("problem", {}).get("type", "unknown")
        if ptype not in by_type:
            by_type[ptype] = {"total": 0, "success": 0}
        by_type[ptype]["total"] += 1
        if e.get("result", {}).get("success"):
            by_type[ptype]["success"] += 1

    # 计算各类型的成功率
    for ptype, stats in by_type.items():
        stats["success_rate"] = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0

    # 按动作类型统计
    by_action = {}
    for e in experiences:
        atype = e.get("action", {}).get("type", "unknown")
        if atype not in by_action:
            by_action[atype] = {"total": 0, "success": 0}
        by_action[atype]["total"] += 1
        if e.get("result", {}).get("success"):
            by_action[atype]["success"] += 1

    for atype, stats in by_action.items():
        stats["success_rate"] = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0

    return {
        "total": len(experiences),
        "success_count": success_count,
        "success_rate": round(success_rate, 1),
        "by_problem_type": by_type,
        "by_action_type": by_action
    }


def main():
    parser = argparse.ArgumentParser(description="经验管理CLI")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 记录命令
    record_parser = subparsers.add_parser("record", help="记录经验")
    record_parser.add_argument("--problem", required=True, help="问题类型")
    record_parser.add_argument("--fitness", type=float, help="Fitness值")
    record_parser.add_argument("--turnover", type=float, help="Turnover值")
    record_parser.add_argument("--sharpe", type=float, help="Sharpe值")
    record_parser.add_argument("--expression", default="", help="表达式")
    record_parser.add_argument("--action-type", default="", help="动作类型")
    record_parser.add_argument("--action-details", default="", help="动作详情")
    record_parser.add_argument("--sharpe-before", type=float)
    record_parser.add_argument("--sharpe-after", type=float)
    record_parser.add_argument("--fitness-before", type=float)
    record_parser.add_argument("--fitness-after", type=float)
    record_parser.add_argument("--turnover-before", type=float)
    record_parser.add_argument("--turnover-after", type=float)
    record_parser.add_argument("--success", action="store_true", help="是否成功")
    record_parser.add_argument("--notes", default="", help="备注")

    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索经验")
    search_parser.add_argument("--problem", help="问题类型")
    search_parser.add_argument("--fitness-max", type=float, help="Fitness最大值")
    search_parser.add_argument("--fitness-min", type=float, help="Fitness最小值")
    search_parser.add_argument("--turnover-max", type=float, help="Turnover最大值")
    search_parser.add_argument("--turnover-min", type=float, help="Turnover最小值")
    search_parser.add_argument("--success-only", action="store_true", help="只显示成功的")
    search_parser.add_argument("--limit", type=int, default=5, help="返回数量")

    # 统计命令
    subparsers.add_parser("stats", help="统计信息")

    args = parser.parse_args()

    if args.command == "record":
        exp_id = record_experience(
            problem_type=args.problem,
            fitness=args.fitness,
            turnover=args.turnover,
            sharpe=args.sharpe,
            expression=args.expression,
            action_type=args.action_type,
            action_details=args.action_details,
            sharpe_before=args.sharpe_before,
            sharpe_after=args.sharpe_after,
            fitness_before=args.fitness_before,
            fitness_after=args.fitness_after,
            turnover_before=args.turnover_before,
            turnover_after=args.turnover_after,
            success=args.success,
            notes=args.notes
        )
        print(f"✓ 经验已记录: {exp_id}")

    elif args.command == "search":
        results = search_experiences(
            problem_type=args.problem,
            fitness_max=args.fitness_max,
            fitness_min=args.fitness_min,
            turnover_max=args.turnover_max,
            turnover_min=args.turnover_min,
            success_only=args.success_only,
            limit=args.limit
        )
        if results:
            print(f"找到 {len(results)} 条相关经验:\n")
            for exp in results:
                problem = exp.get("problem", {})
                action = exp.get("action", {})
                result = exp.get("result", {})
                print(f"ID: {exp.get('id')}")
                print(f"  问题: {problem.get('type')} | fitness={problem.get('fitness')} | turnover={problem.get('turnover')}")
                print(f"  动作: {action.get('type')} - {action.get('details')}")
                print(f"  结果: {'✅ 成功' if result.get('success') else '❌ 失败'} | Sharpe {result.get('sharpe_before')} → {result.get('sharpe_after')}")
                print(f"  时间: {exp.get('timestamp')}")
                print()
        else:
            print("未找到相关经验")

    elif args.command == "stats":
        stats = get_stats()
        print(f"总经验数: {stats['total']}")
        print(f"总成功率: {stats['success_rate']}%\n")
        print("按问题类型:")
        for ptype, s in stats.get("by_problem_type", {}).items():
            print(f"  {ptype}: {s['total']}条, 成功率{s['success_rate']}%")
        print("\n按动作类型:")
        for atype, s in stats.get("by_action_type", {}).items():
            print(f"  {atype}: {s['total']}条, 成功率{s['success_rate']}%")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()