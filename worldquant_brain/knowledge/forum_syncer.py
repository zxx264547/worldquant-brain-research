"""论坛知识同步器 — 通过 Selenium 抓取新帖子，更新 forum.sqlite3"""

import json, sqlite3, sys, os, asyncio
from pathlib import Path
from datetime import datetime

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)


class ForumSyncer:
    """论坛同步器 — 支持JSON导入和实时抓取"""
    def __init__(self, project_root=None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.root = Path(project_root)
        self.db = get_forum_db()

    def sync_json(self, path):
        return sync_from_raw_json(self.db, path)

    def sync_live(self, max_new=10):
        return asyncio.run(sync_live(headless=False, max_new=max_new))

    def stats(self):
        return self.db.execute("SELECT COUNT(*) FROM topics").fetchone()[0]


def get_forum_db():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "forum.sqlite3"
    return sqlite3.connect(str(db_path))


def get_existing_topics(db):
    """获取已存在的帖子 ID 集合"""
    try:
        rows = db.execute("SELECT topic_id FROM topics").fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        return set()


def insert_topic(db, topic_id, title, body, community_id="", community_title="", url=""):
    """插入或更新 topic"""
    import hashlib
    db.execute("""
        INSERT OR REPLACE INTO topics
        (topic_id, community_id, community_title, title, body_text, url, created_at, author, vote_num, comment_count, comments_json, content_hash)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), '', 0, 0, '[]', ?)
    """, (topic_id, community_id or "", community_title or "", title or "", body or "", url or "",
          hashlib.md5((body or "").encode()).hexdigest()[:12]))
    db.commit()


def sync_from_raw_json(db, json_path):
    """从 JSON 文件导入帖子（本地备份方式）"""
    if not os.path.exists(json_path):
        return 0
    with open(json_path) as f:
        posts = json.load(f)
    if isinstance(posts, dict):
        posts = list(posts.values()) if "posts" in posts else [posts]
    existing = get_existing_topics(db)
    new_count = 0
    for post in posts:
        tid = str(post.get("id", post.get("article_id", "")))
        if not tid or tid in existing:
            continue
        insert_topic(db, tid,
                     post.get("title", ""),
                     post.get("body", post.get("content", "")),
                     post.get("community_id", ""),
                     post.get("community", ""),
                     post.get("url", ""))
        existing.add(tid)
        new_count += 1
    return new_count


async def sync_live(headless=True, max_new=20):
    """通过 Selenium 抓取最新帖子（实时方式）"""
    try:
        from platform_functions import BrainApiClient
    except ImportError:
        print("platform_functions 不可用")
        return []

    config_path = Path(__file__).parent.parent / "config" / "user_config.json"
    if not config_path.exists():
        print("user_config.json 不存在")
        return []

    with open(config_path) as f:
        cfg = json.load(f)
    creds = cfg.get("credentials", cfg)

    client = BrainApiClient()
    await client.authenticate(creds["email"], creds["password"])

    db = get_forum_db()
    existing = get_existing_topics(db)
    new_posts = []

    # 搜索最近的 posts
    queries = ["sharpe", "alpha", "因子", "提交", "prod", "vec"]
    for q in queries:
        try:
            result = await client.search_forum_posts(
                creds["email"], creds["password"], q,
                max_results=5, headless=headless
            )
            if isinstance(result, dict) and "posts" in result:
                posts = result["posts"]
            elif isinstance(result, list):
                posts = result
            else:
                continue

            for post in posts:
                tid = str(post.get("id", post.get("article_id", "")))
                if not tid or tid in existing:
                    continue
                insert_topic(db, tid,
                             post.get("title", ""),
                             post.get("body", post.get("content", "")),
                             post.get("community_id", ""),
                             post.get("community", ""),
                             post.get("url", ""))
                existing.add(tid)
                new_posts.append({"id": tid, "title": post.get("title", "")[:80]})
                if len(new_posts) >= max_new:
                    break
        except Exception as e:
            print(f"  搜索 '{q}' 失败: {e}")
            continue

        if len(new_posts) >= max_new:
            break

    return new_posts


# ===== CLI =====
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python forum_syncer.py sync-json <file.json>  # 从JSON导入")
        print("  python forum_syncer.py sync-live              # 实时抓取新帖")
        print("  python forum_syncer.py stats                  # 查看统计")
        sys.exit(0)

    cmd = sys.argv[1]
    db = get_forum_db()

    if cmd == "sync-json":
        path = sys.argv[2]
        n = sync_from_raw_json(db, path)
        print(f"导入 {n} 篇新帖子")

    elif cmd == "sync-live":
        n = asyncio.run(sync_live(headless=False, max_new=10))
        print(f"抓取 {len(n)} 篇新帖子")
        for p in n:
            print(f"  {p['id']}: {p['title']}")

    elif cmd == "stats":
        count = db.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        print(f"总帖子: {count}")
        recent = db.execute("SELECT topic_id, title FROM topics ORDER BY CAST(topic_id AS INTEGER) DESC LIMIT 5").fetchall()
        for r in recent:
            print(f"  {r[0]}: {r[1][:80] if r[1] else '(untitled)'}")
