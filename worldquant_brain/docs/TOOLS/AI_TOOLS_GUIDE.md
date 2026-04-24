# AI工具详细指南

## 主流AI工具概览

| 工具 | 类型 | 特点 | 费用 |
|------|------|------|------|
| **Codex** | AI编程助手 | GPT5.4模型，支持永久记忆 | 付费 |
| **Gemini CLI** | 命令行工具 | 免费使用MiMo/MiniMax模型 | 免费 |
| **OpenCode** | 桌面应用 | 免费模型，支持MCP | 免费 |
| **TARE** | 浏览器插件 | WebApp自动化 | 免费 |
| **打工人** | 工具集 | AI辅助研究 | 免费 |
| **WebApp** | Web应用 | BRAIN官方AI工具 | 免费 |

## OpenCode + 免费模型配置

### 下载安装
1. 访问 OpenCode 官网下载
2. Windows用户下载桌面版，一路下一步安装

### 配置MCP
修改 `opencode.jsonc` 文件：
```json
"mcp": {
  "worldquant-brain": {
    "type": "local",
    "command": ["python", "path/to/platform_functions.py"]
  }
}
```

### 选择免费模型
在对话框下方选择免费模型（MiniMax等）

## Gemini CLI 高级配置

### 安装/更新
```bash
npm install -g @google/gemini-cli@preview
gemini --version  # 确认版本 0.24.0-preview.2
```

### 配置Skills功能
1. 更新 cnhkmcp 到最新版本
2. 将 skills 文件夹复制到 `~/.gemini/` 目录
3. 启动 Gemini CLI
4. 输入 `/settings` 进入设置
5. 开启 **Preview Features** 和 **Agent Skills**
6. 退出重新进入，输入 `/skills` 查看所有技能

### 解决中文乱码
1. Win+R → 输入 `intl.cpl` → 回车
2. 点击「更改系统区域设置」
3. 勾选「Beta版：使用 Unicode (UTF-8) 提供全球语言支持」
4. 重启电脑

## TARE + MCP 自动化

### 问题
TARE Token限制导致无法无人值守运行

### 解决：MCP + OCR 自动化

**所需工具：**
- Tesseract OCR：https://github.com/tesseract-ocr/tesseract/releases
- 中文语言包：https://github.com/tesseract-ocr/tessdata_fast

**核心Python库：**
```python
import pyautogui    # 屏幕控制
import pytesseract  # OCR识别
import pyperclip    # 剪贴板
```

## cnhkmcp Skills系统

### 安装
```bash
pip install --upgrade cnhkmcp
```

### 在Trae中使用Skills
```bash
# 1. 全局安装 OpenSkills
npm install -g openskills

# 2. 复制 skills 到 .claude 目录
mkdir ~/.claude && cp -r $(pip show cnhkmcp | grep Location | cut -d' ' -f2)/cnhkmcp/skills ~/.claude/

# 3. 进入项目目录同步
cd your_project
openskills sync
```

## 工具选择建议

| 场景 | 推荐工具 |
|------|----------|
| 入门新手 | WebApp + 打工人 |
| 自动化研究 | Gemini CLI + Skills |
| 编程辅助 | Codex + 永久记忆 |
| 免费优先 | OpenCode + 免费模型 |
| 批量处理 | MCP + TARE自动化 |

---

*整理时间：2026年4月*
