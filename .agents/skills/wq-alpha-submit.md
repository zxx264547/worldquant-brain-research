---
name: wq-alpha-submit
description: "正确提交 Alpha 到 WorldQuant BRAIN 平台，处理 303 重定向问题。当 Alpha 通过 PPA 检查需要提交、或提交后状态仍为 UNSUBMITTED 时使用。"
whenToUse: "需要提交 Alpha、验证提交状态、处理提交 403 检查失败或 303 重定向问题时使用。"
---

# Alpha 提交 Skill

## 用途
正确提交 Alpha 到 BRAIN 平台，避免 Python requests 的 303 重定向问题。

## 问题背景
Python `requests.post()` 不会自动跟踪 POST 的 303 重定向，导致返回 201 但提交未生效。
必须用 `curl -L`（跟踪重定向）或手动处理 303 链。

## 使用方法

### CLI 单次提交
```bash
python worldquant_brain/scripts/submit_alpha.py <alpha_id>
```

### 批量提交
```bash
python worldquant_brain/scripts/submit_alpha.py --batch <alpha_id1> <alpha_id2> ...
```

### 代码调用
```python
from worldquant_brain.scripts.submit_alpha import submit_alpha, name_alpha

# 命名并加星标
name_alpha("omnKPLX5", "A18 EUR mean66 tw t02 d6")

# 提交
result = submit_alpha("omnKPLX5")
# result["success"] == True → 提交成功
# result["failures"] → 失败的检查项列表
```

## 关键实现
```bash
curl -s -L -X POST \
  "https://api.worldquantbrain.com/alphas/{id}/submit" \
  -H "Cookie: t={jwt}" \
  -H "Accept: application/json" \
  --noproxy '*'
```

`-L` 参数是核心——让 curl 自动跟踪 303 重定向链，直到提交完成。

## 常见返回码

| HTTP | 含义 | 处理 |
|------|------|------|
| 200/201 | 提交成功 | 3秒后 GET 验证 status=ACTIVE |
| 403 | 检查未通过 | 解析 body 中的 FAIL 列表，针对性修复 |
| 303 | 需要重定向 | curl -L 自动处理 |

## 注意事项
- 必须先关闭代理：`unset HTTP_PROXY HTTPS_PROXY`
- JWT token 从保存的 session 自动获取
- 提交前建议先命名（`name_alpha`），方便在平台上查找
