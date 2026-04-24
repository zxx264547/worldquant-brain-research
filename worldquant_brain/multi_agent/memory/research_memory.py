"""
研究记忆模块
避免重复回测相同的idea，反思之前的迭代
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class IdeaRecord:
    """已探索的Idea记录"""
    idea_id: str
    expression: str
    stage: str  # 0-op, 1-op, 2-op
    result: Optional[str]  # success, failed, timeout
    sharpe: Optional[float]
    fitness: Optional[float]
    ppc: Optional[float]
    explored_at: str
    explored_by: str  # worker_id


class ResearchMemory:
    """研究记忆系统"""

    def __init__(self, memory_file: str = "/tmp/multi_agent/memory.json"):
        self.memory_file = Path(memory_file)
        self.ideas: Dict[str, IdeaRecord] = {}
        self.load()

    def load(self):
        """加载记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    for item in data.get('ideas', []):
                        self.ideas[item['idea_id']] = IdeaRecord(**item)
            except Exception as e:
                print(f"加载记忆失败: {e}")

    def save(self):
        """保存记忆"""
        data = {
            "last_updated": datetime.now().isoformat(),
            "ideas": [asdict(r) for r in self.ideas.values()]
        }
        with open(self.memory_file, 'w') as f:
            json.dump(data, f, indent=2)

    def remember(self, record: IdeaRecord):
        """记录已探索的idea"""
        self.ideas[record.idea_id] = record
        self.save()

    def is_explored(self, idea_id: str) -> bool:
        """检查是否已探索"""
        return idea_id in self.ideas

    def get_similar_explored(self, expression: str, stage: str) -> Optional[IdeaRecord]:
        """查找相似的已探索idea"""
        for record in self.ideas.values():
            if record.stage == stage and expression in record.expression:
                return record
        return None

    def reflect(self, worker_id: str) -> List[str]:
        """反思之前做过的事，返回建议的下一轮迭代方向"""
        worker_records = [r for r in self.ideas.values() if r.explored_by == worker_id]

        if not worker_records:
            return []

        suggestions = []

        # 统计各stage成功率
        stage_stats = {}
        for r in worker_records:
            if r.stage not in stage_stats:
                stage_stats[r.stage] = {'success': 0, 'failed': 0}
            if r.result == 'success':
                stage_stats[r.stage]['success'] += 1
            elif r.result == 'failed':
                stage_stats[r.stage]['failed'] += 1

        # 生成建议
        for stage, stats in stage_stats.items():
            if stats['failed'] > stats['success']:
                suggestions.append(f"{stage}阶段失败率高，考虑改变策略")

        return suggestions

    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.ideas)
        if total == 0:
            return {"total": 0}

        success = sum(1 for r in self.ideas.values() if r.result == 'success')
        return {
            "total": total,
            "success": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0
        }


async def main():
    """测试记忆模块"""
    memory = ResearchMemory()

    # 模拟记录
    record = IdeaRecord(
        idea_id="test_1",
        expression="rank(actual_eps_value_quarterly)",
        stage="0-op",
        result="success",
        sharpe=0.85,
        fitness=1.2,
        ppc=0.15,
        explored_at=datetime.now().isoformat(),
        explored_by="worker_1"
    )

    memory.remember(record)
    print(f"记录: {memory.is_explored('test_1')}")
    print(f"统计: {memory.get_stats()}")
    print(f"反思: {memory.reflect('worker_1')}")


if __name__ == "__main__":
    asyncio.run(main())
