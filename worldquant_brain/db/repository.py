"""数据访问层 — SQLite操作封装"""
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "brain.db"


def get_db_path() -> str:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return str(DB_PATH)


@contextmanager
def get_conn():
    """获取数据库连接 (自动提交/关闭)"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库: 执行schema.sql"""
    schema_path = Path(__file__).parent / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema_path.read_text())
    print(f"[DB] 数据库初始化完成: {get_db_path()}")


def hash_expression(expression: str) -> str:
    return hashlib.sha256(expression.encode()).hexdigest()[:16]


# ─── Alpha CRUD ───

def save_alpha(alpha: dict) -> bool:
    """保存alpha结果 (自动去重)"""
    expr_hash = hash_expression(alpha['expression'])
    with get_conn() as conn:
        try:
            conn.execute("""INSERT INTO alphas (id, expression, expression_hash,
                sharpe, fitness, ppc, margin, turnover, settings_json, name,
                combo_type, base_alpha, tech_signal, weight, status, error_message, is_submittable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                alpha.get('alpha_id', ''),
                alpha['expression'],
                expr_hash,
                alpha.get('sharpe', 0),
                alpha.get('fitness', 0),
                alpha.get('ppc', 0),
                alpha.get('margin', 0),
                alpha.get('turnover', 0),
                json.dumps(alpha.get('settings', {})),
                alpha.get('name', ''),
                alpha.get('combo_type', ''),
                alpha.get('base_alpha', ''),
                alpha.get('tech_signal', ''),
                alpha.get('weight'),
                alpha.get('status', 'done'),
                alpha.get('error_message'),
                1 if alpha.get('sharpe', 0) >= 1.58 else 0
            ))
            return True
        except sqlite3.IntegrityError:
            return False  # 重复, 跳过


def find_by_hash(expr_hash: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM alphas WHERE expression_hash = ?", (expr_hash,)
        ).fetchone()
        return dict(row) if row else None


def find_by_expression(expression: str) -> Optional[dict]:
    h = hash_expression(expression)
    return find_by_hash(h)


def get_best_alphas(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alphas WHERE status='done' ORDER BY sharpe DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_submittable() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alphas WHERE is_submittable = 1"
        ).fetchall()
        return [dict(r) for r in rows]


def get_alphas_by_combo(combo_type: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alphas WHERE combo_type = ? ORDER BY sharpe DESC",
            (combo_type,)
        ).fetchall()
        return [dict(r) for r in rows]


def count_alphas() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM alphas").fetchone()[0]


# ─── Task CRUD ───

def push_task(strategy: str, expression: str, settings: dict = None,
              priority: int = 0) -> int:
    expr_hash = hash_expression(expression)
    with get_conn() as conn:
        cur = conn.execute("""INSERT INTO tasks (strategy, expression, expression_hash,
            settings_json, priority) VALUES (?, ?, ?, ?, ?)""",
            (strategy, expression, expr_hash, json.dumps(settings or {}), priority))
        return cur.lastrowid


def pop_task(worker_id: str) -> Optional[dict]:
    """原子出队: 领取优先级最高的待处理任务"""
    with get_conn() as conn:
        row = conn.execute("""SELECT id FROM tasks WHERE status='queued'
            ORDER BY priority DESC, id ASC LIMIT 1""").fetchone()
        if not row:
            return None
        task_id = row[0]
        conn.execute("""UPDATE tasks SET status='running', worker_id=?,
            updated_at=datetime('now') WHERE id=?""", (worker_id, task_id))
        conn.execute("""UPDATE workers SET status='busy', current_task_id=?,
            last_heartbeat=datetime('now') WHERE id=?""", (task_id, worker_id))
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(task) if task else None


def complete_task(task_id: int, alpha_id: str, sharpe: float, success: bool = True,
                  error: str = None):
    with get_conn() as conn:
        status = 'done' if success else 'failed'
        conn.execute("""UPDATE tasks SET status=?, alpha_id=?, sharpe=?,
            error_message=?, updated_at=datetime('now') WHERE id=?""",
            (status, alpha_id, sharpe, error, task_id))
        # 更新worker状态
        conn.execute("""UPDATE workers SET status='idle', current_task_id=NULL,
            last_heartbeat=datetime('now'),
            tasks_completed = tasks_completed + CASE WHEN ? THEN 1 ELSE 0 END,
            tasks_failed = tasks_failed + CASE WHEN ? THEN 0 ELSE 1 END
            WHERE current_task_id = ?""", (success, success, task_id))


def get_pending_count() -> int:
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0]


# ─── Worker CRUD ───

def register_worker(worker_id: str):
    with get_conn() as conn:
        conn.execute("""INSERT OR IGNORE INTO workers (id)
            VALUES (?)""", (worker_id,))


def heartbeat_worker(worker_id: str):
    with get_conn() as conn:
        conn.execute("""UPDATE workers SET last_heartbeat=datetime('now')
            WHERE id=?""", (worker_id,))


def get_idle_workers() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workers WHERE status='idle'").fetchall()
        return [dict(r) for r in rows]


# ─── Experiment CRUD ───

def start_experiment(name: str, strategy: str, config: dict = None) -> int:
    with get_conn() as conn:
        cur = conn.execute("""INSERT INTO experiments (name, strategy, config_json)
            VALUES (?, ?, ?)""", (name, strategy, json.dumps(config or {})))
        return cur.lastrowid


def finish_experiment(exp_id: int, best_sharpe: float):
    with get_conn() as conn:
        conn.execute("""UPDATE experiments SET status='done', best_sharpe=?,
            finished_at=datetime('now') WHERE id=?""", (best_sharpe, exp_id))


# ─── Migration ───

def migrate_json_results(json_dir: str = "/tmp/multi_agent"):
    """迁移历史JSON结果到SQLite"""
    import glob
    count = 0
    for f in glob.glob(f"{json_dir}/*_results.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            for r in data.get('results', []):
                if r.get('status') != 'ok':
                    continue
                alpha = {
                    'alpha_id': r.get('alpha_id', ''),
                    'expression': r.get('expression', ''),
                    'sharpe': r.get('sharpe', 0),
                    'fitness': r.get('fitness', 0),
                    'ppc': r.get('ppc', 0),
                    'margin': r.get('margin', 0),
                    'turnover': r.get('turnover', 0),
                    'name': r.get('name', ''),
                    'status': 'done',
                }
                if save_alpha(alpha):
                    count += 1
        except Exception:
            pass
    print(f"[DB] 迁移完成: {count} 条结果入库")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        init_db()
        migrate_json_results()
        print(f"[DB] 总Alpha数: {count_alphas()}")
        print("[DB] Top 5:")
        for a in get_best_alphas(5):
            print(f"  {a['name']}: Sharpe={a['sharpe']:.3f} Fitness={a['fitness']:.3f}")
    else:
        init_db()
