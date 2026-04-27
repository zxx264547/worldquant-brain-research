#!/usr/bin/env python3
"""
Multi-Agent 系统状态管理器
负责读写 /tmp/multi_agent/state.json，追踪所有Worker状态和任务进度
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

BASE_DIR = Path("/tmp/multi_agent")
STATE_FILE = BASE_DIR / "state.json"


@dataclass
class WorkerStatus:
    worker_id: str
    status: str = "idle"  # idle, busy, failed
    current_ideas: List[int] = field(default_factory=list)
    last_seen: str = ""
    consecutive_failures: int = 0


@dataclass
class IdeaStatus:
    idea_id: int
    status: str = "pending"  # pending, in_progress, completed, failed
    assigned_worker: str = ""
    attempts: int = 0
    last_updated: str = ""


@dataclass
class TeamLeadState:
    phase: str = "idle"  # idle, generating, distributing, monitoring, optimizing
    best_sharpe: float = 0.0
    best_alpha_id: str = ""
    workers: Dict[str, WorkerStatus] = field(default_factory=dict)
    ideas_status: Dict[int, IdeaStatus] = field(default_factory=dict)
    last_poll: str = ""
    consecutive_empty_polls: int = 0
    total_processed: int = 0
    total_submission_ready: int = 0


class StateManager:
    """状态管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.state = self._load_state()

    def _load_state(self) -> TeamLeadState:
        """从文件加载状态"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return self._dict_to_state(data)
            except Exception as e:
                print(f"Warning: Failed to load state: {e}")

        # 返回默认状态
        return self._create_default_state()

    def _dict_to_state(self, data: dict) -> TeamLeadState:
        """字典转状态对象"""
        workers = {}
        for k, v in data.get('workers', {}).items():
            workers[k] = WorkerStatus(**v) if isinstance(v, dict) else v

        ideas = {}
        for k, v in data.get('ideas_status', {}).items():
            # Handle both numeric IDs (2001) and string IDs (idea_1)
            try:
                idea_id = int(k) if k.isdigit() else k
            except ValueError:
                idea_id = k
            ideas[idea_id] = IdeaStatus(**v) if isinstance(v, dict) else v

        return TeamLeadState(
            phase=data.get('phase', 'idle'),
            best_sharpe=data.get('best_sharpe', 0.0),
            best_alpha_id=data.get('best_alpha_id', ''),
            workers=workers,
            ideas_status=ideas,
            last_poll=data.get('last_poll', ''),
            consecutive_empty_polls=data.get('consecutive_empty_polls', 0),
            total_processed=data.get('total_processed', 0),
            total_submission_ready=data.get('total_submission_ready', 0),
        )

    def _state_to_dict(self, state: TeamLeadState) -> dict:
        """状态对象转字典"""
        return {
            'phase': state.phase,
            'best_sharpe': state.best_sharpe,
            'best_alpha_id': state.best_alpha_id,
            'workers': {k: asdict(v) for k, v in state.workers.items()},
            'ideas_status': {str(k): asdict(v) for k, v in state.ideas_status.items()},
            'last_poll': state.last_poll,
            'consecutive_empty_polls': state.consecutive_empty_polls,
            'total_processed': state.total_processed,
            'total_submission_ready': state.total_submission_ready,
            'last_updated': datetime.now().isoformat(),
        }

    def _create_default_state(self) -> TeamLeadState:
        """创建默认状态"""
        workers = {}
        for i in range(1, 9):
            workers[f'worker_{i}'] = WorkerStatus(worker_id=f'worker_{i}')

        return TeamLeadState(workers=workers)

    def save(self):
        """保存状态到文件"""
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(self._state_to_dict(self.state), f, indent=2)

    def load(self) -> TeamLeadState:
        """重新加载状态"""
        self.state = self._load_state()
        return self.state

    # ========== Worker管理 ==========

    def get_worker(self, worker_id: str) -> Optional[WorkerStatus]:
        """获取Worker状态"""
        return self.state.workers.get(worker_id)

    def get_idle_workers(self) -> List[str]:
        """获取所有idle的worker"""
        return [
            w.worker_id for w in self.state.workers.values()
            if w.status == 'idle'
        ]

    def get_busy_workers(self) -> List[str]:
        """获取所有busy的worker"""
        return [
            w.worker_id for w in self.state.workers.values()
            if w.status == 'busy'
        ]

    def set_worker_busy(self, worker_id: str, idea_ids: List[int]):
        """标记worker为busy"""
        if worker_id in self.state.workers:
            self.state.workers[worker_id].status = 'busy'
            self.state.workers[worker_id].current_ideas = idea_ids
            self.state.workers[worker_id].last_seen = datetime.now().isoformat()

    def set_worker_idle(self, worker_id: str):
        """标记worker为idle"""
        if worker_id in self.state.workers:
            self.state.workers[worker_id].status = 'idle'
            self.state.workers[worker_id].current_ideas = []
            self.state.workers[worker_id].last_seen = datetime.now().isoformat()

    def set_worker_failed(self, worker_id: str):
        """标记worker为failed"""
        if worker_id in self.state.workers:
            self.state.workers[worker_id].status = 'failed'
            self.state.workers[worker_id].consecutive_failures += 1

    def reset_worker(self, worker_id: str):
        """重置worker状态"""
        if worker_id in self.state.workers:
            self.state.workers[worker_id].status = 'idle'
            self.state.workers[worker_id].consecutive_failures = 0
            self.state.workers[worker_id].last_seen = datetime.now().isoformat()

    # ========== Idea管理 ==========

    def get_idea_status(self, idea_id: int) -> Optional[IdeaStatus]:
        """获取idea状态"""
        return self.state.ideas_status.get(idea_id)

    def set_idea_in_progress(self, idea_id: int, worker_id: str):
        """标记idea为进行中"""
        self.state.ideas_status[idea_id] = IdeaStatus(
            idea_id=idea_id,
            status='in_progress',
            assigned_worker=worker_id,
            last_updated=datetime.now().isoformat(),
        )

    def set_idea_completed(self, idea_id: int):
        """标记idea为完成"""
        if idea_id in self.state.ideas_status:
            self.state.ideas_status[idea_id].status = 'completed'
            self.state.ideas_status[idea_id].last_updated = datetime.now().isoformat()

    def set_idea_failed(self, idea_id: int):
        """标记idea为失败"""
        if idea_id in self.state.ideas_status:
            self.state.ideas_status[idea_id].status = 'failed'
            self.state.ideas_status[idea_id].attempts += 1
            self.state.ideas_status[idea_id].last_updated = datetime.now().isoformat()

    def get_pending_ideas(self) -> List[int]:
        """获取所有pending的idea"""
        return [
            iid for iid, s in self.state.ideas_status.items()
            if s.status == 'pending'
        ]

    def get_in_progress_ideas(self) -> List[int]:
        """获取所有进行中的idea"""
        return [
            iid for iid, s in self.state.ideas_status.items()
            if s.status == 'in_progress'
        ]

    # ========== 全局状态 ==========

    def update_best_sharpe(self, sharpe: float, alpha_id: str):
        """更新最佳Sharpe"""
        if sharpe > self.state.best_sharpe:
            self.state.best_sharpe = sharpe
            self.state.best_alpha_id = alpha_id
            print(f"[StateManager] New best Sharpe: {sharpe} (alpha: {alpha_id})")

    def increment_processed(self):
        """增加已处理计数"""
        self.state.total_processed += 1

    def increment_submission_ready(self):
        """增加可提交计数"""
        self.state.total_submission_ready += 1

    def update_phase(self, phase: str):
        """更新阶段"""
        self.state.phase = phase
        print(f"[StateManager] Phase: {phase}")

    def record_poll(self, has_new_results: bool):
        """记录一次poll"""
        self.state.last_poll = datetime.now().isoformat()
        if has_new_results:
            self.state.consecutive_empty_polls = 0
        else:
            self.state.consecutive_empty_polls += 1

    def should_reassign(self, idea_id: int) -> bool:
        """判断idea是否应该重新分配"""
        status = self.state.ideas_status.get(idea_id)
        if not status:
            return True
        if status.status == 'failed' and status.attempts < 3:
            return True
        if status.status == 'in_progress':
            # 检查是否超时（15分钟）
            last_update = datetime.fromisoformat(status.last_updated)
            elapsed = (datetime.now() - last_update).total_seconds()
            if elapsed > 900:  # 15分钟
                return True
        return False

    # ========== 统计 ==========

    def get_stats(self) -> dict:
        """获取统计信息"""
        workers = self.state.workers
        return {
            'phase': self.state.phase,
            'best_sharpe': self.state.best_sharpe,
            'best_alpha_id': self.state.best_alpha_id,
            'workers': {
                'active': sum(1 for w in workers.values() if w.status == 'busy'),
                'idle': sum(1 for w in workers.values() if w.status == 'idle'),
                'failed': sum(1 for w in workers.values() if w.status == 'failed'),
            },
            'ideas': {
                'pending': len(self.get_pending_ideas()),
                'in_progress': len(self.get_in_progress_ideas()),
                'completed': sum(1 for s in self.state.ideas_status.values() if s.status == 'completed'),
                'failed': sum(1 for s in self.state.ideas_status.values() if s.status == 'failed'),
            },
            'total_processed': self.state.total_processed,
            'total_submission_ready': self.state.total_submission_ready,
            'consecutive_empty_polls': self.state.consecutive_empty_polls,
            'last_poll': self.state.last_poll,
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        print("=" * 50)
        print("Team Lead State")
        print("=" * 50)
        print(f"Phase: {stats['phase']}")
        print(f"Best Sharpe: {stats['best_sharpe']} (alpha: {stats['best_alpha_id']})")
        print(f"Workers: active={stats['workers']['active']}, idle={stats['workers']['idle']}, failed={stats['workers']['failed']}")
        print(f"Ideas: pending={stats['ideas']['pending']}, in_progress={stats['ideas']['in_progress']}, completed={stats['ideas']['completed']}, failed={stats['ideas']['failed']}")
        print(f"Total processed: {stats['total_processed']}")
        print(f"Submission ready: {stats['total_submission_ready']}")
        print(f"Empty polls: {stats['consecutive_empty_polls']}")
        print(f"Last poll: {stats['last_poll']}")
        print("=" * 50)


# 全局实例
state_manager = StateManager()


if __name__ == "__main__":
    # 测试
    sm = StateManager()
    sm.print_stats()
    sm.save()
