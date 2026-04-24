#!/usr/bin/env python3
"""
Multi-Agent 系统初始化脚本
创建共享存储，初始化配置文件
"""

import json
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/tmp/multi_agent")
LOGS_DIR = BASE_DIR / "logs"
MEMORY_FILE = BASE_DIR / "memory.json"

# Multi-Agent项目目录
PROJECT_DIR = Path(__file__).parent


def init_shared_storage():
    """初始化共享存储"""
    BASE_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    # ideas.json
    with open(BASE_DIR / "ideas.json", 'w') as f:
        json.dump({"ideas": [], "last_updated": datetime.now().isoformat()}, f, indent=2)

    # results.json
    with open(BASE_DIR / "results.json", 'w') as f:
        json.dump({"results": [], "last_updated": datetime.now().isoformat()}, f, indent=2)

    # memory.json
    with open(MEMORY_FILE, 'w') as f:
        json.dump({"ideas": [], "last_updated": datetime.now().isoformat()}, f, indent=2)

    print(f"  ✓ 共享存储: {BASE_DIR}")
    print(f"    - ideas.json")
    print(f"    - results.json")
    print(f"    - memory.json")
    print(f"    - logs/")


def init_config():
    """初始化配置"""
    configs_dir = BASE_DIR / "configs"
    configs_dir.mkdir(exist_ok=True)

    # 从项目configs复制
    project_configs = PROJECT_DIR / "configs"
    if project_configs.exists():
        for f in project_configs.glob("*.json"):
            with open(f, 'r') as src:
                data = json.load(src)
            with open(configs_dir / f.name, 'w') as dst:
                json.dump(data, dst, indent=2, ensure_ascii=False)

    print(f"  ✓ 配置文件: {configs_dir}")


def init_skills():
    """初始化技能模块"""
    skills_dir = BASE_DIR / "skills"
    skills_dir.mkdir(exist_ok=True)

    project_skills = PROJECT_DIR / "skills"
    if project_skills.exists():
        for f in project_skills.glob("*.json"):
            with open(f, 'r') as src:
                data = json.load(src)
            with open(skills_dir / f.name, 'w') as dst:
                json.dump(data, dst, indent=2, ensure_ascii=False)

    print(f"  ✓ 技能模块: {skills_dir}")


def init_system():
    """初始化Multi-Agent系统"""
    print("=" * 60)
    print("Multi-Agent Alpha科研系统初始化")
    print("=" * 60)
    print()

    print("[1/3] 初始化共享存储...")
    init_shared_storage()

    print("[2/3] 初始化配置文件...")
    init_config()

    print("[3/3] 初始化技能模块...")
    init_skills()

    print()
    print("=" * 60)
    print("初始化完成!")
    print("=" * 60)
    print()
    print("下一步:")
    print("1. 使用 /agent 命令确认Agents已创建")
    print("2. 通过SendMessage与Agents协调")


if __name__ == "__main__":
    init_system()
