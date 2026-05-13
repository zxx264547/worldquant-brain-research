"""Focused analyst10 testing - using only proven working field names.
Goal: test fields with anl10_ prefix that we verified work as expression names.
"""
import sys, os, json, asyncio, time, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

for var in ['https_proxy','http_proxy','HTTPS_PROXY','HTTP_PROXY','ALL_PROXY']:
    os.environ.pop(var, None)

sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
from platform_functions import BrainApiClient, SimulationSettings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CREDENTIALS = {"email": "2645471525@qq.com", "password": "20001025ZHANG"}
RESULTS_FILE = Path("/tmp/multi_agent/results.json")

# Fields we KNOW work (anl10_ prefix or specifically verified)
FIELDS_TO_TEST = [
    # REVISION RATIOS TO CLOSE (momentum signals)
    "anl10_epsrevise_ratio_to_close_fy2",
    "anl10_epsrevise_ratio_to_close_fy1",
    "anl10_epsrevise_ratio_to_close_fq1",
    "anl10_epsrevise_ratio_to_close_fq2",

    # REVISION RATIOS TO CONSENSUS
    "anl10_epsrevise_ratio_to_consensus_fy2",
    "anl10_epsrevise_ratio_to_consensus_fy1",
    "anl10_epsrevise_ratio_to_consensus_fq1",
    "anl10_epsrevise_ratio_to_consensus_fq2",

    # NORMAL INCREASE/DECREASE (breadth signals)
    "anl10_epsnormal_increase_fy2",
    "anl10_epsnormal_increase_fy1",
    "anl10_epsnormal_increase_fq2",
    "anl10_epsnormal_increase_fq1",
    "anl10_epsnormal_decrease_fy2",
    "anl10_epsnormal_decrease_fy1",
    "anl10_epsnormal_decrease_fq2",
    "anl10_epsnormal_decrease_fq1",

    # INNOVATION SCORES
    "anl10_epsinnovation_score_fy1",
    "anl10_epsinnovation_score_fy2",
    "anl10_epsinnovation_score_fq1",
    "anl10_epsinnovation_score_fq2",

    # ANALYST INNOVATION: REVISE VALUES
    "anl10_analyst_innovation_eps_revise_value_fy1",
    "anl10_analyst_innovation_eps_revise_value_fq2",

    # ANALYST INNOVATION: REVISE RATIO TO CONSENSUS
    "anl10_analyst_innovation_eps_revise_ratio_to_consensus_fy1",
    "anl10_analyst_innovation_eps_revise_ratio_to_consensus_fy2",
    "anl10_analyst_innovation_eps_revise_ratio_to_consensus_fq1",
    "anl10_analyst_innovation_eps_revise_ratio_to_consensus_fq2",

    # ANALYST INNOVATION SCORES
    "anl10_analyst_innovation_eps_innovation_score_fy1",
    "anl10_analyst_innovation_eps_innovation_score_fy2",
    "anl10_analyst_innovation_eps_innovation_score_fq1",
    "anl10_analyst_innovation_eps_innovation_score_fq2",

    # SALES SMART ESTIMATES
    "anl10_salfq1_consensus_971",
    "anl10_salfy1_smart_ests_v0_981",
    "anl10_salfy1_smart_ests_v1_968",
]

WINDOWS = [5, 22, 66, 120, 252]

def make_settings():
    s = SimulationSettings(
        instrumentType='EQUITY', region='USA', universe='TOP3000',
        delay=1, decay=0.0, neutralization='NONE', truncation=0.01,
        pasteurization='ON', unitHandling='VERIFY', nanHandling='OFF',
        language='FASTEXPR', visualization=False,
    )
    d = s.model_dump()
    for k in ['selectionHandling','selectionLimit','componentActivation']:
        d.pop(k, None)
    return {k:v for k,v in d.items() if v is not None}


def load_existing():
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text())
        except Exception:
            pass
    return []


def save_results(new_results):
    existing = load_existing()
    exprs = {e["expression"]: i for i, e in enumerate(existing)}
    for r in new_results:
        if r["expression"] in exprs:
            existing[exprs[r["expression"]]] = r
        else:
            existing.append(r)
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(existing, indent=2))


def make_result(expression, complexity, sharpe, fitness, turnover, margin, ppc, status, alpha_id="", error=""):
    return {
        "expression": expression, "complexity": complexity, "dataset": "analyst10",
        "sharpe": round(sharpe,4), "fitness": round(fitness,4),
        "turnover": round(turnover,4), "margin": round(margin,4), "ppc": round(ppc,4),
        "status": status, "alpha_id": alpha_id, "error": error,
        "timestamp": datetime.now().isoformat(),
    }


async def run_simulation(client, expression, retry=0) -> Dict[str, Any]:
    await asyncio.sleep(1.5)  # rate limiting

    settings_dict = make_settings()
    payload = {"type": "REGULAR", "settings": settings_dict, "regular": expression}

    resp = client.session.post(f"{client.base_url}/simulations", json=payload)

    if resp.status_code == 429:
        wait = min(float(resp.headers.get("Retry-After", 60)), 120)
        logger.warning(f"Rate limited, wait {wait}s")
        await asyncio.sleep(wait)
        return await run_simulation(client, expression, retry + 1)

    if resp.status_code == 201:
        location = resp.headers.get("Location", "")
        return await poll_sim(client, location, expression)

    err = resp.text[:300]
    logger.error(f"HTTP {resp.status_code}: {err}")
    return {"status": "ERROR", "message": err}


async def poll_sim(client, location, expression, timeout=450):
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(5)
        elapsed += 5

        r = client.session.get(location)
        if r.status_code != 200:
            continue

        data = r.json()
        alpha_id = data.get("alpha")

        if alpha_id:
            ar = client.session.get(f"{client.base_url}/alphas/{alpha_id}")
            if ar.status_code == 200:
                ad = ar.json()
                isd = ad.get("is", {})
                returns = isd.get("returns", 0)
                margin = isd.get("margin", 0)
                return {
                    "status": "COMPLETE",
                    "alpha_id": alpha_id,
                    "sharpe": isd.get("sharpe", 0),
                    "fitness": isd.get("fitness", 0),
                    "margin": margin,
                    "turnover": isd.get("turnover", 0),
                    "returns": returns,
                    "ppc": abs(margin / returns) if returns else 1,
                }

        if data.get("status") == "COMPLETE":
            return {"status": "COMPLETE", "sharpe": 0}
        if data.get("status") == "ERROR":
            return {"status": "ERROR", "message": data.get("message", "Unknown")}

        if data.get("progress") and elapsed % 30 < 5:
            logger.info(f"  {expression[:30]}... {data['progress']:.0%} ({elapsed}s)")

    return {"status": "TIMEOUT", "message": f"Timeout {timeout}s"}


async def main():
    logger.info("=== analyst10 (v2) Focused Exploration ===")

    client = BrainApiClient()
    await client.authenticate(CREDENTIALS["email"], CREDENTIALS["password"])

    results = []
    existing = load_existing()
    tested_exprs = {e["expression"] for e in existing}

    # ─── 0-op Tests ───
    logger.info("\n--- 0-op: rank(field) ---")
    for field in FIELDS_TO_TEST:
        expr = f"rank({field})"
        if expr in tested_exprs:
            logger.info(f"Skipping (already tested): {expr[:50]}")
            continue

        logger.info(f"Testing: {expr[:60]}")
        result = await run_simulation(client, expr)

        if result.get("status") == "COMPLETE":
            sharpe = result.get("sharpe", 0)
            status = "promising" if sharpe > 0 else "needs_review"
            r = make_result(expr, "0-op", sharpe, result.get("fitness",0),
                          result.get("turnover",0), result.get("margin",0),
                          result.get("ppc",1), status, result.get("alpha_id",""))
            logger.info(f"  => Sharpe={sharpe:.4f} Fit={result.get('fitness',0):.4f} [{status}]")
        else:
            r = make_result(expr, "0-op", 0,0,0,0,1, "error",
                          error=result.get("message",""))
            logger.info(f"  => ERROR: {result.get('message','')[:80]}")

        results.append(r)
        save_results(results)

    # ─── 1-op Tests ───
    logger.info("\n--- 1-op: rank(ts_mean(field, W)) ---")
    positive_0op = []
    for r in results:
        if r["complexity"] == "0-op" and r["sharpe"] > 0:
            field = r["expression"].replace("rank(","").replace(")","")
            positive_0op.append(field)

    logger.info(f"Promising 0-op fields: {positive_0op}")

    for field in positive_0op:
        for window in WINDOWS:
            expr = f"rank(ts_mean({field}, {window}))"
            if expr in tested_exprs:
                continue

            logger.info(f"Testing: rank(ts_mean({field[:40]}, {window}))")
            result = await run_simulation(client, expr)

            if result.get("status") == "COMPLETE":
                sharpe = result.get("sharpe", 0)
                fitness = result.get("fitness", 0)
                ppc = result.get("ppc", 1)

                if sharpe >= 1.58 and fitness > 0.5 and ppc < 0.5:
                    status = "ready_to_submit"
                elif sharpe > 1.0:
                    status = "needs_more_optimization"
                elif sharpe > 0.5:
                    status = "promising"
                else:
                    status = "needs_review"

                r = make_result(expr, "1-op", sharpe, fitness,
                              result.get("turnover",0), result.get("margin",0),
                              ppc, status, result.get("alpha_id",""))
                logger.info(f"  => Sharpe={sharpe:.4f} Fit={fitness:.4f} [{status}]")
            else:
                r = make_result(expr, "1-op", 0,0,0,0,1, "error",
                              error=result.get("message",""))

            results.append(r)
            save_results(results)

    # ─── 2-op Tests ───
    logger.info("\n--- 2-op: nested operators ---")
    strong_1op = set()
    for r in results:
        if r["complexity"] == "1-op" and r["sharpe"] > 0.5:
            expr = r["expression"]
            if "ts_mean(" in expr:
                field = expr.split("ts_mean(")[1].split(",")[0].strip()
                strong_1op.add(field)

    logger.info(f"Strong 1-op fields: {strong_1op}")

    for field in strong_1op:
        for op_name, op_expr in [
            ("accum_252", f"ts_backfill(ts_sum({field}, 252), 3)"),
            ("momentum_252", f"rank(ts_delta({field}, 252))"),
            ("winsorize", f"rank(ts_mean(winsorize({field}, 0.01), 22))"),
        ]:
            if op_expr in tested_exprs:
                continue

            logger.info(f"Testing 2-op {op_name}: {op_expr[:60]}")
            result = await run_simulation(client, op_expr)

            if result.get("status") == "COMPLETE":
                sharpe = result.get("sharpe", 0)
                fitness = result.get("fitness", 0)
                ppc = result.get("ppc", 1)

                if sharpe >= 1.58 and fitness > 0.5 and ppc < 0.5:
                    status = "ready_to_submit"
                elif sharpe > 1.0:
                    status = "needs_more_optimization"
                elif sharpe > 0.8:
                    status = "high_potential"
                elif sharpe > 0.5:
                    status = "promising"
                else:
                    status = "needs_review"

                r = make_result(op_expr, f"2-op_{op_name}", sharpe, fitness,
                              result.get("turnover",0), result.get("margin",0),
                              ppc, status, result.get("alpha_id",""))
                logger.info(f"  => Sharpe={sharpe:.4f} Fit={fitness:.4f} [{status}]")
            else:
                r = make_result(op_expr, f"2-op_{op_name}", 0,0,0,0,1, "error",
                              error=result.get("message",""))

            results.append(r)
            save_results(results)

    # ─── Final Summary ───
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    sorted_r = sorted(results, key=lambda x: -x["sharpe"])
    for r in sorted_r[:15]:
        print(f"  S={r['sharpe']:.4f} F={r['fitness']:.4f} T={r['turnover']:.4f} [{r['complexity']}] {r['status']}")
        print(f"    {r['expression'][:80]}")

    high = [r for r in results if r["sharpe"] > 1.0]
    if high:
        print(f"\n*** {len(high)} expressions with Sharpe > 1.0 ***")
        for r in high:
            print(f"  S={r['sharpe']:.4f} {r['expression'][:70]}")

if __name__ == "__main__":
    asyncio.run(main())
