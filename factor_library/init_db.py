#!/usr/bin/env python3
"""
初始化因子库数据库
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'factor_library.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def init_database():
    """初始化数据库"""
    print(f"初始化数据库: {DB_PATH}")

    # 读取schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()

    # 创建数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 执行schema
    cursor.executescript(schema)

    conn.commit()
    conn.close()

    print("数据库初始化完成")


def seed_sample_data():
    """添加示例数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 示例因子
    sample_factors = [
        {
            'alpha_id': 'demo_001',
            'name': '演示Alpha',
            'type': 'PPA',
            'expression': 'ts_rank(ts_max(pv87_2_af_return_high, 20), 60)',
            'region': 'USA',
            'sharpe': 1.25,
            'fitness': 0.65,
            'turnover': 0.12,
            'ppc': 0.35,
            'margin': 0.18,
            'status': 'testing',
            'tags': '["momentum", "pv87"]',
            'created_date': '2026-04-18'
        }
    ]

    for factor in sample_factors:
        cursor.execute('''
            INSERT INTO factors (
                alpha_id, name, type, expression, region,
                sharpe, fitness, turnover, ppc, margin,
                status, tags, created_date
            ) VALUES (
                :alpha_id, :name, :type, :expression, :region,
                :sharpe, :fitness, :turnover, :ppc, :margin,
                :status, :tags, :created_date
            )
        ''', factor)

    conn.commit()
    conn.close()

    print("示例数据添加完成")


def main():
    init_database()
    seed_sample_data()

    # 验证
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\n创建了 {len(tables)} 个表:")
    for table in tables:
        print(f"  - {table[0]}")

    cursor.execute("SELECT COUNT(*) FROM factors")
    count = cursor.fetchone()[0]
    print(f"\n因子表当前有 {count} 条记录")

    conn.close()


if __name__ == "__main__":
    main()
