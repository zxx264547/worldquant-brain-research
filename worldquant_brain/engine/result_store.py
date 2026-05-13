"""结果存储层 — 封装db/repository, 提供高层API"""
import json
from typing import Optional
from pathlib import Path

from worldquant_brain.db.repository import (
    save_alpha, find_by_expression, get_best_alphas,
    get_submittable, count_alphas, push_task, pop_task,
    complete_task, register_worker, start_experiment,
    finish_experiment, init_db, migrate_json_results
)


class ResultStore:
    """统一结果存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "brain.db")
        self.db_path = db_path

    def init(self):
        init_db()

    def migrate(self, json_dir: str = "/tmp/multi_agent"):
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
