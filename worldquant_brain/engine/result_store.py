"""结果存储层 — 统一 JSON 状态后端（state/*.json）

历史问题（2026-06 修复前）：
- 本模块默认路径曾指向废弃的 SQLite (data/brain.db)，
  而实际数据全部写入 state/alphas.json（JSON 后端），
  导致 cli.py best/submittable/perceive 读到空数据。
- 修复后：所有读写统一走 db.repository（JSON 后端），
  data/brain.db 不再使用（保留文件仅为历史兼容）。
"""
from typing import Optional

from worldquant_brain.db.repository import (
    save_alpha, find_by_expression, get_best_alphas,
    get_submittable, count_alphas, push_task, pop_task,
    complete_task, register_worker, start_experiment,
    finish_experiment, init_db, migrate_json_results,
)


class ResultStore:
    """统一结果存储 — JSON 状态后端"""

    def __init__(self, db_path: str = None):
        # db_path 参数仅为旧调用方兼容保留，JSON 后端无需数据库路径
        if db_path is not None:
            import warnings
            warnings.warn(
                "ResultStore(db_path=...) 已废弃：存储后端已统一为 "
                "worldquant_brain/state/*.json，参数将被忽略",
                DeprecationWarning, stacklevel=2)

    def init(self):
        init_db()

    def migrate(self, json_dir: str = None):
        migrate_json_results(json_dir)

    def save(self, alpha: dict) -> bool:
        return save_alpha(alpha)

    def exists(self, expression: str, settings: dict = None) -> bool:
        return find_by_expression(expression, settings) is not None

    def find(self, expression: str, settings: dict = None) -> Optional[dict]:
        return find_by_expression(expression, settings)

    def best(self, limit: int = 20) -> list[dict]:
        return get_best_alphas(limit)

    def submittable(self) -> list[dict]:
        return get_submittable()

    @property
    def count(self) -> int:
        return count_alphas()

    # Task methods
    def enqueue(self, strategy: str, expression: str,
                settings: dict = None, priority: int = 0) -> int:
        return push_task(strategy, expression, settings, priority)

    def dequeue(self, worker_id: str) -> Optional[dict]:
        return pop_task(worker_id)

    def mark_done(self, task_id: int, alpha_id: str,
                  sharpe: float, error: str = None):
        complete_task(task_id, alpha_id, sharpe,
                      success=(error is None), error=error)

    # Worker methods
    def register_worker(self, worker_id: str):
        register_worker(worker_id)

    # Experiment methods
    def start_experiment(self, name: str, strategy: str,
                         config: dict = None) -> int:
        return start_experiment(name, strategy, config)

    def finish_experiment(self, exp_id: int, best_sharpe: float):
        finish_experiment(exp_id, best_sharpe)


# 全局单例
store = ResultStore()
