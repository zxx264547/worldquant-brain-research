# MCP配置指南

## cnhkmcp 安装与配置

### 安装
```bash
pip install --upgrade cnhkmcp
```

### 配置MCP连接
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

### Windows路径示例
```
C:\Users\admin\AppData\Roaming\Python\Python314\site-packages\cnhkmcp\untracked\platform_functions.py
```

## Skills配置

### Gemini CLI中配置Skills
1. 复制 cnhkmcp 中的 skills 文件夹到 `~/.gemini/` 目录
2. 启动 Gemini CLI
3. 输入 `/settings`
4. 开启 **Preview Features** 和 **Agent Skills**
5. 输入 `/skills` 查看所有技能

### Trae IDE中配置Skills
```bash
npm install -g openskills
mkdir ~/.claude && cp -r cnhkmcp/skills ~/.claude/
cd your_project && openskills sync
```

## 常见问题

| 问题 | 解决 |
|------|------|
| Token限制 | MCP+OCR自动化 |
| MCP连接失败 | 检查Python路径是否正确 |
| Skills不显示 | 确认skills文件夹在正确位置 |
