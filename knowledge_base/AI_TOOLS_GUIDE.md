# WorldQuant BRAIN AI工具详细指南

> 从论坛帖子中整理的AI工具使用指南

---

## 一、主流AI工具概览

| 工具 | 类型 | 特点 | 费用 |
|------|------|------|------|
| **Codex** | AI编程助手 | GPT5.4模型，支持永久记忆 | 付费 |
| **Gemini CLI** | 命令行工具 | 免费使用MiMo/MiniMax模型 | 免费 |
| **OpenCode** | 桌面应用 | 免费模型，支持MCP | 免费 |
| **TARE** | 浏览器插件 | WebApp自动化 | 免费 |
| **打工人** | 工具集 | AI辅助研究 | 免费 |
| **WebApp** | Web应用 | BRAIN官方AI工具 | 免费 |

---

## 二、OpenCode + 免费模型配置（推荐）

### 2.1 下载安装
1. 访问 OpenCode 官网下载
2. Windows用户下载桌面版，一路下一步安装

### 2.2 配置MCP
修改 `opencode.jsonc` 文件，添加：
```json
"mcp": {
  "worldquant-brain": {
    "type": "local",
    "command": ["python", "C:\\Users\\admin\\AppData\\Roaming\\Python\\Python314\\site-packages\\cnhkmcp\\untracked\\platform_functions.py"]
  }
}
```

### 2.3 选择免费模型
- 在对话框下方选择免费模型（MiniMax等）
- 可以白嫖使用

---

## 三、Gemini CLI 高级配置

### 3.1 安装/更新
```bash
npm install -g @google/gemini-cli@preview
gemini --version  # 确认版本 0.24.0-preview.2
```

### 3.2 配置Skills功能
1. 更新 cnhkmcp 到最新版本
2. 将 skills 文件夹复制到 `~/.gemini/` 目录
3. 启动 Gemini CLI
4. 输入 `/settings` 进入设置
5. 开启 **Preview Features** 和 **Agent Skills**
6. 退出重新进入，输入 `/skills` 查看所有技能

### 3.3 解决中文乱码
1. Win+R → 输入 `intl.cpl` → 回车
2. 点击「更改系统区域设置」
3. 勾选「Beta版：使用 Unicode (UTF-8) 提供全球语言支持」
4. 重启电脑

### 3.4 Gemini CLI 常用命令
```
/settings     # 进入设置模式
/skills       # 列出所有技能
/model        # 切换模型
/help         # 帮助
```

---

## 四、TARE + MCP 自动化配置

### 4.1 TARE简介
- TARE 是浏览器插件，用于自动化 WebApp 操作
- 可以绕过 Token 限制，实现无人值守

### 4.2 MCP + OCR 自动化
**解决的问题：** TARE 的 Token 限制导致无法无人值守运行

**所需工具：**
- Tesseract OCR：https://github.com/tesseract-ocr/tesseract/releases
- 中文语言包：https://github.com/tesseract-ocr/tessdata_fast

**配置步骤：**
1. 安装 Tesseract（Windows默认路径：`C:\Program Files\Tesseract-OCR\tesseract.exe`）
2. 下载 `chi_sim.traineddata` 放入 tessdata 文件夹
3. 将 TARE 输入框截图保存为 `input_box.png`
4. 运行监控脚本，自动检测并填写

**核心Python库：**
```python
import pyautogui    # 屏幕控制
import pytesseract  # OCR识别
import pyperclip    # 剪贴板
```

### 4.3 MCP配置示例
在 Claude Code 或其他 MCP 客户端中配置：
```json
{
  "mcp": {
    "worldquant-brain": {
      "command": "python",
      "args": ["path/to/platform_functions.py"]
    }
  }
}
```

---

## 五、cnhkmcp Skills 系统

### 5.1 Skills是什么
Skills 是将"方法论"封装成AI可调用的技能模块，让AI能够：
- 调用已有的分析套路
- 复用社区分享的经验
- 自动化执行复杂任务

### 5.2 安装cnhkmcp
```bash
pip install --upgrade cnhkmcp
```

### 5.3 在不同工具中使用Skills

**Trae IDE 配置：**
```bash
# 1. 全局安装 OpenSkills
npm install -g openskills

# 2. 新建 .claude 文件夹，复制 skills 进去
mkdir ~/.claude && cp -r $(pip show cnhkmcp | grep Location | cut -d' ' -f2)/cnhkmcp/skills ~/.claude/

# 3. 进入项目目录同步
cd your_project
openskills sync

# 4. 使用
# 输入：查看并描述你的技能库中的技能
```

**VSCode/Cursor 配置：**
1. 安装 Claude/Cursor 插件
2. 复制 skills 到项目 `.claude` 目录
3. 输入 `/skills` 查看可用技能

### 5.4 常用Skills
- `brain-datafield-exploration-general`：字段全面分析
- `alpha-pattern-detector`：Alpha模式检测
- `backtest-analyzer`：回测结果分析

---

## 六、AIAC比赛模板

### 6.1 高分模板分享
```python
ts_rank(ts_max({data}, d1), d2)
# d1, d2 可取 (60, 250) 或 (20, 120)
```

**经济学解释：**
- 衡量当前季度的峰值在过去一年中处于什么位置
- 高分（接近1.0）：年度级别向上突破，极强动能
- 低分（接近0.0）：长期阴跌趋势

### 6.2 使用技巧
- 适用于 EUR 地区出货较多的场景
- 可以结合 ts_rank 和 ts_max 捕捉动量反转

---

## 七、免费API资源

### 7.1 Google Developer 每月10刀
- 访问：https://developers.google.com/program/my-benefits
- 每月10刀免费额度用于 Google API 服务
- 可调用 Gemini 3.0 Flash API
- 新用户首次注册送300刀（三个月有效期）

### 7.2 iflow 切换模型
当提示 "Insufficient Balance" 时：
1. 输入 `/model` 切换到其他模型
2. 推荐：kimi-k2-thinking

---

## 八、Codex 永久记忆配置

### 8.1 核心思路
让AI记录每次研究操作，形成"越用越聪明"的效果

### 8.2 目录结构
```
量化/
├── GEMINI.md              # 量化入口说明
├── CURRENT_STATE.md       # 当前研究状态
├── WORKSPACE_MAP.md       # 工作区地图
├── MEMORY.md             # 长期记忆
├── memory/
│   └── YYYY-MM-DD.md      # 每日记录
├── skills/
│   └── skills-index.md    # 技能索引
├── factor_library/
│   └── factor_library.sqlite3  # 因子库
└── QUANT_PROCESS_ROUTER.md    # 流程路由
```

### 8.3 工作流
1. 启动时加载 `AI_CONTEXT_LITE` 目录作为轻量上下文
2. 读取当日 `memory` 和 `skills`
3. 研究完成后记录到 `factor_library` 和 `memory`
4. 新脚本、提示词同步更新到 `skills-index.md`

### 8.4 量化入口关键词
```
量化、进入量化、量化模式、继续量化
```

---

## 九、常见问题解决

### 9.1 Token限制
- 使用 MCP + OCR 实现无人值守
- 切换到免费模型（MiniMax、Kimi等）

### 9.2 中文乱码
- 启用系统 UTF-8 支持
- 重启电脑

### 9.3 模型余额不足
- iflow：输入 `/model` 切换模型
- Google API：升级套餐或等待每月额度重置

### 9.4 MCP连接失败
- 检查 Python 路径是否正确
- 确认 cnhkmcp 已正确安装
- 重启 Claude Code/IDE

---

## 十、工具选择建议

| 场景 | 推荐工具 |
|------|----------|
| 入门新手 | WebApp + 打工人 |
| 自动化研究 | Gemini CLI + Skills |
| 编程辅助 | Codex + 永久记忆 |
| 免费优先 | OpenCode + 免费模型 |
| 批量处理 | MCP + TARE自动化 |

---

*整理时间：2026年4月*
