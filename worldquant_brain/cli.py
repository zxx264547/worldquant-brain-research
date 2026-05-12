#!/usr/bin/env python3
"""WorldQuant BRAIN 统一CLI"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def _import_engine():
    """延迟导入引擎模块（需要外部依赖）"""
    from worldquant_brain.engine import (ExpressionBuilder, ExpressionTemplates,
                                          BacktestRunner, get_settings, store)
    from worldquant_brain.strategies import ALL_STRATEGIES, get_strategy
    from worldquant_brain.scheduler import Orchestrator
    return locals()


# ─── CLI框架 (不依赖click, 使用argparse) ───

def cmd_mine(args):
    """运行Alpha挖掘"""
    eng = _import_engine()
    strategy_names = args.strategy or ['combination']
    workers = args.workers or 3

    async def _run():
        orch = eng['Orchestrator'](strategy_names, workers)
        await orch.run()

    asyncio.run(_run())


def cmd_test(args):
    """测试单个表达式"""
    eng = _import_engine()
    expression = args.expression
    name = args.name or "test"

    async def _run():
        runner = eng['BacktestRunner']()
        result = await runner.run(expression, name=name)
        if result.get('status') == 'ok':
            print(f"Sharpe: {result['sharpe']:.3f}")
            print(f"Fitness: {result['fitness']:.3f}")
            print(f"Turnover: {result['turnover']:.4f}")
            print(f"Margin: {result['margin']:.4f}")
            print(f"PPC: {result['ppc']:.4f}")
            if result.get('is_submittable'):
                print("*** 可提交! ***")
        else:
            print(f"Error: {result.get('error', 'Unknown')}")

    asyncio.run(_run())


def cmd_check(args):
    """检查Alpha是否可提交"""
    alpha_id = args.alpha_id

    async def _run():
        from worldquant_brain.scripts.core import RetryableBrainClient
        client = RetryableBrainClient()
        await client.authenticate_with_retry()
        alpha = await client.get_alpha_with_retry(alpha_id)

        sharpe = alpha.get('sharpe', 0)
        fitness = alpha.get('fitness', 0)
        ppc = alpha.get('ppc', 0)
        margin = alpha.get('margin', 0)
        turnover = alpha.get('turnover', 0)

        checks = {
            'Sharpe >= 1.58': sharpe >= 1.58,
            'Fitness > 0.5': fitness > 0.5,
            'PPC < 0.5': ppc < 0.5,
            'Margin > Turnover': margin > turnover,
        }

        for check, passed in checks.items():
            print(f"  {'✓' if passed else '✗'} {check}")

        if all(checks.values()):
            print("\n*** Alpha满足提交条件! ***")
        else:
            print("\nAlpha不满足提交条件")

    asyncio.run(_run())


def cmd_best(args):
    """查看最佳Alpha"""
    eng = _import_engine()
    limit = args.limit or 10
    for a in eng['store'].best(limit):
        print(f"  {a['name'][:50]:50s} Sharpe={a['sharpe']:.3f} "
              f"Fitness={a['fitness']:.3f} alpha_id={a['id']}")


def cmd_submittable(args):
    """查看可提交Alpha"""
    eng = _import_engine()
    subs = eng['store'].submittable()
    if not subs:
        print("没有可提交的Alpha")
        return
    for a in subs:
        print(f"  {a['alpha_id']}: Sharpe={a['sharpe']:.3f} "
              f"Name={a['name'][:40]}")


def cmd_ideas(args):
    """查看待处理的Ideas (Agent用)"""
    from worldquant_brain.engine.agent_adapter import load_ideas
    ideas = load_ideas(args.limit or 8)
    if not ideas:
        print("暂无待处理Idea")
    for i, idea in enumerate(ideas):
        expr = idea.get('expression', '')[:60]
        print(f"  [{i}] {idea.get('idea_id','?')} | {expr}")


def cmd_backtest(args):
    """执行单次回测 (Agent用)"""
    async def _run():
        from worldquant_brain.engine.agent_adapter import run_backtest
        result = await run_backtest(args.expression, None, args.name or 'cli')
        if result:
            print(f"  alpha_id={result.get('alpha_id','')}")
            print(f"  Sharpe={result.get('sharpe',0):.3f} "
                  f"Fitness={result.get('fitness',0):.3f}")
    asyncio.run(_run())


def cmd_knowledge(args):
    """搜索知识库 (Agent用)"""
    from worldquant_brain.engine.agent_adapter import search_knowledge
    results = search_knowledge(args.query)
    if not results:
        print("未找到相关知识")
    for r in results[:5]:
        if isinstance(r, dict):
            print(f"  [{r.get('slug','?')}] {r.get('title','')[:80]}")


def cmd_state(args):
    """查看系统状态 (Agent/TeamLead用)"""
    from worldquant_brain.engine.agent_adapter import load_state, get_stats
    state = load_state()
    stats = get_stats()
    print(f"总Alpha: {stats['total_alphas']}")
    print(f"最佳Sharpe: {stats['best']['sharpe']:.3f}" if stats['best'] else "无结果")
    print(f"Worker数: {len(state.get('workers',[]))}")
    print(f"时间: {state.get('timestamp','')}")


def cmd_memory(args):
    """保存记忆 (Agent用)"""
    note = args.save
    ts = datetime.now().isoformat()
    mem_file = Path("/tmp/multi_agent/memory.json")
    entries = []
    if mem_file.exists():
        entries = json.loads(mem_file.read_text())
    entries.append({"timestamp": ts, "note": note})
    mem_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"记忆已保存: {note[:60]}")


## ─── 认知循环命令 ───

def cmd_perceive(args):
    """感知当前全局状态（认知循环第1步）"""
    from worldquant_brain.cognitive_loop import cli_perceive
    cli_perceive()


def cmd_dispatch(args):
    """下发批量任务（认知循环第3步）"""
    from worldquant_brain.cognitive_loop import cli_dispatch
    cli_dispatch(args.plan)


def cmd_reflect(args):
    """分析批量结果（认知循环第4步）"""
    from worldquant_brain.cognitive_loop import cli_reflect
    cli_reflect(args.results_file)


def cmd_remember_insight(args):
    """记录发现到知识库（认知循环第5步）"""
    from worldquant_brain.cognitive_loop import cli_remember
    cli_remember(args.insight, args.confidence)


def cmd_evolve(args):
    """提议规则修改（认知循环第6步）"""
    from worldquant_brain.cognitive_loop import cli_evolve
    cli_evolve()


def cmd_clean(args):
    """清理数据库 (保留Top N)"""
    keep = args.keep or 200
    import sqlite3
    from worldquant_brain.db.repository import get_db_path, count_alphas

    before = count_alphas()
    conn = sqlite3.connect(get_db_path())
    conn.execute("""DELETE FROM alphas WHERE id NOT IN
        (SELECT id FROM alphas ORDER BY sharpe DESC LIMIT ?)""", (keep,))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    after = count_alphas()
    print(f"清理: {before} → {after} (保留Top {keep})")


# ─── 主CLI ───

def create_parser():
    import argparse
    parser = argparse.ArgumentParser(
        description='WorldQuant BRAIN Alpha Research CLI')
    sub = parser.add_subparsers(dest='command')

    # mine
    p = sub.add_parser('mine', help='运行Alpha挖掘')
    p.add_argument('--strategy', '-s', nargs='+')
    p.add_argument('--workers', '-w', type=int, default=3)
    p.set_defaults(func=cmd_mine)

    # test
    p = sub.add_parser('test', help='测试单个表达式')
    p.add_argument('expression', help='Alpha表达式')
    p.add_argument('--name', '-n', help='名称')
    p.set_defaults(func=cmd_test)

    # check
    p = sub.add_parser('check', help='检查Alpha')
    p.add_argument('alpha_id', help='Alpha ID')
    p.set_defaults(func=cmd_check)

    # best
    p = sub.add_parser('best', help='最佳Alpha')
    p.add_argument('--limit', '-l', type=int, default=10)
    p.set_defaults(func=cmd_best)

    # submittable
    p = sub.add_parser('submittable', help='可提交Alpha')
    p.set_defaults(func=cmd_submittable)

    # ideas (Agent用)
    p = sub.add_parser('ideas', help='查看待处理Idea')
    p.add_argument('--limit', '-l', type=int, default=8)
    p.set_defaults(func=cmd_ideas)

    # backtest (Agent用)
    p = sub.add_parser('backtest', help='执行单次回测')
    p.add_argument('expression', help='Alpha表达式')
    p.add_argument('--name', '-n', help='名称')
    p.set_defaults(func=cmd_backtest)

    # knowledge (Agent用)
    p = sub.add_parser('knowledge', help='搜索知识库')
    p.add_argument('query', help='搜索关键词')
    p.set_defaults(func=cmd_knowledge)

    # state (Agent用)
    p = sub.add_parser('state', help='系统状态')
    p.set_defaults(func=cmd_state)

    # memory (Agent用)
    p = sub.add_parser('memory', help='保存记忆')
    p.add_argument('--save', '-s', required=True, help='记忆内容')
    p.set_defaults(func=cmd_memory)

    # ─── 认知循环命令 ───

    # perceive
    p = sub.add_parser('perceive', help='感知全局状态（认知循环）')
    p.set_defaults(func=cmd_perceive)

    # dispatch
    p = sub.add_parser('dispatch', help='下发批量任务（认知循环）')
    p.add_argument('plan', help='JSON格式的执行计划')
    p.set_defaults(func=cmd_dispatch)

    # reflect
    p = sub.add_parser('reflect', help='分析批量结果（认知循环）')
    p.add_argument('results_file', help='结果JSON文件路径')
    p.set_defaults(func=cmd_reflect)

    # remember
    p = sub.add_parser('remember', help='记录发现到知识库（认知循环）')
    p.add_argument('insight', help='发现内容')
    p.add_argument('--confidence', '-c', type=float, default=0.6)
    p.set_defaults(func=cmd_remember_insight)

    # evolve
    p = sub.add_parser('evolve', help='提议规则修改（认知循环）')
    p.set_defaults(func=cmd_evolve)

    # clean
    p = sub.add_parser('clean', help='清理数据库')
    p.add_argument('--keep', '-k', type=int, default=200,
                   help='保留Top N条记录')
    p.set_defaults(func=cmd_clean)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
