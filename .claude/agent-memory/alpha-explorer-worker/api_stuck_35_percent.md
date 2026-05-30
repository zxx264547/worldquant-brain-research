---
name: api_stuck_35_percent_root_cause
description: BRAIN API simulation 永远卡在35% — 根因是服务端问题（IS回测数据缺失或超时）
metadata:
  type: reference
---

# API Simulations Stuck at 35% - 根因确认 (2026-05-25 更新)

## 症状
- `POST /simulations` → 201 成功，返回 simulation ID
- `GET /simulations/{id}` → `{"progress": 0.35}`, `Retry-After: 5.0`
- 永远停在 35%，永不出现 `alpha` 字段
- 尝试等待 300s+ 无改善

## 根因
**服务端问题**：IS 回测的计算资源或数据问题。

证据：
1. POST 返回 201，simulation 创建成功
2. 进度到 35% 后永恒定（35% 正好是 IS 回测的中间阶段）
3. `Retry-After` 一直是 5.0，从未变成 0
4. simulation 一直存在（没变 404），但永不完成

## API 行为
```python
# POST /simulations → 201
location: "https://api.worldquantbrain.com/simulations/{id}"

# GET /simulations/{id} → 永远返回
{
    "progress": 0.35,
    # 永远没有 "alpha" 字段
}
# Headers: Retry-After: 5.0 (永恒定)

# 等待 300s+ 后仍然如此
```

## 正确的轮询代码（已实现，但服务端不触发完成）

```python
while True:
    resp = session.get(location)
    data = resp.json()

    # 正确方式1: alpha_id 在响应中
    if alpha_id := data.get('alpha'):
        return alpha_id

    # 正确方式2: Retry-After=0 表示完成
    retry_after = float(resp.headers.get('Retry-After', '5'))
    if retry_after == 0:
        alpha_id = data.get('alpha')
        if alpha_id:
            return alpha_id
        break  # 但这个条件永远不会触发

    time.sleep(retry_after)
```

## 临时解决方案

1. **等服务端恢复** — 35% 卡住说明服务端 IS 计算资源有问题
2. **换数据集/表达式** — 某些表达式可能触发服务端 bug
3. **用短测试期** — `testPeriod='P0Y3M'` 可能更容易完成
4. **联系 WorldQuant 支持** — 如果问题持续存在

## 测试命令

```bash
# 测试 simulation 是否能完成
/home/zxx/wq_env/bin/python -c "
import asyncio, sys
sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
from platform_functions import BrainApiClient, SimulationSettings, SimulationData

async def test():
    client = BrainApiClient()
    await client.authenticate(email='2645471525@qq.com', password='20001025ZHANG')
    sim_settings = SimulationSettings(region='USA', universe='TOP3000', delay=1, testPeriod='P0Y3M')
    sim_data = SimulationData(settings=sim_settings, regular='rank(close)')
    result = await client.create_simulation(sim_data)
    print(f'Sharpe: {result.get(\"is\", {}).get(\"sharpe\", \"N/A\")}')

asyncio.run(test())
"
```

## 相关文件
- `api_client.py:_poll_for_completion` - 轮询逻辑（正确，但服务端不触发）
- `batch_backtest.py` - 批量回测（同样受影响）

---

## Alpha 提交成功的判断规则（2026-05-25 更新）

### 核心规则
**返回 HTTP 201 = 真正提交成功，其他都是失败**

| HTTP Status | 含义 |
|-------------|------|
| 201 | 提交成功，触发 OS 回测 |
| 403 + checks | 提交检查失败（被拒绝） |
| 429 | 限流（需等待后重试） |
| 400 | 参数错误或认证失败 |

### 验证方法
```python
resp = session.post(f'{base_url}/alphas/{alpha_id}/submit')

if resp.status_code == 201:
    # 真正提交成功
    pass
elif resp.status_code == 403:
    # 检查失败，看 checks 详情
    checks = resp.json().get('is', {}).get('checks', [])
    failed = [c['name'] for c in checks if c['result'] == 'FAIL']
elif resp.status_code == 429:
    # 限流，等待后重试
```

### 检查真正提交成功的字段
```python
# dateSubmitted 有值 = 已提交
# status = 'SUBMITTED' = 已提交
# stage = 'OS' = 已触发 OS 回测
```