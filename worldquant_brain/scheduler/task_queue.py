#!/usr/bin/env python3
"""基于SQLite的原子任务队列 — 替代文件轮询"""

from worldquant_brain.engine.result_store import store


class TaskQueue:
    """原子任务队列

    使用SQLite WAL模式实现原子push/pop,
    替代 /tmp/multi_agent/ 文件系统IPC
    """

    def __init__(self):
        self.store = store

    async def push(self, strategy: str, expression: str,
                   settings: dict = None, priority: int = 0) -> int:
        return self.store.enqueue(strategy, expression, settings, priority)

    async def push_batch(self, candidates: list, strategy: str = "batch",
                         priority: int = 0) -> list[int]:
        task_ids = []
        for expr, settings, name in candidates:
            tid = self.store.enqueue(strategy, expr, settings, priority)
            task_ids.append(tid)
        return task_ids

    async def pop(self, worker_id: str) -> dict | None:
        return self.store.dequeue(worker_id)

    async def complete(self, task_id: int, alpha_id: str,
                       sharpe: float, error: str = None):
        self.store.mark_done(task_id, alpha_id, sharpe, error)

    @property
    def pending(self) -> int:
        from worldquant_brain.db.repository import get_pending_count
        return get_pending_count()
