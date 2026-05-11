#!/usr/bin/env python3
"""
Research Assistant Service (独立进程)
持续搜索论坛和QQ邮件，将有用内容沉淀到知识库

用法:
    python3 research_assistant_service.py

或用 cron 每分钟运行:
    * * * * * /home/zxx/wq_env/bin/python /path/to/research_assistant_service.py
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# 添加路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

WQ_FORUM_RAG_SRC = Path("/home/zxx/worldQuant/worldquant_brain/wq_forum_rag/src")
sys.path.insert(0, str(WQ_FORUM_RAG_SRC))

from wq_forum_rag.evolution import EvolutionService

# 配置
KNOWLEDGE_DB_PATH = "/home/zxx/worldQuant/worldquant_brain/data/forum.sqlite3"
STATE_FILE = Path("/tmp/multi_agent/research_state.json")
INTERVAL_MINUTES = 30  # 每30分钟运行一次


class ResearchAssistantService:
    """研究助手服务 - 独立持续运行"""

    def __init__(self):
        self.evo = EvolutionService(KNOWLEDGE_DB_PATH)
        self.logger = Logger()
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """加载状态"""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return {
            'last_run': None,
            'run_count': 0,
            'items_saved': 0,
        }

    def _save_state(self):
        """保存状态"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.state.get('last_run'):
            return True

        last_run = datetime.fromisoformat(self.state['last_run'])
        if datetime.now() - last_run < timedelta(minutes=INTERVAL_MINUTES):
            return False
        return True

    def run(self):
        """执行一次研究"""
        if not self.should_run():
            self.logger.log(f"Skipped: interval not elapsed (runs every {INTERVAL_MINUTES} min)")
            return

        self.logger.log("Research assistant started")
        self.state['run_count'] += 1

        try:
            saved = self._research_loop()
            self.state['items_saved'] += saved
            self.state['last_run'] = datetime.now().isoformat()
            self._save_state()
            self.logger.log(f"Research completed: {saved} items saved")

        except Exception as e:
            self.logger.log(f"Error: {e}")

    def _research_loop(self) -> int:
        """研究循环"""
        # 研究问题列表
        queries = [
            ("fitness_low", "alpha fitness improve reduce turnover"),
            ("turnover_high", "alpha turnover high reduce"),
            ("sharpe_optimization", "alpha sharpe improve optimization"),
            ("submission_ready", "alpha submission ready PPA"),
            ("correlation", "alpha correlation reduce"),
        ]

        saved_count = 0

        for topic, query in queries:
            try:
                result = self.evo.build_evolution_context(query, top_k=5)

                # 处理论坛证据
                for post in result.get('forum_evidence', [])[:2]:
                    topic_id = post.get('topic_id', '')
                    if not topic_id:
                        continue

                    # 检查是否已保存
                    if self._is_already_saved(topic_id):
                        continue

                    slug = f"forum-{topic}-{topic_id}"
                    title = post.get('title', '')[:50]
                    body_text = post.get('body_text', '') or post.get('text', '')
                    summary = body_text[:150] if body_text else ''

                    self.evo.propose_knowledge_page(
                        slug=slug,
                        title=f"论坛发现 [{topic}]: {title}",
                        summary=summary,
                        body=body_text,
                        source_topic_ids=[topic_id],
                        confidence=0.7,
                        auto_publish=True,
                    )
                    saved_count += 1
                    self.logger.log(f"  Saved: {slug}")

            except Exception as e:
                self.logger.log(f"  Error on query '{topic}': {e}")

        return saved_count

    def _is_already_saved(self, topic_id: str) -> bool:
        """检查是否已经保存过"""
        try:
            page = self.evo.get_knowledge_page(f"forum-{topic_id}")
            return page is not None
        except:
            return False


class Logger:
    """日志记录器 (带轮转)"""

    def __init__(self):
        from worldquant_brain.multi_agent.logging_utils import get_logger
        self._logger = get_logger("research_assistant",
                                  str(Path("/tmp/multi_agent/logs") / "research_assistant.log"))

    def log(self, message: str):
        self._logger.info(message)


def main():
    print("=" * 60)
    print("Research Assistant Service (Independent Process)")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)

    service = ResearchAssistantService()

    # 持续运行模式
    while True:
        service.run()
        print(f"Next run in {INTERVAL_MINUTES} minutes...")
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
