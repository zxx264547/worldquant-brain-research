#!/usr/bin/env python3
"""
Alpha 提交工具 — 使用 curl -L 正确提交 Alpha 到 BRAIN 平台

用法:
  python submit_alpha.py <alpha_id> [<name>]
  python submit_alpha.py --batch <alpha_id1> <alpha_id2> ...

原因:
  Python requests 的 POST 不会跟踪 303 重定向，导致提交返回 201 但未生效。
  curl -L 会跟踪重定向链，正确完成提交。
"""

import asyncio, sys, os, json, subprocess, time

def get_jwt():
    """从已保存的session获取JWT token"""
    sys.path.insert(0, "/home/zxx/worldQuant")
    from worldquant_brain.scripts.core.api_client import RetryableBrainClient

    async def _get():
        client = RetryableBrainClient()
        await client.ensure_authenticated()
        for c in client.client.session.cookies:
            if c.name == 't':
                return c.value
        return None

    return asyncio.run(_get())


def submit_alpha(alpha_id: str, jwt: str = None) -> dict:
    """提交单个 Alpha，返回结果"""
    clean_env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()}

    if not jwt:
        jwt = get_jwt()
    if not jwt:
        return {"success": False, "reason": "无法获取JWT token"}

    # Step 1: 提交
    cmd = ['curl', '-s', '-L', '--max-time', '30', '-w', '\n%{http_code}',
           '-X', 'POST', f'https://api.worldquantbrain.com/alphas/{alpha_id}/submit',
           '-H', f'Cookie: t={jwt}', '-H', 'Accept: application/json',
           '--noproxy', '*']
    result = subprocess.run(cmd, capture_output=True, text=True, env=clean_env, timeout=35)
    lines = result.stdout.strip().split('\n')
    status_code = lines[-1] if lines else '?'
    body = '\n'.join(lines[:-1]) if len(lines) > 1 else ''

    # Step 2: 分析结果
    time.sleep(3)

    if status_code == '200' or status_code == '201':
        # 验证状态
        cmd2 = ['curl', '-s', f'https://api.worldquantbrain.com/alphas/{alpha_id}',
                '-H', f'Cookie: t={jwt}', '--noproxy', '*']
        result2 = subprocess.run(cmd2, capture_output=True, text=True, env=clean_env, timeout=15)
        if result2.stdout:
            alpha = json.loads(result2.stdout)
            submitted = alpha.get('dateSubmitted')
            status = alpha.get('status')
            is_s = alpha.get('is', {}).get('sharpe', 0)

            if submitted and status == 'ACTIVE':
                return {
                    "success": True,
                    "alpha_id": alpha_id,
                    "status": status,
                    "submitted": submitted,
                    "sharpe": is_s,
                    "link": f"https://platform.worldquantbrain.com/alphas/{alpha_id}"
                }
            else:
                return {
                    "success": False,
                    "alpha_id": alpha_id,
                    "reason": f"提交未生效 (status={status}, submitted={submitted})",
                    "detail": body[:300]
                }

    # 403 — 检查失败
    if status_code == '403':
        try:
            data = json.loads(body) if body else {}
            checks = data.get('is', {}).get('checks', [])
            fails = [f"{c['name']}" for c in checks if c.get('result') == 'FAIL']
            return {
                "success": False,
                "alpha_id": alpha_id,
                "reason": "检查未通过",
                "failures": fails,
                "detail": body[:300]
            }
        except:
            return {"success": False, "alpha_id": alpha_id, "reason": f"403 Forbidden", "detail": body[:200]}

    return {"success": False, "alpha_id": alpha_id, "reason": f"HTTP {status_code}", "detail": body[:200]}


def name_alpha(alpha_id: str, name: str, jwt: str = None):
    """给 Alpha 命名并加星标"""
    clean_env = {k: v for k, v in os.environ.items() if 'proxy' not in k.lower()}
    if not jwt:
        jwt = get_jwt()

    cmd = ['curl', '-s', '-X', 'PATCH',
           f'https://api.worldquantbrain.com/alphas/{alpha_id}',
           '-H', f'Cookie: t={jwt}',
           '-H', 'Content-Type: application/json',
           '-H', 'Accept: application/json',
           '-d', json.dumps({"name": name, "favorite": True}),
           '--noproxy', '*']
    result = subprocess.run(cmd, capture_output=True, text=True, env=clean_env, timeout=15)
    return result.status_code == 200


# ===== CLI =====
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--batch":
        ids = sys.argv[2:]
    else:
        ids = [sys.argv[1]]

    jwt = get_jwt()
    if not jwt:
        print("无法认证，请检查配置文件")
        sys.exit(1)

    results = []
    for aid in ids:
        print(f"\n提交 {aid}...")
        result = submit_alpha(aid, jwt)
        results.append(result)

        if result["success"]:
            print(f"  ✅ 提交成功!")
            print(f"  Status: {result.get('status')}")
            print(f"  Submitted: {result.get('submitted')}")
            print(f"  Link: {result.get('link')}")
        else:
            print(f"  ❌ {result['reason']}")
            if 'failures' in result:
                for f in result['failures']:
                    print(f"    - {f}")

    success = sum(1 for r in results if r["success"])
    print(f"\n{'='*40}")
    print(f"Total: {success}/{len(results)} submitted successfully")
