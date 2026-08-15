#!/usr/bin/env python3
"""Worker池 — 替代独立进程轮询"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worldquant_brain.scheduler.task_queue import TaskQueue
from worldquant_brain.engine.backtest_runner import BacktestRunner


class WorkerPool:
    """asyncio Worker池

    替代原有的8个独立进程 worker_service.py
    """

    def __init__(self, size: int = 4, poll_interval: float = 5.0):
        self.size = size
        self.poll_interval = poll_interval
        self.queue = TaskQueue()
        self.runner = BacktestRunner()
        self._tasks = []
        self._running = False

    async def start(self):
        self._running = True
        await self.runner.init()

        # 崩溃恢复：重置上次进程遗留的 running 任务
        from worldquant_brain.db.repository import recover_stale_tasks
        recover_stale_tasks()

        for i in range(self.size):
            worker_id = f"worker_{i+1}"
            self.queue.store.register_worker(worker_id)
            task = asyncio.create_task(self._worker_loop(worker_id))
            self._tasks.append(task)

        print(f"[WorkerPool] {self.size} workers started")

    async def stop(self):
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _worker_loop(self, worker_id: str):
        """Worker主循环 — 拉取任务→执行→标记完成"""
        while self._running:
            task = await self.queue.pop(worker_id)
            if task is None:
                await asyncio.sleep(self.poll_interval)
                continue

            try:
                result = await self.runner.run(
                    task['expression'],
                    task['settings_json'] if isinstance(task['settings_json'], dict)
                    else {}, task.get('strategy', 'unknown'))
                sharpe = result.get('sharpe', 0)
                alpha_id = result.get('alpha_id', '')
                await self.queue.complete(task['id'], alpha_id, sharpe)

            except Exception as e:
                await self.queue.complete(task['id'], '', 0, error=str(e))
