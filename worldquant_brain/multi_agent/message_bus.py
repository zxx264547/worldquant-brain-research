#!/usr/bin/env python3
"""
Multi-Agent 消息总线
基于文件事件的通知系统
"""

import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

BASE_DIR = Path("/tmp/multi_agent")
EVENTS_DIR = BASE_DIR / "events"
PROCESSED_DIR = EVENTS_DIR / "processed"


class EventType(Enum):
    # Worker事件
    WORKER_RESULT = "result:new"
    WORKER_BUSY = "worker:busy"
    WORKER_IDLE = "worker:idle"
    WORKER_FAILED = "worker:failed"

    # Idea事件
    IDEA_GENERATED = "idea:generated"
    IDEA_ASSIGNED = "idea:assigned"

    # Alpha事件
    ALPHA_PROMISING = "alpha:promising"
    ALPHA_SUBMISSION_READY = "alpha:submission_ready"
    ALPHA_FAILED = "alpha:failed"

    # 系统事件
    SYSTEM_ERROR = "system:error"
    API_RATE_LIMIT = "system:api_rate_limit"
    TIMEOUT = "system:timeout"


@dataclass
class Event:
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: str = ""
    event_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.event_id:
            self.event_id = f"{self.event_type}_{self.timestamp}_{id(self)}"


class MessageBus:
    """消息总线 - 单例模式"""

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
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        for subdir in ['results', 'ideas', 'workers', 'alpha', 'system']:
            (EVENTS_DIR / subdir).mkdir(exist_ok=True)
            (PROCESSED_DIR / subdir).mkdir(exist_ok=True)

    # ========== 发布事件 ==========

    def publish(self, event: Event):
        """发布事件"""
        with self._lock:
            # 根据事件类型保存到对应目录
            event_type = event.event_type

            # 使用event_id作为文件名
            filename = f"{event.event_id}.json"

            if ':' in event_type:
                category = event_type.split(':')[0]
                # 映射到正确的目录名
                category_map = {
                    'result': 'results',
                    'idea': 'ideas',
                    'worker': 'workers',
                    'alpha': 'alpha',
                    'system': 'system'
                }
                mapped_category = category_map.get(category, category)
                if mapped_category:
                    filepath = EVENTS_DIR / mapped_category / filename
                else:
                    filepath = EVENTS_DIR / filename
            else:
                filepath = EVENTS_DIR / filename

            # 确保目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w') as f:
                json.dump(asdict(event), f, indent=2)

            print(f"[MessageBus] Published: {event.event_type} -> {filepath}")

    def publish_result(self, worker_id: str, idea_id: int, result: dict):
        """发布结果事件"""
        event = Event(
            event_type=EventType.WORKER_RESULT.value,
            source=worker_id,
            data={
                'idea_id': idea_id,
                'result': result,
            }
        )
        self.publish(event)

    def publish_alpha_promising(self, alpha_id: str, sharpe: float, expr: str):
        """发布有潜力alpha事件"""
        event = Event(
            event_type=EventType.ALPHA_PROMISING.value,
            source='team_lead',
            data={
                'alpha_id': alpha_id,
                'sharpe': sharpe,
                'expression': expr,
            }
        )
        self.publish(event)

    def publish_alpha_submission_ready(self, alpha_id: str, sharpe: float, metrics: dict):
        """发布可提交alpha事件"""
        event = Event(
            event_type=EventType.ALPHA_SUBMISSION_READY.value,
            source='team_lead',
            data={
                'alpha_id': alpha_id,
                'sharpe': sharpe,
                'metrics': metrics,
            }
        )
        self.publish(event)

    def publish_api_rate_limit(self, retry_after: int = 60):
        """发布API限速事件"""
        event = Event(
            event_type=EventType.API_RATE_LIMIT.value,
            source='api_client',
            data={'retry_after': retry_after}
        )
        self.publish(event)

    # ========== 订阅事件 ==========

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)

    # ========== 处理事件 ==========

    def get_unprocessed_events(self, category: str = "") -> List[Path]:
        """获取未处理的事件"""
        self._ensure_dirs()

        if category:
            search_dir = EVENTS_DIR / category
        else:
            search_dir = EVENTS_DIR

        events = []
        for filepath in search_dir.glob("**/*.json"):
            # 跳过已处理目录中的文件
            if "processed" in filepath.parts:
                continue
            # 检查是否已处理
            relative = filepath.relative_to(EVENTS_DIR)
            processed_path = PROCESSED_DIR / relative
            if not processed_path.exists():
                events.append(filepath)

        return sorted(events)

    def process_events(self, category: str = "") -> List[Event]:
        """处理未处理的事件"""
        events = []
        for filepath in self.get_unprocessed_events(category):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                event = Event(**data)
                events.append(event)

                # 移动到已处理目录
                self._mark_processed(filepath)

                # 触发订阅回调
                self._notify(event)

            except Exception as e:
                print(f"[MessageBus] Error processing {filepath}: {e}")
                # 移动到已处理避免重复
                self._mark_processed(filepath)

        return events

    def _mark_processed(self, filepath: Path):
        """标记为已处理"""
        try:
            relative = filepath.relative_to(EVENTS_DIR)
            dest = PROCESSED_DIR / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(filepath), str(dest))
        except Exception as e:
            print(f"[MessageBus] Error marking processed {filepath}: {e}")

    def _notify(self, event: Event):
        """通知订阅者"""
        callbacks = self._subscribers.get(event.event_type, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"[MessageBus] Error in callback for {event.event_type}: {e}")

    # ========== 工具方法 ==========

    def clear_old_processed(self, hours: int = 24):
        """清理旧的已处理事件"""
        cutoff = datetime.now().timestamp() - hours * 3600

        for filepath in PROCESSED_DIR.glob("**/*.json"):
            if filepath.stat().st_mtime < cutoff:
                try:
                    filepath.unlink()
                except Exception as e:
                    print(f"[MessageBus] Error deleting {filepath}: {e}")

    def get_event_stats(self) -> dict:
        """获取事件统计"""
        stats = {}
        for subdir in ['results', 'ideas', 'workers', 'alpha', 'system']:
            unprocessed = len(list((EVENTS_DIR / subdir).glob("*.json")))
            processed = len(list((PROCESSED_DIR / subdir).glob("*.json")))
            stats[subdir] = {'unprocessed': unprocessed, 'processed': processed}
        return stats

    def print_stats(self):
        """打印事件统计"""
        stats = self.get_event_stats()
        print("=" * 50)
        print("Message Bus Events")
        print("=" * 50)
        for category, counts in stats.items():
            print(f"  {category}: unprocessed={counts['unprocessed']}, processed={counts['processed']}")
        print("=" * 50)


# 全局实例
message_bus = MessageBus()


if __name__ == "__main__":
    # 测试
    mb = MessageBus()

    # 发布测试事件
    mb.publish_result('worker_1', 101, {'sharpe': 1.04, 'fitness': 1.47})

    # 处理事件
    events = mb.process_events('results')
    print(f"Processed {len(events)} events")

    mb.print_stats()
