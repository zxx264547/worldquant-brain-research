#!/bin/bash
# 使用 wq_env 运行 Python 脚本

WQ_ENV="/home/zxx/wq_env"
PYTHON="$WQ_ENV/bin/python"
FORUM_PATH="$WQ_ENV/lib/python3.12/site-packages/cnhkmcp/untracked"

# 使用 PYTHONPATH 让 cnhkmcp 能正确导入
PYTHONPATH="$FORUM_PATH" $PYTHON "$@"
