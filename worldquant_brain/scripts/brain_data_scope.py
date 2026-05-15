#!/usr/bin/env python3
"""
brain-data-scope — 离线数据分析工具
根据论坛帖子#40091088861591 华子哥插件数据分析模块的思路实现

四个核心功能：
1. available_star — 检查 dataset+region+universe+delay 组合是否存在
2. osis_badge — OS/IS Sharpe 比率与颜色徽章
3. neutralization_popup — 中性化桶分布分析
4. field_report — 单字段覆盖率/信号质量报告
"""

import json, sqlite3, os
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "data" / "field_analysis.db"


def init_db():
    """初始化本地分析数据库"""
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""CREATE TABLE IF NOT EXISTS field_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset TEXT, field TEXT, region TEXT, universe TEXT, delay INTEGER,
        coverage REAL, pos_ratio REAL, neg_ratio REAL,
        best_sharpe REAL, best_expression TEXT,
        best_neutralization TEXT, best_truncation REAL,
        tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(dataset, field, region, universe, delay)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS dataset_combos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset TEXT, region TEXT, universe TEXT, delay INTEGER,
        total_fields INTEGER, avg_sharpe REAL, max_sharpe REAL,
        best_field TEXT, best_neut TEXT
    )""")
    db.commit()
    return db


def available_star(db: sqlite3.Connection, dataset: str, region: str = "USA",
                   universe: str = "TOP3000", delay: int = 1) -> str:
    """检查 dataset+region+universe+delay 组合是否存在并返回星级"""
    rows = db.execute(
        "SELECT COUNT(*) FROM field_reports WHERE dataset=? AND region=? AND universe=? AND delay=?",
        (dataset, region, universe, delay)
    ).fetchone()
    count = rows[0]

    max_sharpe = db.execute(
        "SELECT MAX(best_sharpe) FROM field_reports WHERE dataset=? AND region=? AND universe=? AND delay=?",
        (dataset, region, universe, delay)
    ).fetchone()[0] or 0

    if count > 10 and max_sharpe >= 2.0:
        return "★★★"
    elif count > 5 and max_sharpe >= 1.5:
        return "★★"
    elif count > 0:
        return "★"
    else:
        return "☆ (未测试)"


def osis_badge(db: sqlite3.Connection, dataset: str, region: str = "USA",
               delay: int = 1) -> dict:
    """计算 OS/IS Sharpe 比率与颜色徽章"""
    rows = db.execute(
        "SELECT field, AVG(best_sharpe) as avg_s, MAX(best_sharpe) as max_s, COUNT(*) as cnt "
        "FROM field_reports WHERE dataset=? AND region=? AND delay=? AND best_sharpe > 0 "
        "GROUP BY field", (dataset, region, delay)
    ).fetchall()

    if not rows:
        return {"badge": "⚫", "color": "#9CA3AF", "reason": "无数据"}

    all_sharpes = [r[1] for r in rows]
    mean_sharpe = sum(all_sharpes) / len(all_sharpes)
    best_field = max(rows, key=lambda r: r[2])

    # 与全局均值对比
    global_avg = db.execute("SELECT AVG(best_sharpe) FROM field_reports WHERE best_sharpe > 0").fetchone()[0] or 1.0

    ratio = best_field[2] / global_avg if global_avg > 0 else 0

    if ratio >= 1.3:
        badge, color = "🟢", "#34D399"
    elif ratio >= 0.8:
        badge, color = "🟡", "#FBBF24"
    else:
        badge, color = "🔴", "#F87171"

    return {
        "badge": badge,
        "color": color,
        "best_sharpe": best_field[2],
        "best_field": best_field[0],
        "mean_sharpe": round(mean_sharpe, 3),
        "global_mean": round(global_avg, 3),
        "ratio": round(ratio, 3),
        "field_count": len(rows),
        "data_date": "2026-05-15"
    }


def neutralization_popup(db: sqlite3.Connection, field: str, dataset: str = None,
                         region: str = "USA") -> dict:
    """分析不同中性化方式对该字段的效果分布"""
    conditions = ["1=1"]
    params = []
    if dataset:
        conditions.append("dataset=?")
        params.append(dataset)

    # 简化版：基于已有数据中不同中性化设置的效果
    rows = db.execute(
        f"SELECT best_neutralization, COUNT(*) as cnt, AVG(best_sharpe) as avg_s, MAX(best_sharpe) as max_s "
        f"FROM field_reports WHERE field=? AND region=? AND {' AND '.join(conditions)} "
        f"GROUP BY best_neutralization ORDER BY avg_s DESC",
        [field, region] + params
    ).fetchall()

    if not rows:
        return {"recommendation": "无数据", "buckets": []}

    total = sum(r[1] for r in rows)
    buckets = []
    for neut, cnt, avg_s, max_s in rows:
        buckets.append({
            "neutralization": neut or "NONE",
            "count": cnt,
            "percentage": round(cnt / total * 100, 1),
            "avg_sharpe": round(avg_s, 3) if avg_s else 0,
            "max_sharpe": round(max_s, 3) if max_s else 0
        })

    return {
        "field": field,
        "best_neutralization": buckets[0]["neutralization"] if buckets else "NONE",
        "total_samples": total,
        "buckets": buckets[:8]
    }


def field_report(db: sqlite3.Connection, field: str, dataset: str = None,
                 region: str = "USA", universe: str = "TOP3000") -> dict:
    """生成单个字段的综合报告"""
    conditions = ["field=? AND region=? AND universe=?"]
    params = [field, region, universe]
    if dataset:
        conditions.append("dataset=?")
        params.append(dataset)

    rows = db.execute(
        f"SELECT dataset, coverage, pos_ratio, neg_ratio, best_sharpe, best_expression, best_neutralization "
        f"FROM field_reports WHERE {' AND '.join(conditions)}",
        params
    ).fetchall()

    if not rows:
        return {
            "field": field,
            "status": "未测试",
            "recommendation": "需要回测验证"
        }

    best = max(rows, key=lambda r: r[4])
    all_sharpes = [r[4] for r in rows if r[4]]

    return {
        "field": field,
        "dataset": best[0],
        "coverage": round(best[1] * 100, 1) if best[1] else None,
        "pos_ratio": round(best[2] * 100, 1) if best[2] else None,
        "neg_ratio": round(best[3] * 100, 1) if best[3] else None,
        "best_sharpe": round(best[4], 3),
        "best_expression": best[5],
        "best_neutralization": best[6] or "NONE",
        "avg_sharpe": round(sum(all_sharpes) / len(all_sharpes), 3) if all_sharpes else 0,
        "test_count": len(rows),
        "status": "SUBMITTABLE" if best[4] >= 1.58 else ("PROMISING" if best[4] >= 1.0 else "WEAK"),
    }


def ingest_from_results(db: sqlite3.Connection, results_json_path: str):
    """从回测结果JSON文件导入数据"""
    with open(results_json_path) as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    count = 0
    for r in data:
        if r.get("status") != "ok":
            continue

        settings = r.get("settings", {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except:
                settings = {}

        try:
            db.execute(
                "INSERT OR REPLACE INTO field_reports "
                "(dataset, field, region, universe, delay, coverage, pos_ratio, neg_ratio, "
                "best_sharpe, best_expression, best_neutralization, best_truncation) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _extract_dataset(r.get("expression", "")),
                    _extract_field(r.get("expression", "")),
                    settings.get("region", "USA"),
                    settings.get("universe", "TOP3000"),
                    settings.get("delay", 1),
                    None, None, None,
                    r.get("sharpe", 0),
                    r.get("expression", ""),
                    settings.get("neutralization", "NONE"),
                    settings.get("truncation", 0.01)
                )
            )
            count += 1
        except Exception:
            pass

    db.commit()
    return count


def _extract_dataset(expr: str) -> str:
    """从表达式中提取数据集"""
    mappings = {
        "min_loan_rate": "shortinterest3",
        "mean_loan_rate": "shortinterest3",
        "max_loan_rate": "shortinterest3",
        "actual_eps_value_quarterly": "analyst4",
        "rsk60_": "risk60",
        "anl44_": "analyst44",
        "anl47_": "analyst47",
        "close": "market",
        "volume": "market",
        "fnd6_": "fundamental6",
        "broker_dealer": "order_flow_imb",
        "news_transformer": "news_transformer_scores",
        "anl69_": "analyst69",
        "anl15_": "analyst15",
        "anl12_": "analyst12",
        "relative_interest": "search_interest",
        "anl16_": "analyst16",
    }
    for key, ds in mappings.items():
        if key in expr:
            return ds
    return "unknown"


def _extract_field(expr: str) -> str:
    """从表达式中提取主要字段名"""
    import re
    # Match common field patterns
    patterns = [
        r'vec_max\((\w+)\)', r'vec_min\((\w+)\)', r'vec_avg\((\w+)\)',
        r'ts_mean\((\w+)', r'ts_sum\((\w+)', r'zscore\((\w+)',
        r'rank\((\w+)', r'ts_max\((\w+)', r'signed_power\((\w+)',
    ]
    for pat in patterns:
        m = re.search(pat, expr)
        if m:
            return m.group(1)
    return "unknown"


# ===== CLI =====
if __name__ == "__main__":
    import sys

    db = init_db()

    if len(sys.argv) < 2:
        print("brain-data-scope — 离线数据分析工具")
        print("用法:")
        print("  python brain_data_scope.py star <dataset> [region] [universe] [delay]")
        print("  python brain_data_scope.py badge <dataset> [region]")
        print("  python brain_data_scope.py neut <field> [dataset]")
        print("  python brain_data_scope.py report <field> [dataset]")
        print("  python brain_data_scope.py ingest <results.json>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "star":
        ds = sys.argv[2]
        region = sys.argv[3] if len(sys.argv) > 3 else "USA"
        universe = sys.argv[4] if len(sys.argv) > 4 else "TOP3000"
        delay = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        result = available_star(db, ds, region, universe, delay)
        print(f"{ds} / {region} / {universe} / Delay{delay}: {result}")

    elif cmd == "badge":
        ds = sys.argv[2]
        region = sys.argv[3] if len(sys.argv) > 3 else "USA"
        result = osis_badge(db, ds, region)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "neut":
        field = sys.argv[2]
        ds = sys.argv[3] if len(sys.argv) > 3 else None
        result = neutralization_popup(db, field, ds)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "report":
        field = sys.argv[3] if cmd == "report" and len(sys.argv) > 3 else sys.argv[2]
        result = field_report(db, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "ingest":
        path = sys.argv[2]
        count = ingest_from_results(db, path)
        print(f"Imported {count} results from {path}")

    elif cmd == "ingest-all":
        import glob
        total = 0
        for fname in sorted(glob.glob("/tmp/multi_agent/*.json")):
            try:
                c = ingest_from_results(db, fname)
                if c > 0:
                    print(f"  {os.path.basename(fname)}: {c} imported")
                    total += c
            except Exception as e:
                print(f"  {os.path.basename(fname)}: skip ({e})")
        print(f"Total: {total} results imported")
