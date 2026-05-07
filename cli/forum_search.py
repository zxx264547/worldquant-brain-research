#!/usr/bin/env python3
"""
论坛搜索CLI - wq-forum-search
用法: wq-forum-search "搜索关键词" [--max 5] [--locale zh-cn]
"""

import sys
import os
import json
import asyncio
import argparse
from pathlib import Path

# 添加cnhkmcp路径
FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from forum_functions import ForumClient


async def search_forum(query: str, max_results: int = 5, locale: str = "zh-cn") -> dict:
    """搜索论坛"""
    # 加载凭据
    config_path = Path("/home/zxx/worldQuant/worldquant_brain/config/user_config.json")
    credentials = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            # 支持顶层或credentials嵌套
            if 'credentials' in config:
                credentials = config.get('credentials', {})
            else:
                credentials = {
                    'email': config.get('email', ''),
                    'password': config.get('password', '')
                }

    if not credentials.get('email'):
        return {"success": False, "error": "未配置email/password"}

    forum = ForumClient()

    try:
        results = await forum.search_forum_posts(
            email=credentials['email'],
            password=credentials['password'],
            search_query=query,
            max_results=max_results,
            locale=locale
        )
        return results
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="搜索WorldQuant论坛")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--max", type=int, default=5, help="最大结果数")
    parser.add_argument("--locale", default="zh-cn", help="语言 zh-cn 或 en-us")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    results = asyncio.run(search_forum(args.query, args.max, args.locale))

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        if results.get("success"):
            print(f"找到 {results.get('total_found', 0)} 条结果:\n")
            for i, r in enumerate(results.get("results", []), 1):
                print(f"{i}. {r.get('title', 'N/A')}")
                print(f"   投票: {r.get('votes', 0)} | 作者: {r.get('author', 'N/A')}")
                print(f"   摘要: {r.get('snippet', 'N/A')[:100]}...")
                print(f"   链接: {r.get('link', 'N/A')}\n")
        else:
            print(f"搜索失败: {results.get('error', '未知错误')}")


if __name__ == "__main__":
    main()