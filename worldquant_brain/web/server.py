#!/usr/bin/env python3
"""Web仪表盘 — Alpha挖掘进度监控"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
import sqlite3
import subprocess
from datetime import datetime

app = FastAPI(title="WorldQuant BRAIN Dashboard")

WEB_DIR = Path(__file__).parent

DB_PATH = Path(__file__).parent.parent / "data" / "brain.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ─── API Endpoints ───

@app.get("/api/stats")
async def api_stats():
    """系统概览统计"""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM alphas").fetchone()[0]
        valid = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done'").fetchone()[0]
        best_row = conn.execute(
            "SELECT MAX(sharpe) as best, AVG(sharpe) as avg "
            "FROM alphas WHERE status='done'").fetchone()
        submittable = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE is_submittable=1").fetchone()[0]
        # 检测实际运行的挖掘进程
        live_miners = []
        try:
            result = subprocess.run(
                ['pgrep', '-af', 'python.*mining'],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.strip().split('\n'):
                if line and 'python' in line:
                    parts = line.strip().split(' ', 1)
                    pid = parts[0] if parts else ''
                    cmd = parts[1] if len(parts) > 1 else ''
                    script = cmd.split('/')[-1].replace('.py', '') if '/' in cmd else cmd[:50]
                    live_miners.append({"pid": pid, "script": script, "cmd": cmd[:80]})
        except Exception:
            pass

        pending_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0]
        running_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='running'").fetchone()[0]
        done_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
        workers = conn.execute(
            "SELECT * FROM workers").fetchall()

        recent_count = conn.execute(
            "SELECT COUNT(*) FROM alphas "
            "WHERE created_at > datetime('now', '-1 day')").fetchone()[0]

        # 最近1小时新增
        recent_1h = conn.execute(
            "SELECT COUNT(*) FROM alphas "
            "WHERE created_at > datetime('now', '-1 hour')").fetchone()[0]

        return {
            "total_alphas": total,
            "valid_alphas": valid,
            "best_sharpe": round(best_row['best'] or 0, 3),
            "avg_sharpe": round(best_row['avg'] or 0, 3),
            "submittable": submittable,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "done_tasks": done_tasks,
            "recent_24h": recent_count,
            "recent_1h": recent_1h,
            "live_miners": live_miners,
            "mining_active": len(live_miners) > 0,
            "workers": [
                {"id": w['id'], "status": w['status'],
                 "completed": w['tasks_completed'], "failed": w['tasks_failed'],
                 "last_heartbeat": w['last_heartbeat']}
                for w in workers
            ],
            "timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()


@app.get("/api/alphas")
async def api_alphas(limit: int = Query(50, le=200),
                     offset: int = Query(0),
                     sort: str = Query("sharpe"),
                     order: str = Query("desc")):
    """Alpha列表"""
    conn = get_db()
    try:
        allowed = {'sharpe', 'fitness', 'created_at', 'turnover', 'margin'}
        if sort not in allowed:
            sort = 'sharpe'
        direction = 'DESC' if order == 'desc' else 'ASC'

        rows = conn.execute(
            f"SELECT * FROM alphas WHERE status='done' "
            f"ORDER BY {sort} {direction} LIMIT ? OFFSET ?",
            (limit, offset)).fetchall()

        return {
            "alphas": [
                {
                    "id": r['id'], "name": r['name'] or '', "sharpe": r['sharpe'],
                    "fitness": r['fitness'], "ppc": r['ppc'],
                    "margin": r['margin'], "turnover": r['turnover'],
                    "is_submittable": bool(r['is_submittable']),
                    "expression": (r['expression'] or '')[:120],
                    "created_at": r['created_at']
                }
                for r in rows
            ],
            "total": conn.execute("SELECT COUNT(*) FROM alphas WHERE status='done'").fetchone()[0]
        }
    finally:
        conn.close()


@app.get("/api/tasks")
async def api_tasks(limit: int = Query(20, le=100)):
    """任务队列状态"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",
            (limit,)).fetchall()
        return {
            "tasks": [
                {
                    "id": r['id'], "strategy": r['strategy'],
                    "status": r['status'], "worker_id": r['worker_id'] or '',
                    "sharpe": r['sharpe'], "alpha_id": r['alpha_id'] or '',
                    "retries": r['retries'],
                    "created_at": r['created_at'], "updated_at": r['updated_at']
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


@app.get("/api/trend")
async def api_trend():
    """Sharpe趋势 (最近50条)"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT sharpe, created_at FROM alphas WHERE status='done' "
            "ORDER BY created_at DESC LIMIT 50").fetchall()
        return {
            "trend": [
                {"sharpe": r['sharpe'], "time": r['created_at']}
                for r in reversed(rows)
            ]
        }
    finally:
        conn.close()


@app.get("/api/best")
async def api_best(limit: int = Query(20, le=100)):
    """最佳Alpha"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM alphas WHERE status='done' "
            "ORDER BY sharpe DESC LIMIT ?", (limit,)).fetchall()
        return {
            "best": [
                {
                    "id": r['id'], "name": r['name'] or '', "sharpe": r['sharpe'],
                    "fitness": r['fitness'], "ppc": r['ppc'],
                    "margin": r['margin'], "turnover": r['turnover'],
                    "is_submittable": bool(r['is_submittable']),
                    "expression": (r['expression'] or '')[:150],
                    "created_at": r['created_at']
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


# ─── 分析API ───

@app.get("/api/analysis/distribution")
async def api_distribution():
    """Sharpe分布"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT sharpe FROM alphas WHERE status='done'").fetchall()
        values = [r['sharpe'] for r in rows]
        if not values:
            return {"buckets": [], "stats": {}}

        buckets = [
            ("< 0", 0), ("0.0-0.5", 0), ("0.5-1.0", 0),
            ("1.0-1.2", 0), ("1.2-1.4", 0), ("1.4-1.58", 0), (">= 1.58", 0)
        ]
        for v in values:
            if v < 0: buckets[0] = ("< 0", buckets[0][1] + 1)
            elif v < 0.5: buckets[1] = ("0.0-0.5", buckets[1][1] + 1)
            elif v < 1.0: buckets[2] = ("0.5-1.0", buckets[2][1] + 1)
            elif v < 1.2: buckets[3] = ("1.0-1.2", buckets[3][1] + 1)
            elif v < 1.4: buckets[4] = ("1.2-1.4", buckets[4][1] + 1)
            elif v < 1.58: buckets[5] = ("1.4-1.58", buckets[5][1] + 1)
            else: buckets[6] = (">= 1.58", buckets[6][1] + 1)

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "buckets": [{"range": b[0], "count": b[1]} for b in buckets],
            "max_count": max(b[1] for b in buckets),
            "stats": {
                "count": n,
                "mean": round(sum(values) / n, 3),
                "median": round(sorted_vals[n // 2], 3),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "std": round((sum((v - sum(values)/n)**2 for v in values) / n) ** 0.5, 3),
                "pct_positive": round(sum(1 for v in values if v > 0) / n * 100, 1),
                "pct_above_1": round(sum(1 for v in values if v >= 1.0) / n * 100, 1),
                "pct_submittable": round(sum(1 for v in values if v >= 1.58) / n * 100, 1),
            }
        }
    finally:
        conn.close()


@app.get("/api/analysis/by_combo")
async def api_by_combo():
    """按组合类型分析"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT combo_type,
                   COUNT(*) as cnt,
                   ROUND(AVG(sharpe), 3) as avg_sharpe,
                   MAX(sharpe) as max_sharpe,
                   ROUND(AVG(fitness), 2) as avg_fitness,
                   ROUND(AVG(turnover), 4) as avg_turnover
            FROM alphas WHERE status='done' AND combo_type != ''
            GROUP BY combo_type ORDER BY max_sharpe DESC
        """).fetchall()
        return {
            "combos": [dict(r) for r in rows],
            "best_combo": rows[0]['combo_type'] if rows else None
        }
    finally:
        conn.close()


@app.get("/api/analysis/by_tech")
async def api_by_tech():
    """按技术信号分析"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT tech_signal,
                   COUNT(*) as cnt,
                   ROUND(AVG(sharpe), 3) as avg_sharpe,
                   MAX(sharpe) as max_sharpe,
                   ROUND(AVG(fitness), 2) as avg_fitness
            FROM alphas WHERE status='done' AND tech_signal != ''
            GROUP BY tech_signal ORDER BY max_sharpe DESC LIMIT 15
        """).fetchall()
        return {"techs": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/analysis/by_base")
async def api_by_base():
    """按基础Alpha分析"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT base_alpha,
                   COUNT(*) as cnt,
                   ROUND(AVG(sharpe), 3) as avg_sharpe,
                   MAX(sharpe) as max_sharpe
            FROM alphas WHERE status='done' AND base_alpha != ''
            GROUP BY base_alpha ORDER BY max_sharpe DESC LIMIT 10
        """).fetchall()
        return {"bases": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/analysis/by_weight")
async def api_by_weight():
    """按权重参数分析"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT weight,
                   COUNT(*) as cnt,
                   ROUND(AVG(sharpe), 3) as avg_sharpe,
                   MAX(sharpe) as max_sharpe,
                   ROUND(AVG(fitness), 2) as avg_fitness
            FROM alphas WHERE status='done' AND weight IS NOT NULL
            GROUP BY weight ORDER BY max_sharpe DESC
        """).fetchall()
        return {"weights": [dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/analysis/ppa")
async def api_ppa():
    """PPA合规分析"""
    conn = get_db()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done'").fetchone()[0] or 1
        ppc_ok = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done' AND ppc < 0.5").fetchone()[0]
        fit_ok = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done' AND fitness > 0.5").fetchone()[0]
        margin_ok = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done' AND margin > turnover").fetchone()[0]
        sharpe_ok = conn.execute(
            "SELECT COUNT(*) FROM alphas WHERE status='done' AND sharpe >= 1.58").fetchone()[0]

        # 最近50条的PPA趋势
        recent = conn.execute("""
            SELECT sharpe, fitness, ppc, margin, turnover, created_at
            FROM alphas WHERE status='done' ORDER BY created_at DESC LIMIT 50
        """).fetchall()
        ppa_trend = []
        for r in recent:
            criteria = {
                'sharpe_ok': r['sharpe'] >= 1.58,
                'fitness_ok': r['fitness'] > 0.5,
                'ppc_ok': r['ppc'] < 0.5,
                'margin_ok': r['margin'] > r['turnover'],
            }
            score = sum(criteria.values())
            ppa_trend.append({
                'time': r['created_at'],
                'sharpe': r['sharpe'],
                'score': score,
                'all_pass': score == 4
            })

        return {
            "total": total,
            "criteria": [
                {"name": "PPC < 0.5", "pass": ppc_ok, "pct": round(ppc_ok / total * 100, 1)},
                {"name": "Fitness > 0.5", "pass": fit_ok, "pct": round(fit_ok / total * 100, 1)},
                {"name": "Margin > Turnover", "pass": margin_ok, "pct": round(margin_ok / total * 100, 1)},
                {"name": "Sharpe >= 1.58", "pass": sharpe_ok, "pct": round(sharpe_ok / total * 100, 1)},
            ],
            "ppa_trend": ppa_trend
        }
    finally:
        conn.close()


@app.get("/api/analysis/summary")
async def api_summary():
    """综合分析摘要"""
    conn = get_db()
    try:
        stats = conn.execute("""
            SELECT COUNT(*) as total,
                   ROUND(AVG(sharpe), 3) as avg_s,
                   MAX(sharpe) as max_s,
                   ROUND(AVG(fitness), 2) as avg_f,
                   ROUND(AVG(ppc), 3) as avg_ppc,
                   ROUND(AVG(margin), 4) as avg_margin,
                   ROUND(AVG(turnover), 4) as avg_to
            FROM alphas WHERE status='done'
        """).fetchone()

        recent_20 = conn.execute("""
            SELECT sharpe, fitness, name FROM alphas WHERE status='done'
            ORDER BY created_at DESC LIMIT 20
        """).fetchall()
        recent_avg = sum(r['sharpe'] for r in recent_20) / max(len(recent_20), 1)

        return {
            "total": stats['total'],
            "best_sharpe": stats['max_s'],
            "avg_sharpe": stats['avg_s'],
            "recent_avg_sharpe": round(recent_avg, 3),
            "avg_fitness": stats['avg_f'],
            "avg_ppc": stats['avg_ppc'],
            "avg_margin": stats['avg_margin'],
            "avg_turnover": stats['avg_to'],
            "trend": "improving" if recent_avg > (stats['avg_s'] or 0) else "stable"
        }
    finally:
        conn.close()


# ─── 信号灯分析API ───

@app.get("/api/analysis/traffic-light")
async def api_traffic_light():
    """信号灯系统分析"""
    from worldquant_brain.engine.traffic_light import (
        evaluate_direction, compute_direction_strength_index,
        get_light_emoji
    )
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM alphas WHERE status='done' ORDER BY created_at DESC"
        ).fetchall()
        results = [dict(r) for r in rows]

        # 整体评估
        overall = evaluate_direction(results)

        # 按组合类型分组评估
        by_combo = {}
        for r in results:
            combo = (r.get('combo_type') or '').strip()
            if combo:
                by_combo.setdefault(combo, []).append(r)

        combo_lights = {}
        for combo, combo_results in by_combo.items():
            if len(combo_results) >= 3:
                eval_ = evaluate_direction(combo_results)
                combo_lights[combo] = {
                    "light": eval_['light'],
                    "dsi": eval_['dsi'],
                    "n": len(combo_results),
                    "best_sharpe": eval_.get('best_sharpe', 0),
                    "reason": eval_['reason'][:100]
                }

        # 算子多样性分析
        from worldquant_brain.engine.traffic_light import count_operator_families
        op_diversity = {}
        for r in results:
            expr = r.get('expression', '')
            if not expr:
                continue
            families = count_operator_families(expr)
            bucket = str(families) if families <= 5 else "6+"
            op_diversity.setdefault(bucket, {"count": 0, "sharpe_sum": 0, "best": 0})
            op_diversity[bucket]["count"] += 1
            op_diversity[bucket]["sharpe_sum"] += r['sharpe'] or 0
            op_diversity[bucket]["best"] = max(op_diversity[bucket]["best"], r['sharpe'] or 0)

        diversity_stats = []
        for k in sorted(op_diversity.keys(), key=lambda x: int(x.split('+')[0])):
            d = op_diversity[k]
            diversity_stats.append({
                "families": k, "count": d["count"],
                "avg_sharpe": round(d["sharpe_sum"] / max(d["count"], 1), 3),
                "best_sharpe": round(d["best"], 3)
            })

        return {
            "overall": {
                "light": overall['light'],
                "dsi": overall['dsi'],
                "reason": overall['reason'],
                "action": overall['action'],
                "best_sharpe": overall.get('best_sharpe', 0),
                "mean_sharpe": overall.get('mean_sharpe', 0),
                "n": overall.get('n', 0),
            },
            "combo_lights": combo_lights,
            "operator_diversity": diversity_stats,
            "guardrails": {
                "small_sample": overall.get('n', 0) < 5,
                "ceiling_protection": overall.get('best_sharpe', 0) >= 1.0,
                "bimodality": overall.get('bimodality', 0) > 0.556
            }
        }
    finally:
        conn.close()


# ─── Harness / Ledger API ───

@app.get("/api/harness/summary")
async def api_harness_summary():
    """AlphaHarness总览"""
    from worldquant_brain.engine.ledger import ledger
    from worldquant_brain.engine.route_contract import RouteContract
    return {
        "ledger": ledger.get_summary(),
        "rounds": ledger.get_rounds(10),
        "contracts": {
            "eps_usa": RouteContract.template_eps_usa().to_dict(),
            "breakthrough": RouteContract.template_breakthrough().to_dict(),
        }
    }


@app.get("/api/harness/failures")
async def api_harness_failures(failure_type: str = None, limit: int = 50):
    """失败记录查询"""
    from worldquant_brain.engine.ledger import ledger
    return {
        "failures": ledger.get_failures(failure_type, limit),
        "by_type": ledger.get_summary().get('failures_by_type', {})
    }


# ─── Alpha详情 (表达式解释 + 回测分析) ───

@app.get("/api/alphas/{alpha_id}")
async def api_alpha_detail(alpha_id: str):
    """获取单个Alpha的完整详情: 表达式解释 + PPA分析 + 信号灯"""
    from worldquant_brain.engine.expression_explainer import explain_expression, analyze_result
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM alphas WHERE id=? AND status='done'", (alpha_id,)).fetchone()
        if not row:
            return {"error": "Alpha not found"}
        r = dict(row)

        # 表达式解释
        explanation = explain_expression(r.get('expression', '') or '')

        # 结果分析
        analysis = analyze_result(r)

        return {
            "alpha_id": r['id'],
            "name": r.get('name', ''),
            "expression": r.get('expression', '') or '',
            "sharpe": r.get('sharpe', 0),
            "fitness": r.get('fitness', 0),
            "ppc": r.get('ppc', 0),
            "margin": r.get('margin', 0),
            "turnover": r.get('turnover', 0),
            "is_submittable": bool(r.get('is_submittable', 0)),
            "created_at": r.get('created_at', ''),
            "explanation": explanation,
            "analysis": analysis,
        }
    finally:
        conn.close()


# ─── 健康检查 ───

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ─── 页面路由 ───

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """主仪表盘"""
    html_file = WEB_DIR / "templates" / "dashboard.html"
    return HTMLResponse(html_file.read_text(encoding='utf-8'))


@app.get("/alphas", response_class=HTMLResponse)
async def alphas_page():
    """Alpha列表页"""
    html_file = WEB_DIR / "templates" / "alphas.html"
    return HTMLResponse(html_file.read_text(encoding='utf-8'))


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page():
    """数据分析页"""
    html_file = WEB_DIR / "templates" / "analysis.html"
    return HTMLResponse(html_file.read_text(encoding='utf-8'))


# ─── 启动 ───

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
