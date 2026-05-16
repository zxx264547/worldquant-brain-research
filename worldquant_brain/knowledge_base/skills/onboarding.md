# 项目启动 Skill（Onboarding）

## 目的
让克隆项目后的新用户（或新 AI Agent）在 5 分钟内完成环境配置，开始挖 Alpha。

---

## Step 1: Python 环境

```bash
# 创建虚拟环境（推荐 Python 3.12+）
python3.12 -m venv wq_env

# 激活
source wq_env/bin/activate

# 安装依赖
pip install requests pandas

# 如果需要论坛抓取功能，额外安装
pip install playwright
playwright install chromium
```

---

## Step 2: 用户配置

编辑 `worldquant_brain/config/user_config.json`，填入自己的 BRAIN 账号：

```json
{
  "credentials": {
    "email": "你的BRAIN邮箱",
    "password": "你的BRAIN密码"
  },
  "api_settings": {
    "base_url": "https://api.worldquantbrain.com",
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

> 重要：填完后的 `user_config.json` 不要提交到 Git！在 `.gitignore` 中确认已忽略。

---

## Step 3: AI API 配置（可选）

如果要用 `seed_alpha_generator.py`（论文驱动 Alpha 生成），编辑脚本顶部配置：

```python
AI_BASE_URL = "https://api.moonshot.cn/v1"   # 或其他兼容 OpenAI 的 API
AI_API_KEY = "sk-你的密钥"
AI_MODEL = "kimi-k2-0711-preview"            # 或 claude-sonnet-4-6 等
```

---

## Step 4: 验证安装

```bash
# 检查 Python 环境
wq_env/bin/python -c "import requests, pandas; print('OK')"

# 测试 BRAIN 认证
wq_env/bin/python -c "
from worldquant_brain.scripts.core.api_client import RetryableBrainClient
import asyncio
async def test():
    client = RetryableBrainClient()
    await client.ensure_authenticated()
    print('认证成功')
asyncio.run(test())
"
```

---

## Step 5: 认知循环启动

AI Agent 启动后，按 CLAUDE.md 定义的顺序自动加载：

```
1. CURRENT_STATE.md  → 当前研究进展
2. WORKSPACE_MAP.md  → 文件位置
3. LONG_TERM_MEMORY.md → 经验总结
4. daily/YYYY-MM-DD.md → 今日进展
5. skills-index.md   → 可用技能
```

---

## 关键文件速查

| 文件 | 用途 |
|------|------|
| `CLAUDE.md` | 项目总导航 |
| `worldquant_brain/config/user_config.json` | BRAIN 账号 |
| `worldquant_brain/scripts/core/api_client.py` | API 客户端 |
| `worldquant_brain/scripts/submit_alpha.py` | Alpha 提交 |
| `worldquant_brain/scripts/brain_data_scope.py` | 离线数据分析 |
| `worldquant_brain/scripts/direction_radar.py` | 信号灯系统 |
| `worldquant_brain/scripts/seed_alpha_generator.py` | 论文驱动生成 |

---

## 常见问题

### 代理问题（API 调用失败）
```bash
# 清除代理环境变量
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
```

### Alpha 提交 201 但不生效
必须用 `curl -L` 跟踪 303 重定向（详见 `alpha-submit` skill）：
```bash
python worldquant_brain/scripts/submit_alpha.py <alpha_id>
```

### API 429 限流
等待 `Retry-After` 秒数，通常 60-90 秒后恢复。

### Playwright 缺少库
```bash
sudo apt install libnspr4 libnss3
# 或设置 LD_LIBRARY_PATH 到库所在路径
export LD_LIBRARY_PATH=/path/to/libs:$LD_LIBRARY_PATH
```
