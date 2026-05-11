#!/usr/bin/env python3
"""
Multi-Agent Team Lead 服务 (Cron模式)
每30秒被Cron唤醒，检查状态，分发任务，协调各Worker

用法:
    */30 * * * * /home/zxx/wq_env/bin/python /path/to/team_lead_service.py
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from worldquant_brain.multi_agent.state_manager import StateManager, state_manager
from worldquant_brain.multi_agent.message_bus import MessageBus, message_bus, Event, EventType

# 共享存储路径
BASE_DIR = Path("/tmp/multi_agent")
IDEAS_FILE = BASE_DIR / "ideas.json"
RESULTS_FILE = BASE_DIR / "results.json"
CONFIG_FILE = BASE_DIR / "configs" / "team_lead.json"

# 知识库路径
KNOWLEDGE_DB_PATH = Path("/home/zxx/worldQuant/worldquant_brain/data/forum.sqlite3")

# 添加 wq_forum_rag 路径
WQ_FORUM_RAG_SRC = Path("/home/zxx/worldQuant/worldquant_brain/wq_forum_rag/src")
if str(WQ_FORUM_RAG_SRC) not in sys.path:
    sys.path.insert(0, str(WQ_FORUM_RAG_SRC))


class TeamLeadService:
    """Team Lead 服务"""

    def __init__(self):
        self.state_mgr = StateManager()
        self.msg_bus = MessageBus()
        self.config = self._load_config()
        self.logger = Logger()

    def _ensure_research_assistant_running(self):
        """确保 research_assistant 在运行"""
        import subprocess
        import os

        # 检查进程是否在运行
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'research_assistant_service'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # 进程已在运行
                return

            # 进程不在运行，启动它
            script_path = Path(__file__).parent / "research_assistant_service.py"
            log_file = Path("/tmp/multi_agent/logs/research_assistant.log")

            # 启动为后台进程
            with open(log_file, 'a') as f:
                subprocess.Popen(
                    ['/home/zxx/wq_env/bin/python', str(script_path)],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(script_path.parent)
                )
            self.logger.log("Started research_assistant_service")

        except Exception as e:
            self.logger.log(f"Error starting research_assistant: {e}")

    def _load_config(self) -> dict:
        """加载配置"""
        default_config = {
            'target_sharpe': 1.58,
            'min_sharpe_for_deep': 1.0,
            'max_idle_ideas': 16,
            'poll_interval': 30,
            'timeout_seconds': 900,
        }
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                # 合并配置
                default_config.update(user_config)
        return default_config

    def run(self):
        """主运行循环"""
        self.logger.log("Team Lead Service started")

        # 0. 确保 research_assistant 在运行
        self._ensure_research_assistant_running()

        # 1. 处理新事件
        self._process_events()

        # 2. 处理新结果
        new_results = self._process_results()

        # 3. 记录poll
        self.state_mgr.record_poll(len(new_results) > 0)

        # 4. 动态任务分配
        self._assign_tasks()

        # 5. 检查是否需要生成新ideas
        self._check_generate_ideas()

        # 6. 决策
        self._make_decisions()

        # 7. 保存状态
        self.state_mgr.save()

        # 8. 输出状态
        self.state_mgr.print_stats()
        self.logger.log("Team Lead Service finished")

    def _process_events(self):
        """处理新事件"""
        events = self.msg_bus.process_events()

        for event in events:
            event_type = event.event_type
            source = event.source
            data = event.data

            if event_type == EventType.WORKER_RESULT.value:
                # Worker返回结果
                idea_id = data.get('idea_id')
                result = data.get('result', {})
                self._handle_worker_result(source, idea_id, result)

            elif event_type == EventType.WORKER_BUSY.value:
                self.state_mgr.set_worker_busy(source, data.get('ideas', []))

            elif event_type == EventType.WORKER_IDLE.value:
                self.state_mgr.set_worker_idle(source)

            elif event_type == EventType.API_RATE_LIMIT.value:
                retry_after = data.get('retry_after', 60)
                self.logger.log(f"API rate limit, retry after {retry_after}s")

    def _process_results(self) -> List[dict]:
        """处理results.json中的新结果"""
        try:
            if not RESULTS_FILE.exists():
                return []

            with open(RESULTS_FILE, 'r') as f:
                data = json.load(f)

            results = data.get('results', [])
            new_results = []

            for result in results:
                alpha_id = result.get('alpha_id')
                sharpe = result.get('sharpe', 0)

                # 检查是否是新的best
                if sharpe > self.state_mgr.state.best_sharpe:
                    self.state_mgr.update_best_sharpe(sharpe, alpha_id)

                # 检查是否可提交
                if self._is_submission_ready(result):
                    self.state_mgr.increment_submission_ready()
                    self.msg_bus.publish_alpha_submission_ready(
                        alpha_id, sharpe, result
                    )
                    self.logger.log(f"ALPHA SUBMISSION READY: {alpha_id} Sharpe={sharpe}")
                    self._log_alpha_experience(result, confidence=0.95, tag='submission-ready')

                # 检查是否有潜力深度优化
                elif sharpe >= self.config['min_sharpe_for_deep']:
                    self.msg_bus.publish_alpha_promising(alpha_id, sharpe, result.get('code', ''))
                    self._log_alpha_experience(result, confidence=0.80, tag='promising')

                new_results.append(result)

            return new_results

        except Exception as e:
            self.logger.log(f"Error processing results: {e}")
            return []

    def _handle_worker_result(self, worker_id: str, idea_id: int, result: dict):
        """处理Worker返回的结果"""
        sharpe = result.get('sharpe', 0)

        # 更新状态
        self.state_mgr.set_idea_completed(idea_id)
        self.state_mgr.set_worker_idle(worker_id)
        self.state_mgr.increment_processed()

        if sharpe > self.state_mgr.state.best_sharpe:
            self.state_mgr.update_best_sharpe(sharpe, result.get('alpha_id', ''))

        self.logger.log(f"Worker {worker_id} completed idea {idea_id}: Sharpe={sharpe}")

    def _assign_tasks(self):
        """动态分配任务给idle workers"""
        idle_workers = self.state_mgr.get_idle_workers()
        if not idle_workers:
            self.logger.log("No idle workers")
            return

        # 加载ideas
        pending_ideas = self._get_pending_ideas()
        if not pending_ideas:
            self.logger.log("No pending ideas")
            return

        # 分配任务
        for worker_id in idle_workers:
            if not pending_ideas:
                break

            idea = pending_ideas.pop(0)
            self._assign_idea_to_worker(worker_id, idea)

        # 保存更新后的ideas
        self._save_ideas(pending_ideas)

    def _get_pending_ideas(self) -> List[dict]:
        """获取待处理的ideas"""
        try:
            if not IDEAS_FILE.exists():
                return []

            with open(IDEAS_FILE, 'r') as f:
                data = json.load(f)

            ideas = data.get('ideas', [])

            # 过滤出pending且应该重新分配的
            pending = []
            for idea in ideas:
                idea_id = idea.get('id')
                if self.state_mgr.should_reassign(idea_id):
                    pending.append(idea)

            return pending

        except Exception as e:
            self.logger.log(f"Error loading ideas: {e}")
            return []

    def _assign_idea_to_worker(self, worker_id: str, idea: dict):
        """分配idea给worker"""
        idea_id = idea.get('id')

        # 更新state
        self.state_mgr.set_worker_busy(worker_id, [idea_id])
        self.state_mgr.set_idea_in_progress(idea_id, worker_id)

        # 发布分配事件
        self.msg_bus.publish(Event(
            event_type=EventType.IDEA_ASSIGNED.value,
            source='team_lead',
            data={
                'worker_id': worker_id,
                'idea_id': idea_id,
                'idea': idea,
            }
        ))

        self.logger.log(f"Assigned idea {idea_id} to {worker_id}")

    def _save_ideas(self, pending_ideas: List[dict]):
        """保存更新后的ideas列表 - 保留in_progress和pending的ideas"""
        try:
            # 重新加载完整数据
            with open(IDEAS_FILE, 'r') as f:
                data = json.load(f)

            existing_ideas = data.get('ideas', [])

            # 获取当前in_progress和pending的idea IDs
            active_ids = set()
            for idea_id, status in self.state_mgr.state.ideas_status.items():
                if status.status in ('in_progress', 'pending'):
                    active_ids.add(idea_id)

            # 过滤出保留的ideas (in_progress + pending)
            kept_ideas = [idea for idea in existing_ideas if idea.get('id') in active_ids]

            # 合并新pending ideas (避免重复)
            existing_ids = set(idea.get('id') for idea in kept_ideas)
            for idea in pending_ideas:
                if idea.get('id') not in existing_ids:
                    kept_ideas.append(idea)

            data['ideas'] = kept_ideas
            data['last_updated'] = datetime.now().isoformat()

            with open(IDEAS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.log(f"Error saving ideas: {e}")

    def _check_generate_ideas(self):
        """检查是否需要生成新ideas"""
        pending = self.state_mgr.get_pending_ideas()
        in_progress = self.state_mgr.get_in_progress_ideas()

        total = len(pending) + len(in_progress)

        if total < self.config['max_idle_ideas']:
            self.logger.log(f"Low ideas queue ({total}), generating more")
            self.msg_bus.publish(Event(
                event_type=EventType.IDEA_GENERATED.value,
                source='team_lead',
                data={'count': self.config['max_idle_ideas'] - total}
            ))

    def _make_decisions(self):
        """做决策"""
        stats = self.state_mgr.get_stats()

        # 检查是否连续多次poll没有新结果
        if stats['consecutive_empty_polls'] >= 3:
            self.logger.log("WARNING: 3+ consecutive empty polls, may need intervention")

        # 更新phase
        phase = 'monitoring'
        if stats['ideas']['in_progress'] > 0:
            phase = 'distributing'
        elif stats['ideas']['pending'] > 0:
            phase = 'monitoring'
        elif self.state_mgr.state.total_submission_ready > 0:
            phase = 'optimizing'

        self.state_mgr.update_phase(phase)

    def _is_submission_ready(self, result: dict) -> bool:
        """检查alpha是否满足提交条件"""
        sharpe = result.get('sharpe', 0)
        fitness = result.get('fitness', 0)
        margin = result.get('margin', 0)
        turnover = result.get('turnover', 0)
        ppc = result.get('ppc', 1)

        return (
            sharpe >= self.config['target_sharpe'] and
            fitness > 0.5 and
            ppc < 0.5 and
            margin > turnover
        )

    def _get_idea_by_id(self, idea_id: int) -> Optional[dict]:
        """根据idea_id获取idea详情"""
        try:
            if not IDEAS_FILE.exists():
                return None
            with open(IDEAS_FILE, 'r') as f:
                data = json.load(f)
            ideas = data.get('ideas', [])
            for idea in ideas:
                if idea.get('id') == idea_id:
                    return idea
            return None
        except Exception:
            return None

    def _log_alpha_experience(self, result: dict, confidence: float, tag: str):
        """将 alpha 配置和性能沉淀到知识库"""
        try:
            from wq_forum_rag.evolution import EvolutionService

            idea_id = result.get('idea_id')
            idea = self._get_idea_by_id(idea_id) if idea_id else None

            evo = EvolutionService(str(KNOWLEDGE_DB_PATH))

            slug = f"alpha-{tag}-{idea_id}" if idea_id else f"alpha-{tag}-{result.get('alpha_id', 'unknown')}"

            # 从 idea 或 result 中提取信息
            dataset = idea.get('dataset', 'N/A') if idea else result.get('dataset', 'N/A')
            field = idea.get('field', 'N/A') if idea else result.get('field', 'N/A')
            operator = idea.get('operator', 'N/A') if idea else result.get('operator', 'N/A')
            window = idea.get('window', 'N/A') if idea else result.get('window', 'N/A')

            body = f"""## Alpha配置

- 数据集: {dataset}
- 字段: {field}
- 算子: {operator}
- 窗口: {window}

## 性能指标

| 指标 | 值 |
|------|-----|
| Sharpe | {result.get('sharpe', 0):.3f} |
| Fitness | {result.get('fitness', 0):.3f} |
| Turnover | {result.get('turnover', 0):.3f} |
| Margin | {result.get('margin', 0):.3f} |
| PPC | {result.get('ppc', 0):.3f} |

## 表达式

```
{result.get('expression', 'N/A')}
```
"""

            evo.propose_knowledge_page(
                slug=slug,
                title=f"Alpha经验 [{tag}]: {dataset} + {operator}",
                summary=f"Sharpe={result.get('sharpe', 0):.2f}, Fitness={result.get('fitness', 0):.2f}",
                body=body,
                source_topic_ids=[],
                confidence=confidence,
                auto_publish=True,
            )
            self.logger.log(f"Experience logged: {slug}")

        except Exception as e:
            self.logger.log(f"Error logging experience: {e}")

    def _trigger_research(self):
        """触发 research-assistant 搜索论坛并沉淀知识"""
        try:
            from wq_forum_rag.evolution import EvolutionService
            from datetime import datetime, timedelta

            # 检查触发频率
            research_interval = self.config.get('research_interval_hours', 1)
            last_research = self.state_mgr.state.__dict__.get('last_research_time')
            if last_research:
                last_time = datetime.fromisoformat(last_research)
                if datetime.now() - last_time < timedelta(hours=research_interval):
                    self.logger.log(f"Research skipped: interval not elapsed")
                    return

            self.logger.log("Starting research: searching forum and emails...")

            evo = EvolutionService(str(KNOWLEDGE_DB_PATH))

            # 搜索当前研究问题的解决方案
            queries = [
                "alpha fitness improve",
                "turnover high reduce",
                "sharpe optimization",
            ]

            saved_count = 0
            for query in queries:
                result = evo.build_evolution_context(query, top_k=3)

                # 将有用的论坛帖子沉淀到知识库
                for post in result.get('forum_evidence', [])[:2]:
                    topic_id = post.get('topic_id', '')
                    if not topic_id:
                        continue

                    slug = f"research-{topic_id}"
                    title = post.get('title', '')[:50]
                    body_text = post.get('body_text', '')
                    summary = body_text[:100] if body_text else ''

                    evo.propose_knowledge_page(
                        slug=slug,
                        title=f"论坛发现: {title}",
                        summary=summary,
                        body=body_text,
                        source_topic_ids=[topic_id],
                        confidence=0.7,
                        auto_publish=True,
                    )
                    saved_count += 1

            # 更新最后研究时间
            if hasattr(self.state_mgr.state, 'last_research_time'):
                self.state_mgr.state.last_research_time = datetime.now().isoformat()

            self.logger.log(f"Research completed: {saved_count} items saved to knowledge base")

        except Exception as e:
            self.logger.log(f"Error in research: {e}")


class Logger:
    """日志记录器 (带轮转)"""

    def __init__(self):
        from worldquant_brain.multi_agent.logging_utils import get_logger
        self._logger = get_logger("team_lead",
                                  str(BASE_DIR / "logs" / "team_lead.log"))

    def log(self, message: str):
        """记录日志"""
        self._logger.info(message)


def main():
    """主入口"""
    print("=" * 60)
    print("Team Lead Service (Cron Mode)")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)

    try:
        service = TeamLeadService()
        service.run()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
