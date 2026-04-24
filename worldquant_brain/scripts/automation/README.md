# Automation Scripts

此目录存放自动化脚本，用于实现无人值守的量化研究流程。

## 功能模块

### 1. TARE+OCR 监控

实现 TARE 和 OCR 任务的自动化监控：
- 自动检测 TARE 任务状态
- 自动提交 OCR 结果
- 异常情况告警

### 2. 提交调度器

实现 Alpha 的定时提交：
- 定时检查可提交的 Alpha
- 自动提交到 BRAIN 平台
- 记录提交历史

## 使用方法

```bash
# 启动调度器
./run.sh scripts/automation/submission_scheduler.py

# 检查待提交 Alpha
python3 scripts/automation/submission_scheduler.py --check-only
```

## 注意事项

- 调度任务需要配置 config/user_config.json 中的凭证
- 建议配合 cron 使用实现真正的无人值守
- 定期检查日志确保任务正常运行

---

*最后更新：2026年4月*
