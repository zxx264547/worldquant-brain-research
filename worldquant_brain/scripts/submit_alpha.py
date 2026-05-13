#!/usr/bin/env python3
"""Alpha submission script - uses existing session cookie directly."""

import asyncio
import json
import os
import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

import requests
import urllib3
urllib3.disable_warnings()

ALPHA_ID = "vR50553z"
BASE_URL = "https://api.worldquantbrain.com"

# Session cookie from saved session
JWT_COOKIE = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJTQVdYZWM3cFFiZnRhNE9ZM2ZReHZWcmNQa1A2SnR1TyIsImV4cCI6MTc3ODY2MjU1NH0.zJo-OdSLDV0znlIpErImUyAcgXHdwu8h3BjauucM3pM"

MAX_RETRIES = 5
RETRY_DELAY = 30  # seconds


def make_session():
    """Create a requests session with the saved JWT cookie."""
    s = requests.Session()
    s.cookies.set("t", JWT_COOKIE)
    # No proxy - direct connection works
    for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
        os.environ.pop(k, None)
    return s


async def api_get(session, path, retries=MAX_RETRIES):
    """GET request with retry logic for 429s."""
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", RETRY_DELAY))
                wait = min(retry_after, 120)
                logger.warning(f"  429 rate limited. Waiting {wait}s (attempt {attempt+1}/{retries})...")
                await asyncio.sleep(wait)
                continue
            elif r.status_code == 401:
                logger.error("  401 Unauthorized - session expired")
                return None
            else:
                logger.warning(f"  HTTP {r.status_code}: {r.text[:200]}")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None
        except Exception as e:
            logger.error(f"  Request failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
    return None


async def api_post(session, path, retries=MAX_RETRIES):
    """POST request with retry logic for 429s."""
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            r = session.post(url, timeout=60)
            if r.status_code in (200, 201):
                return r.json() if r.text else {"status": "ok"}
            elif r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", RETRY_DELAY))
                wait = min(retry_after, 120)
                logger.warning(f"  429 rate limited. Waiting {wait}s (attempt {attempt+1}/{retries})...")
                await asyncio.sleep(wait)
                continue
            elif r.status_code == 401:
                logger.error("  401 Unauthorized - session expired")
                return None
            else:
                logger.warning(f"  HTTP {r.status_code}: {r.text[:200]}")
                if attempt < retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return None
        except Exception as e:
            logger.error(f"  Request failed: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(RETRY_DELAY)
                continue
            return None
    return None


async def step_get_details(session):
    """Step 1: Get alpha details."""
    logger.info("=" * 60)
    logger.info("STEP 1: Getting Alpha Details")
    logger.info("=" * 60)

    data = await api_get(session, f"/alphas/{ALPHA_ID}")
    if not data:
        logger.error("  Failed to get alpha details!")
        return None

    is_data = data.get("is", {})
    expression = data.get("regular", {}).get("code", data.get("expression", "N/A"))
    settings = data.get("settings", {})

    logger.info(f"  Alpha ID: {ALPHA_ID}")
    logger.info(f"  Expression: {expression}")
    logger.info(f"  Author: {data.get('author', 'N/A')}")
    logger.info(f"  Status: {data.get('stage', data.get('status', 'N/A'))}")
    logger.info(f"  Date Created: {data.get('dateCreated', 'N/A')}")
    logger.info(f"  Date Submitted: {data.get('dateSubmitted', 'Not submitted')}")

    sharpe = is_data.get("sharpe", 0)
    fitness = is_data.get("fitness", 0)
    margin = is_data.get("margin", 0)
    turnover = is_data.get("turnover", 0)
    returns = is_data.get("returns", 0)
    ppc = abs(margin / returns) if returns != 0 else 1

    logger.info(f"  Sharpe: {sharpe:.4f}")
    logger.info(f"  Fitness: {fitness:.4f}")
    logger.info(f"  Margin: {margin:.6f}")
    logger.info(f"  Turnover: {turnover:.6f}")
    logger.info(f"  Returns: {returns:.6f}")
    logger.info(f"  PPC: {ppc:.4f}")

    logger.info("  --- PPA Criteria Check ---")
    checks = {
        "Sharpe >= 1.58": (sharpe >= 1.58, f"{sharpe:.4f}"),
        "Fitness > 0.5": (fitness > 0.5, f"{fitness:.4f}"),
        "PPC < 0.5": (ppc < 0.5, f"{ppc:.4f}"),
        "Margin > Turnover": (margin > turnover, f"margin={margin:.6f} turnover={turnover:.6f}"),
    }
    all_pass = True
    for check, (passed, val) in checks.items():
        sym = "PASS" if passed else "FAIL"
        logger.info(f"  [{sym}] {check}: {val}")
        if not passed:
            all_pass = False

    if all_pass:
        logger.info("  >>> ALL PPA CRITERIA PASSED!")
    else:
        logger.warning("  >>> Some PPA criteria FAILED (may still be submitable)")

    return data


async def step_get_self_correlation(session):
    """Step 2: Get self-correlation."""
    logger.info("=" * 60)
    logger.info("STEP 2: Getting Self-Correlation")
    logger.info("=" * 60)

    data = await api_get(session, f"/alphas/{ALPHA_ID}/correlations/self")
    if data:
        logger.info(f"  Self-correlation: {json.dumps(data, indent=2)[:600]}")
    else:
        logger.warning("  Self-correlation: empty or unavailable")
    return data


async def step_get_production_correlation(session):
    """Step 3: Get production correlation."""
    logger.info("=" * 60)
    logger.info("STEP 3: Getting Production Correlation")
    logger.info("=" * 60)

    data = await api_get(session, f"/alphas/{ALPHA_ID}/correlations/prod")
    if data:
        logger.info(f"  Production correlation: {json.dumps(data, indent=2)[:600]}")
    else:
        logger.warning("  Production correlation: empty or unavailable")
    return data


async def step_submit(session):
    """Step 4: Submit the alpha."""
    logger.info("=" * 60)
    logger.info("STEP 4: SUBMITTING ALPHA")
    logger.info("=" * 60)

    logger.info(f"  Submitting alpha {ALPHA_ID}...")
    result = await api_post(session, f"/alphas/{ALPHA_ID}/submit")

    if result:
        logger.info("  >>> ALPHA SUBMITTED SUCCESSFULLY! <<<")
        logger.info(f"  Response: {json.dumps(result, indent=2)[:500]}")
    else:
        logger.error("  Submission failed!")

    return result


async def main():
    logger.info("Creating API session with saved JWT cookie...")
    session = make_session()

    # Step 1: Get alpha details
    details = await step_get_details(session)
    if not details:
        logger.error("Cannot proceed: failed to get alpha details.")
        return

    # Check if already submitted
    date_submitted = details.get("dateSubmitted")
    if date_submitted:
        logger.warning(f"  Alpha was already submitted on: {date_submitted}")
        logger.info("  Skipping submission.")
        return

    stage = details.get("stage", "")
    logger.info(f"  Alpha stage: {stage}")

    # Step 2: Self-correlation
    await step_get_self_correlation(session)

    # Step 3: Production correlation
    await step_get_production_correlation(session)

    # Step 4: Submit
    await step_submit(session)

    logger.info("=" * 60)
    logger.info("Submission process complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
