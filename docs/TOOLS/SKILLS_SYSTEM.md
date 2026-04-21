# Skills系统使用

## Skills是什么
Skills 是将"方法论"封装成AI可调用的技能模块，让AI能够：
- 调用已有的分析套路
- 复用社区分享的经验
- 自动化执行复杂任务

## 安装cnhkmcp
```bash
pip install --upgrade cnhkmcp
```

## 内置Skills

| Skill名称 | 用途 |
|-----------|------|
| `brain-datafield-exploration-general` | 字段全面分析 |
| `alpha-pattern-detector` | Alpha模式检测 |
| `backtest-analyzer` | 回测结果分析 |
| `pnl-scoring` | PnL续航力评分 |
| `alpha-submission-checker` | 提交前检查 |
| `correlation-family-splitter` | 相关性分族工具 |

## 在不同工具中使用Skills

### Gemini CLI
```bash
gemini --version  # 确认 0.24.0-preview.2
gemini
/settings  # 开启 Agent Skills
/skills    # 查看所有技能
```

### Trae IDE
```bash
npm install -g openskills
openskills sync
# 输入：查看并描述你的技能库中的技能
```

### VSCode/Cursor
1. 安装 Claude/Cursor 插件
2. 复制 skills 到项目 `.claude` 目录
3. 输入 `/skills` 查看可用技能

## 使用示例

使用brain-datafield-exploration-general技能对USA地区中analyst11的anl11_1e字段进行全面分析。

## Skills工作流

```
用户输入idea
    ↓
OpenCode/Gemini CLI
    ↓
加载相关Skills
    ↓
执行研究流程
    ↓
记录到因子库和记忆系统
    ↓
更新Skills索引
```

---

*整理时间：2026年4月*
