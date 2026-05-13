"""analyst10 dataset alpha exploration script.
Tests Performance-Weighted Analyst Estimates fields at incremental complexity levels.
"""
import sys
import os
import json
import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Unset proxy to avoid SSL issues
for var in ['https_proxy', 'http_proxy', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY']:
    os.environ.pop(var, None)

sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
from platform_functions import BrainApiClient, SimulationSettings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Config ───
CREDENTIALS = {"email": "2645471525@qq.com", "password": "20001025ZHANG"}
RESULTS_FILE = Path("/tmp/multi_agent/results.json")

# ─── Phase 1 Test Definitions ───
FIELDS = [
    # Core EPS consensus estimates
    "year1_eps_consensus_estimate",
    "year2_eps_consensus_estimate",

    # Analyst coverage count
    "year1_eps_estimate_analyst_count",
    "year2_eps_estimate_analyst_count",

    # EPS revision signals
    "anl10_epsrevise_ratio_to_close_fy2",
    "anl10_epsrevise_ratio_to_consensus_fq2",

    # Innovation scores
    "anl10_analyst_innovation_eps_innovation_score_fy2",
    "anl10_analyst_innovation_eps_revise_ratio_to_consensus_fy2",

    # Sales smart estimates
    "anl10_salfy1_smart_ests_v0_981",
    "anl10_salfy1_smart_ests_v1_968",

    # EPS revision counts
    "anl10_epsnormal_increase_fq2",

    # Quarter consensus
    "quarter1_eps_consensus_estimate",
    "quarter2_eps_consensus_estimate",
]

# Test windows
WINDOWS = [5, 22, 66, 120, 252]

test_results = []


def _make_settings(**overrides):
    """Create SimulationSettings and return the cleaned dict."""
    s = SimulationSettings(
        instrumentType=overrides.get('instrumentType', 'EQUITY'),
        region=overrides.get('region', 'USA'),
        universe=overrides.get('universe', 'TOP3000'),
        delay=overrides.get('delay', 1),
        decay=overrides.get('decay', 0.0),
        neutralization=overrides.get('neutralization', 'NONE'),
        truncation=overrides.get('truncation', 0.01),
        pasteurization=overrides.get('pasteurization', 'ON'),
        unitHandling=overrides.get('unitHandling', 'VERIFY'),
        nanHandling=overrides.get('nanHandling', 'OFF'),
        language=overrides.get('language', 'FASTEXPR'),
        visualization=overrides.get('visualization', False),
    )
    d = s.model_dump()
    # Remove SUPER-specific fields not needed for REGULAR type
    d.pop('selectionHandling', None)
    d.pop('selectionLimit', None)
    d.pop('componentActivation', None)
    d = {k: v for k, v in d.items() if v is not None}
    return d


def log_result(expression: str, complexity: str, sharpe: float, fitness: float,
               turnover: float, margin: float, ppc: float, status: str, alpha_id: str = ""):
    result = {
        "expression": expression,
        "complexity": complexity,
        "sharpe": round(sharpe, 4),
        "fitness": round(fitness, 4),
        "turnover": round(turnover, 4),
        "margin": round(margin, 4),
        "ppc": round(ppc, 4),
        "status": status,
        "alpha_id": alpha_id,
        "dataset": "analyst10",
        "timestamp": datetime.now().isoformat(),
    }
    test_results.append(result)
    logger.info(f"[{status}] Sharpe={sharpe:.4f} Fitness={fitness:.4f} | {expression[:70]}")
    _save_results()
    return result


def _save_results():
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE) as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing_exprs = {e["expression"]: i for i, e in enumerate(existing)}
    for tr in test_results:
        if tr["expression"] in existing_exprs:
            existing[existing_exprs[tr["expression"]]] = tr
        else:
            existing.append(tr)
    with open(RESULTS_FILE, "w") as f:
        json.dump(existing, f, indent=2)


async def rate_limited_simulation(client, expression: str, retry_count: int = 0) -> Dict[str, Any]:
    """Run a single simulation with rate limiting."""
    settings_dict = _make_settings()
    payload = {
        "type": "REGULAR",
        "settings": settings_dict,
        "regular": expression
    }

    # Small delay between calls
    if retry_count > 0:
        await asyncio.sleep(5)
    else:
        await asyncio.sleep(1)

    logger.info(f"Creating sim: {expression[:60]}...")
    resp = client.session.post(f"{client.base_url}/simulations", json=payload)

    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", "60")
        wait = min(float(retry_after), 120)
        logger.warning(f"Rate limited, waiting {wait}s...")
        await asyncio.sleep(wait)
        return await rate_limited_simulation(client, expression, retry_count + 1)

    if resp.status_code == 422:
        err = resp.text[:300]
        logger.error(f"422 error (likely field not found): {err}")
        return {"status": "ERROR", "message": err}

    if resp.status_code == 400:
        err = resp.text[:300]
        logger.error(f"400 error: {err}")
        return {"status": "ERROR", "message": err}

    if resp.status_code != 201:
        logger.error(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return {"status": "ERROR", "message": f"HTTP {resp.status_code}"}

    location = resp.headers.get("Location", "")
    logger.info(f"Sim created, location: ...{location[-40:]}")
    return await _poll_simulation(client, location, expression)


async def _poll_simulation(client, location: str, expression: str, timeout: int = 450):
    """Poll for simulation completion."""
    poll_interval = 5
    elapsed = 0

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        r = client.session.get(location)
        if r.status_code != 200:
            continue

        data = r.json()
        alpha_id = data.get("alpha")

        if alpha_id:
            logger.info(f"Alpha {alpha_id} ready, fetching results...")
            alpha_resp = client.session.get(f"{client.base_url}/alphas/{alpha_id}")
            if alpha_resp.status_code == 200:
                alpha_data = alpha_resp.json()
                is_data = alpha_data.get("is", {})
                returns = is_data.get("returns", 0)
                margin = is_data.get("margin", 0)
                return {
                    "status": "COMPLETE",
                    "alpha_id": alpha_id,
                    "sharpe": is_data.get("sharpe", 0),
                    "fitness": is_data.get("fitness", 0),
                    "margin": margin,
                    "turnover": is_data.get("turnover", 0),
                    "returns": returns,
                    "ppc": abs(margin / returns) if returns != 0 else 1,
                    "expression": expression,
                }

        status = data.get("status")
        if status == "COMPLETE":
            logger.info(f"Sim completed (no alpha_id)")
            return {"status": "COMPLETE", "sharpe": 0}
        elif status == "ERROR":
            return {"status": "ERROR", "message": data.get("message", "Unknown")}

        progress = data.get("progress")
        if progress and elapsed % 30 < 5:
            logger.info(f"  Progress: {progress:.0%} ({elapsed}s)")

    logger.warning(f"Simulation timed out after {timeout}s")
    return {"status": "TIMEOUT", "message": f"Timed out after {timeout}s"}


async def main():
    logger.info("=== analyst10 Alpha Exploration ===")

    # Authenticate
    client = BrainApiClient()
    auth_result = await client.authenticate(CREDENTIALS["email"], CREDENTIALS["password"])
    logger.info(f"Auth: {auth_result.get('status')}")

    if auth_result.get("status") != "authenticated":
        logger.error("Authentication failed!")
        return

    # ─── PHASE 2A: 0-op Testing ───
    logger.info("\n" + "="*60)
    logger.info("PHASE 2A: 0-op Testing (rank(field))")
    logger.info("="*60)

    for field in FIELDS:
        expr = f"rank({field})"
        result = await rate_limited_simulation(client, expr)

        if result.get("status") == "COMPLETE":
            sharpe = result.get("sharpe", 0)
            status = "promising" if sharpe > 0 else "needs_review"
            log_result(expr, "0-op", sharpe, result.get("fitness", 0),
                       result.get("turnover", 0), result.get("margin", 0),
                       result.get("ppc", 1), status, result.get("alpha_id", ""))
        else:
            log_result(expr, "0-op", 0, 0, 0, 0, 1,
                       f"error: {result.get('message', 'Unknown')}")

    # ─── PHASE 2B: 1-op Testing ───
    logger.info("\n" + "="*60)
    logger.info("PHASE 2B: 1-op Testing (rank(ts_mean(field, W)))")
    logger.info("="*60)

    # Fields that had positive Sharpe in 0-op
    fields_1op = []
    for tr in test_results:
        if tr["complexity"] == "0-op" and tr["sharpe"] > 0:
            # Extract field name
            field = tr["expression"].replace("rank(", "").replace(")", "")
            fields_1op.append(field)

    logger.info(f"Fields progressing to 1-op ({len(fields_1op)}): {fields_1op}")

    for field in fields_1op:
        for window in WINDOWS:
            expr = f"rank(ts_mean({field}, {window}))"
            result = await rate_limited_simulation(client, expr)

            if result.get("status") == "COMPLETE":
                sharpe = result.get("sharpe", 0)
                fitness = result.get("fitness", 0)

                if sharpe >= 1.58 and fitness > 0.5 and result.get("ppc", 1) < 0.5:
                    status = "ready_to_submit"
                elif sharpe > 1.0:
                    status = "needs_more_optimization"
                elif sharpe > 0.5:
                    status = "promising"
                else:
                    status = "needs_review"

                log_result(expr, "1-op", sharpe, fitness,
                           result.get("turnover", 0), result.get("margin", 0),
                           result.get("ppc", 1), status, result.get("alpha_id", ""))
            else:
                log_result(expr, "1-op", 0, 0, 0, 0, 1,
                           f"error: {result.get('message', 'Unknown')}")

    # ─── PHASE 2C: 2-op Testing ───
    logger.info("\n" + "="*60)
    logger.info("PHASE 2C: 2-op Testing (nested operators)")
    logger.info("="*60)

    # Fields with at least one 1-op result with Sharpe > 0.5
    fields_2op = set()
    for tr in test_results:
        if tr["complexity"] == "1-op" and tr["sharpe"] > 0.5:
            expr = tr["expression"]
            if "ts_mean(" in expr:
                inner = expr.split("ts_mean(")[1].split(",")[0].strip()
                fields_2op.add(inner)

    logger.info(f"Fields progressing to 2-op ({len(fields_2op)}): {fields_2op}")

    for field in fields_2op:
        # 2-op pattern 1: ts_backfill(ts_sum(field, 252), 3)
        expr = f"ts_backfill(ts_sum({field}, 252), 3)"
        result = await rate_limited_simulation(client, expr)
        if result.get("status") == "COMPLETE":
            sharpe = result.get("sharpe", 0)
            if sharpe >= 1.58: status = "ready_to_submit"
            elif sharpe > 1.0: status = "needs_more_optimization"
            elif sharpe > 0.5: status = "promising"
            else: status = "needs_review"
            log_result(expr, "2-op_accum", sharpe, result.get("fitness", 0),
                       result.get("turnover", 0), result.get("margin", 0),
                       result.get("ppc", 1), status, result.get("alpha_id", ""))
        else:
            log_result(expr, "2-op_accum", 0, 0, 0, 0, 1,
                       f"error: {result.get('message', 'Unknown')}")

        # 2-op pattern 2: rank(ts_delta(field, 252))
        expr = f"rank(ts_delta({field}, 252))"
        result = await rate_limited_simulation(client, expr)
        if result.get("status") == "COMPLETE":
            sharpe = result.get("sharpe", 0)
            if sharpe >= 1.58: status = "ready_to_submit"
            elif sharpe > 1.0: status = "needs_more_optimization"
            elif sharpe > 0.5: status = "promising"
            else: status = "needs_review"
            log_result(expr, "2-op_momentum", sharpe, result.get("fitness", 0),
                       result.get("turnover", 0), result.get("margin", 0),
                       result.get("ppc", 1), status, result.get("alpha_id", ""))
        else:
            log_result(expr, "2-op_momentum", 0, 0, 0, 0, 1,
                       f"error: {result.get('message', 'Unknown')}")

        # 2-op pattern 3: rank(ts_mean(winsorize(field), 22))
        expr = f"rank(ts_mean(winsorize({field}, 0.01), 22))"
        result = await rate_limited_simulation(client, expr)
        if result.get("status") == "COMPLETE":
            sharpe = result.get("sharpe", 0)
            if sharpe >= 1.58: status = "ready_to_submit"
            elif sharpe > 1.0: status = "needs_more_optimization"
            elif sharpe > 0.5: status = "promising"
            else: status = "needs_review"
            log_result(expr, "2-op_winsorize", sharpe, result.get("fitness", 0),
                       result.get("turnover", 0), result.get("margin", 0),
                       result.get("ppc", 1), status, result.get("alpha_id", ""))
        else:
            log_result(expr, "2-op_winsorize", 0, 0, 0, 0, 1,
                       f"error: {result.get('message', 'Unknown')}")

    # ─── Summary ───
    print("\n" + "="*80)
    print("FINAL SUMMARY - analyst10 Alpha Exploration")
    print("="*80)

    sorted_results = sorted(test_results, key=lambda x: -x["sharpe"])
    for tr in sorted_results[:10]:
        tag = "*** KEY ***" if tr["sharpe"] > 1.0 else ""
        print(f"  S={tr['sharpe']:.4f} F={tr['fitness']:.4f} [{tr['complexity']}] {tr['status']} {tag}")
        print(f"    {tr['expression'][:80]}")

    ready = [tr for tr in test_results if tr["status"] == "ready_to_submit"]
    if ready:
        print(f"\nREADY TO SUBMIT: {len(ready)}")
        for tr in ready:
            print(f"  S={tr['sharpe']:.4f} {tr['expression'][:70]}")


if __name__ == "__main__":
    asyncio.run(main())
