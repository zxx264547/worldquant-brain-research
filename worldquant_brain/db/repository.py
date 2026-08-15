"""数据访问层 — JSON文件操作封装（替代原SQLite后端）

保持所有函数签名与原SQLite版本完全一致，上游模块零改动。
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

from worldquant_brain.db.json_store import (
    alphas_store, experiments_store, datasets_store,
    valid_fields_store, tasks_store, workers_store,
    ensure_state_dir, STATE_DIR, RUNTIME_DIR,
)

# ─── Alpha 持久化状态语义 ───
# 历史遗留：部分旧数据写入 status='ok'（结果状态语义），
# 持久化层统一用 'done' 表示"已完成回测并入库"。
# 读取端必须兼容两种值，写入端统一归一化为 STATUS_DONE。
STATUS_DONE = "done"
STATUS_OK = "ok"
DONE_STATUSES = (STATUS_DONE, STATUS_OK)

# 任务状态
TASK_QUEUED = "queued"
TASK_RUNNING = "running"
TASK_DONE = "done"
TASK_FAILED = "failed"


def get_db_path() -> str:
    """兼容旧接口 — 返回 state 目录路径"""
    ensure_state_dir()
    return str(STATE_DIR)


def init_db():
    """初始化状态文件（幂等）"""
    ensure_state_dir()
    print(f"[State] 状态目录初始化完成: {STATE_DIR}")


# ─── Hash 工具 ───

def hash_expression(expression: str) -> str:
    return hashlib.sha256(expression.encode()).hexdigest()[:16]


def hash_alpha(expression: str, settings: dict = None) -> str:
    """表达式+关键设置联合哈希，避免不同neutralization/decay等被误判为重复"""
    parts = [expression]
    if settings:
        for k in sorted(['neutralization', 'decay', 'truncation', 'region', 'universe', 'delay']):
            v = settings.get(k)
            if v is not None:
                parts.append(f"{k}={v}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


# ─── Alpha CRUD ───

def save_alpha(alpha: dict) -> bool:
    """保存alpha结果 (自动去重，含settings)"""
    settings = alpha.get('settings_json')
    if isinstance(settings, str):
        try:
            settings = json.loads(settings)
        except Exception:
            settings = alpha.get('settings', {})
    elif isinstance(settings, dict):
        pass
    else:
        settings = alpha.get('settings', {})
    expr_hash = hash_alpha(alpha['expression'], settings)

    data = alphas_store.load()
    if expr_hash in data["entries"]:
        return False

    data["entries"][expr_hash] = {
        "id": alpha.get('alpha_id', ''),
        "expression": alpha['expression'],
        "expression_hash": expr_hash,
        "sharpe": alpha.get('sharpe', 0),
        "fitness": alpha.get('fitness', 0),
        "ppc": alpha.get('ppc', 0),
        "margin": alpha.get('margin', 0),
        "turnover": alpha.get('turnover', 0),
        "settings_json": json.dumps(alpha.get('settings', {})),
        "name": alpha.get('name', ''),
        "combo_type": alpha.get('combo_type', ''),
        "base_alpha": alpha.get('base_alpha', ''),
        "tech_signal": alpha.get('tech_signal', ''),
        "weight": alpha.get('weight'),
        # 持久化状态统一为 'done'（历史数据可能是 'ok'，读取端兼容）
        "status": STATUS_DONE if alpha.get('status', STATUS_DONE) in DONE_STATUSES
                  else alpha.get('status', STATUS_DONE),
        "error_message": alpha.get('error_message'),
        "is_submittable": 1 if alpha.get('sharpe', 0) >= 1.58 else 0,
        "submit_status": alpha.get('submit_status'),
        "submit_date": alpha.get('submit_date'),
        "reject_reason": alpha.get('reject_reason'),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    alphas_store.save()
    return True


def find_by_hash(expr_hash: str) -> Optional[dict]:
    data = alphas_store.load()
    entry = data["entries"].get(expr_hash)
    return dict(entry) if entry else None


def find_by_expression(expression: str, settings: dict = None) -> Optional[dict]:
    h = hash_alpha(expression, settings)
    return find_by_hash(h)


def get_best_alphas(limit: int = 20) -> list[dict]:
    data = alphas_store.load()
    done = [e for e in data["entries"].values()
            if e.get("status") in DONE_STATUSES]
    done.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    return done[:limit]


def get_submittable() -> list[dict]:
    data = alphas_store.load()
    return [e for e in data["entries"].values() if e.get("is_submittable") == 1]


def get_alphas_by_combo(combo_type: str) -> list[dict]:
    data = alphas_store.load()
    matched = [e for e in data["entries"].values() if e.get("combo_type") == combo_type]
    matched.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    return matched


def count_alphas() -> int:
    data = alphas_store.load()
    return len(data["entries"])


def update_alpha(expr_hash: str, updates: dict):
    """更新已有alpha的字段"""
    data = alphas_store.load()
    if expr_hash in data["entries"]:
        data["entries"][expr_hash].update(updates)
        data["entries"][expr_hash]["updated_at"] = datetime.now().isoformat()
        alphas_store.save()


# ─── Task CRUD ───

def push_task(strategy: str, expression: str, settings: dict = None,
              priority: int = 0) -> int:
    expr_hash = hash_expression(expression)
    data = tasks_store.load()
    task_id = data["_meta"]["next_id"]
    data["items"].append({
        "id": task_id,
        "strategy": strategy,
        "expression": expression,
        "expression_hash": expr_hash,
        "settings_json": json.dumps(settings or {}),
        "status": "queued",
        "priority": priority,
        "worker_id": None,
        "retries": 0,
        "max_retries": 3,
        "alpha_id": None,
        "sharpe": None,
        "error_message": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    })
    data["_meta"]["next_id"] = task_id + 1
    tasks_store.save()
    return task_id


def pop_task(worker_id: str) -> Optional[dict]:
    """原子出队: 领取优先级最高的待处理任务"""
    data = tasks_store.load()
    queued = [t for t in data["items"] if t["status"] == "queued"]
    if not queued:
        return None
    queued.sort(key=lambda t: (-t["priority"], t["id"]))
    task = queued[0]
    task["status"] = "running"
    task["worker_id"] = worker_id
    task["updated_at"] = datetime.now().isoformat()

    # 更新 worker 状态
    w_data = workers_store.load()
    if worker_id in w_data["entries"]:
        w_data["entries"][worker_id]["status"] = "busy"
        w_data["entries"][worker_id]["current_task_id"] = task["id"]
        w_data["entries"][worker_id]["last_heartbeat"] = datetime.now().isoformat()
        workers_store.save()

    tasks_store.save()
    return dict(task)


def complete_task(task_id: int, alpha_id: str, sharpe: float, success: bool = True,
                  error: str = None):
    data = tasks_store.load()
    for task in data["items"]:
        if task["id"] == task_id:
            task["status"] = "done" if success else "failed"
            task["alpha_id"] = alpha_id
            task["sharpe"] = sharpe
            task["error_message"] = error
            task["updated_at"] = datetime.now().isoformat()
            break

    # 更新 worker
    w_data = workers_store.load()
    for wid, w in w_data["entries"].items():
        if w.get("current_task_id") == task_id:
            w["status"] = "idle"
            w["current_task_id"] = None
            w["last_heartbeat"] = datetime.now().isoformat()
            if success:
                w["tasks_completed"] = w.get("tasks_completed", 0) + 1
            else:
                w["tasks_failed"] = w.get("tasks_failed", 0) + 1
            break
    workers_store.save()
    tasks_store.save()


def get_pending_count() -> int:
    """获取待处理任务数（包含queued和running，避免WorkerPool提前退出）"""
    data = tasks_store.load()
    return sum(1 for t in data["items"] if t["status"] in ("queued", "running"))


def get_queued_tasks(limit: int = 8) -> list[dict]:
    """获取待处理任务列表"""
    data = tasks_store.load()
    queued = [t for t in data["items"] if t["status"] == "queued"]
    queued.sort(key=lambda t: (-t["priority"], t["id"]))
    return queued[:limit]


# ─── Task 恢复与清理 ───

def recover_stale_tasks() -> int:
    """崩溃恢复：把所有遗留 running 任务重置为 queued（幂等）

    进程被杀后 tasks 会残留 running 状态，导致任务永远卡死。
    WorkerPool 启动时必须调用本函数。
    """
    data = tasks_store.load()
    recovered = 0
    for task in data["items"]:
        if task["status"] == TASK_RUNNING:
            task["status"] = TASK_QUEUED
            task["worker_id"] = None
            task["updated_at"] = datetime.now().isoformat()
            recovered += 1
    if recovered:
        tasks_store.save()
        print(f"[State] 崩溃恢复: {recovered} 条 running 任务重置为 queued")

    # 清理 worker 的占用状态
    w_data = workers_store.load()
    dirty = False
    for wid, w in w_data["entries"].items():
        if w.get("status") == "busy":
            w["status"] = "idle"
            w["current_task_id"] = None
            w["last_heartbeat"] = datetime.now().isoformat()
            dirty = True
    if dirty:
        workers_store.save()
    return recovered


def clean_tasks(statuses: tuple = (TASK_FAILED, TASK_RUNNING)) -> int:
    """清理指定状态的任务记录（默认清理 failed + 僵尸 running）

    Returns:
        删除的任务数
    """
    data = tasks_store.load()
    before = len(data["items"])
    data["items"] = [t for t in data["items"] if t.get("status") not in statuses]
    removed = before - len(data["items"])
    if removed:
        tasks_store.save()
    print(f"[State] 任务清理: 删除 {removed} 条 ({','.join(statuses)})，"
          f"剩余 {len(data['items'])} 条")
    return removed


# ─── Worker CRUD ───

def register_worker(worker_id: str):
    data = workers_store.load()
    if worker_id not in data["entries"]:
        data["entries"][worker_id] = {
            "id": worker_id,
            "status": "idle",
            "current_task_id": None,
            "last_heartbeat": datetime.now().isoformat(),
            "tasks_completed": 0,
            "tasks_failed": 0,
        }
        workers_store.save()


def heartbeat_worker(worker_id: str):
    data = workers_store.load()
    if worker_id in data["entries"]:
        data["entries"][worker_id]["last_heartbeat"] = datetime.now().isoformat()
        workers_store.save()


def get_idle_workers() -> list[dict]:
    data = workers_store.load()
    return [w for w in data["entries"].values() if w.get("status") == "idle"]


def get_workers() -> list[dict]:
    """获取所有worker状态"""
    data = workers_store.load()
    return list(data["entries"].values())


# ─── Experiment CRUD ───

def start_experiment(name: str, strategy: str, config: dict = None) -> int:
    data = experiments_store.load()
    exp_id = data["_meta"]["next_id"]
    data["items"].append({
        "id": exp_id,
        "name": name,
        "strategy": strategy,
        "config_json": json.dumps(config or {}),
        "status": "running",
        "total_tasks": 0,
        "completed_tasks": 0,
        "best_sharpe": 0,
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
    })
    data["_meta"]["next_id"] = exp_id + 1
    experiments_store.save()
    return exp_id


def finish_experiment(exp_id: int, best_sharpe: float):
    data = experiments_store.load()
    for exp in data["items"]:
        if exp["id"] == exp_id:
            exp["status"] = "done"
            exp["best_sharpe"] = best_sharpe
            exp["finished_at"] = datetime.now().isoformat()
            break
    experiments_store.save()


# ─── Dataset CRUD ───

def save_dataset(dataset_id: str, name: str, fields: list[str]):
    data = datasets_store.load()
    data["entries"][dataset_id] = {
        "id": dataset_id,
        "name": name,
        "field_count": len(fields),
        "fields_json": json.dumps(fields),
        "last_fetched": datetime.now().isoformat(),
    }
    datasets_store.save()


def save_valid_field(field_name: str, dataset_id: str, data_type: str = ""):
    data = valid_fields_store.load()
    data["entries"][field_name] = {
        "field_name": field_name,
        "dataset_id": dataset_id,
        "data_type": data_type,
        "first_seen": datetime.now().isoformat(),
    }
    valid_fields_store.save()


# ─── Clean ───

def clean_alphas(keep_top: int = 500):
    """清理：只保留 top N 个 alpha"""
    data = alphas_store.load()
    entries = list(data["entries"].values())
    entries.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    kept = entries[:keep_top]
    data["entries"] = {e["expression_hash"]: e for e in kept}
    alphas_store.save()
    return len(entries) - keep_top


# ─── Migration ───

def normalize_alpha_statuses() -> int:
    """幂等数据修复：把历史遗留 status='ok' 的 alpha 条目归一化为 'done'

    2026-06 之前 backtest_runner 以结果状态 'ok' 直接入库，
    导致感知层（只认 'done'）统计为 0。本函数一次性修复存量数据，
    新数据由 save_alpha 写入时自动归一化。

    Returns:
        修复的条目数
    """
    data = alphas_store.load()
    fixed = 0
    for entry in data["entries"].values():
        if entry.get("status") == STATUS_OK:
            entry["status"] = STATUS_DONE
            entry["updated_at"] = datetime.now().isoformat()
            fixed += 1
    if fixed:
        alphas_store.save()
        print(f"[State] 数据修复完成: {fixed} 条 status 'ok' → 'done'")
    return fixed


def migrate_json_results(json_dir: str = None):
    """迁移历史JSON结果到state

    默认扫描项目内运行时目录（不再依赖 /tmp）：
    <project>/worldquant_brain/state/_runtime/multi_agent_results/*_results.json
    """
    import glob
    if json_dir is None:
        json_dir = str(RUNTIME_DIR / "multi_agent_results")
    count = 0
    for f in glob.glob(f"{json_dir}/*_results.json"):
        try:
            with open(f) as fp:
                file_data = json.load(fp)
            for r in file_data.get('results', []):
                if r.get('status') != STATUS_OK:
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
                    'status': STATUS_DONE,
                }
                if save_alpha(alpha):
                    count += 1
        except Exception:
            pass
    print(f"[State] 迁移完成: {count} 条结果入库")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        init_db()
        migrate_json_results()
        print(f"[State] 总Alpha数: {count_alphas()}")
        print("[State] Top 5:")
        for a in get_best_alphas(5):
            print(f"  {a['name']}: Sharpe={a['sharpe']:.3f} Fitness={a['fitness']:.3f}")
    elif len(sys.argv) > 1 and sys.argv[1] == '--fix-status':
        init_db()
        normalize_alpha_statuses()
        print(f"[State] 总Alpha数: {count_alphas()}")
        print("[State] Top 5:")
        for a in get_best_alphas(5):
            print(f"  {a['name']}: Sharpe={a['sharpe']:.3f} Fitness={a['fitness']:.3f}")
    else:
        init_db()
