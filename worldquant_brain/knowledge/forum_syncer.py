"""论坛知识同步器 — AI主动获取论坛新知识并提炼沉淀

触发方式：不是定时任务，而是AI在认知循环中主动决定何时同步。
典型触发条件：策略停滞 + 距离上次同步>24h
"""
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

from .unified_store import UnifiedKnowledgeStore


class ForumSyncer:
    """论坛知识同步器

    流程：
    1. 检测是否有新的论坛数据文件
    2. 导入新帖子到 forum.sqlite3
    3. 提取知识点（由AI Agent完成提炼）
    4. 写入知识页面
    """

    def __init__(self, project_root: str | Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        self.root = Path(project_root)
        self.store = UnifiedKnowledgeStore(self.root)
        self.forum_db_path = self.root / "worldquant_brain" / "data" / "forum.sqlite3"
        self.raw_posts_path = self.root / "posts_raw.json"
        self.data_dir = self.root / "worldquant_brain" / "data" / "raw"

    def check_new_data(self) -> dict:
        """检查是否有新的论坛数据可导入

        检查点：
        1. posts_raw.json 的修改时间 vs 上次同步时间
        2. data/raw/ 下是否有新的 JSON 文件
        """
        last_sync = self.store._get_last_event_time("forum_sync")
        new_sources = []

        # 检查主数据文件
        if self.raw_posts_path.exists():
            mtime = datetime.fromtimestamp(self.raw_posts_path.stat().st_mtime)
            if last_sync is None or mtime > datetime.fromisoformat(last_sync):
                new_sources.append({
                    "path": str(self.raw_posts_path),
                    "modified": mtime.isoformat(),
                    "type": "posts_raw"
                })

        # 检查 data/raw 目录
        if self.data_dir.exists():
            for f in self.data_dir.glob("*.json"):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if last_sync is None or mtime > datetime.fromisoformat(last_sync):
                    new_sources.append({
                        "path": str(f),
                        "modified": mtime.isoformat(),
                        "type": "data_raw"
                    })

        return {
            "has_new_data": len(new_sources) > 0,
            "new_sources": new_sources,
            "last_sync": last_sync,
            "forum_db_exists": self.forum_db_path.exists()
        }

    def ingest_posts(self, source_path: str = None) -> dict:
        """导入帖子到数据库

        如果 forum.sqlite3 不存在，创建并初始化。
        使用内容哈希做增量更新（跳过已存在的帖子）。
        """
        source = Path(source_path) if source_path else self.raw_posts_path
        if not source.exists():
            return {"status": "error", "message": f"数据源不存在: {source}"}

        posts = json.loads(source.read_text())
        if isinstance(posts, dict):
            # posts_categorized.json 格式
            all_posts = []
            for category, data in posts.items():
                for topic in data.get("topics", []):
                    topic["category"] = category
                    all_posts.append(topic)
            posts = all_posts

        # 确保数据库和表存在
        self._ensure_forum_tables()

        new_count = 0
        skip_count = 0

        conn = sqlite3.connect(str(self.forum_db_path))
        for post in posts:
            content = post.get("content", post.get("summary", ""))
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            existing = conn.execute(
                "SELECT id FROM forum_posts WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()

            if existing:
                skip_count += 1
                continue

            conn.execute("""
                INSERT INTO forum_posts (post_id, subject, author, date_str, content, content_hash, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                post.get("id", ""),
                post.get("subject", post.get("title", "")),
                post.get("author", ""),
                post.get("date", ""),
                content,
                content_hash,
                post.get("category", ""),
            ))
            new_count += 1

        conn.commit()
        conn.close()

        # 记录同步事件
        self.store.record_forum_sync(new_count, 0)

        return {
            "status": "success",
            "new_posts": new_count,
            "skipped": skip_count,
            "total_in_source": len(posts)
        }

    def get_unprocessed_posts(self, limit: int = 20) -> list[dict]:
        """获取尚未提炼为知识的帖子（供AI阅读和提炼）"""
        if not self.forum_db_path.exists():
            return []

        conn = sqlite3.connect(str(self.forum_db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM forum_posts
            WHERE processed = 0
            ORDER BY rowid DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()

        return [dict(r) for r in rows]

    def mark_processed(self, post_ids: list[str]):
        """标记帖子为已处理"""
        if not self.forum_db_path.exists():
            return

        conn = sqlite3.connect(str(self.forum_db_path))
        for pid in post_ids:
            conn.execute(
                "UPDATE forum_posts SET processed = 1 WHERE post_id = ?",
                (pid,))
        conn.commit()
        conn.close()

    def deposit_knowledge(self, title: str, summary: str, source_post_ids: list[str],
                          confidence: float = 0.7) -> int:
        """将AI提炼的知识沉淀为知识事件

        这是AI在阅读论坛帖子后调用的方法：
        1. AI阅读 get_unprocessed_posts() 返回的帖子
        2. AI提炼出可操作的insight
        3. 调用此方法存储
        4. 标记帖子为已处理
        """
        event_id = self.store.record_insight(
            insight=f"[{title}] {summary}",
            source="forum_extraction",
            confidence=confidence,
            metadata={
                "title": title,
                "source_posts": source_post_ids,
                "extraction_time": datetime.now().isoformat()
            }
        )
        self.mark_processed(source_post_ids)
        return event_id

    def sync(self) -> dict:
        """完整同步流程（不包含AI提炼步骤）

        Returns:
            同步状态，包含需要AI处理的待处理帖子数
        """
        # Step 1: 检查新数据
        check = self.check_new_data()
        if not check["has_new_data"]:
            return {"status": "no_new_data", "message": "没有新的论坛数据"}

        # Step 2: 导入
        total_new = 0
        for source in check["new_sources"]:
            result = self.ingest_posts(source["path"])
            total_new += result.get("new_posts", 0)

        # Step 3: 返回待处理数
        unprocessed = self.get_unprocessed_posts(limit=1)
        unprocessed_count = len(unprocessed)

        return {
            "status": "synced",
            "new_posts_imported": total_new,
            "unprocessed_count": unprocessed_count,
            "message": f"导入{total_new}条新帖子，{unprocessed_count}条待AI提炼"
        }

    def _ensure_forum_tables(self):
        """确保论坛帖子表存在"""
        self.forum_db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.forum_db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS forum_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT,
                subject TEXT,
                author TEXT,
                date_str TEXT,
                content TEXT,
                content_hash TEXT UNIQUE,
                category TEXT DEFAULT '',
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_hash ON forum_posts(content_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_processed ON forum_posts(processed)")
        conn.commit()
        conn.close()
