#!/usr/bin/env python3
"""
Alpha Mining Entry Point - 统一挖掘入口

用法:
    python mine.py --datasets pv87 mdl136 --max-combos 300
    python mine.py --datasets pv87 --max-combos 100
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.alpha_mining_engine import AlphaMiningEngine, DEFAULT_TEMPLATES
from scripts.core.logging_config import setup_logging, setup_global_exception_handler

logger = setup_logging('mine')
setup_global_exception_handler(logger)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Alpha Mining Engine - 统一挖掘入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python mine.py --datasets pv87 mdl136 --max-combos 300
  python mine.py --datasets pv87 --max-combos 100 --output results.json
        """
    )

    parser.add_argument(
        '--datasets',
        nargs='+',
        default=['pv87'],
        help='数据集列表 (默认: pv87)'
    )

    parser.add_argument(
        '--max-combos',
        type=int,
        default=100,
        help='最大组合数 (默认: 100)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='mining_results.json',
        help='输出文件路径 (默认: mining_results.json)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='配置文件路径'
    )

    return parser.parse_args()


async def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Alpha Mining Engine")
    logger.info("=" * 60)
    logger.info(f"数据集: {args.datasets}")
    logger.info(f"最大组合: {args.max_combos}")
    logger.info(f"输出: {args.output}")

    # 加载凭证
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config_path = Path(__file__).parent.parent / 'config' / 'user_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            logger.error(f"配置文件不存在: {config_path}")
            return

    credentials = config.get('credentials', {})

    # 创建引擎
    engine = AlphaMiningEngine(credentials=credentials)

    # 认证
    logger.info("\n[1/3] 认证中...")
    try:
        await engine.authenticate()
        logger.info("✅ 认证成功!")
    except Exception as e:
        logger.error(f"❌ 认证失败: {e}")
        return

    # 挖掘
    logger.info("\n[2/3] 挖掘中...")
    try:
        results = await engine.mine(
            datasets=args.datasets,
            max_combinations=args.max_combos
        )
        logger.info(f"✅ 挖掘完成! 测试了 {len(results)} 个组合")
    except Exception as e:
        logger.error(f"❌ 挖掘失败: {e}")
        return

    # 保存结果
    logger.info("\n[3/3] 保存结果...")
    engine.save_results(args.output)
    engine.print_summary()


if __name__ == "__main__":
    asyncio.run(main())