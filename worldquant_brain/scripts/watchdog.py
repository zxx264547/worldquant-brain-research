#!/usr/bin/env python3
"""服务看门狗 — 自动监控和重启关键服务

基于论坛文章: MCP Http Server + launchd/systemd 保活
Linux/WSL: 使用简单的进程监控 + 自动重启
"""

import subprocess
import time
import sys
import signal
from pathlib import Path
from datetime import datetime

SERVICES = {
    "web_dashboard": {
        "cmd": [
            "/home/zxx/wq_env/bin/python",
            "/home/zxx/worldQuant/worldquant_brain/web/server.py"
        ],
        "health_url": "http://localhost:8080/api/stats",
        "port": 8080,
        "max_restarts": 10,
        "restart_delay": 5,
    },
    "orchestrated_mining": {
        "cmd": [
            "/home/zxx/wq_env/bin/python",
            "/home/zxx/worldQuant/worldquant_brain/scripts/orchestrated_mining.py"
        ],
        "health_url": None,
        "port": None,
        "max_restarts": 5,
        "restart_delay": 30,
    },
}

LOG_FILE = Path("/tmp/multi_agent/logs/watchdog.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [WATCHDOG] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


import requests


def health_check(service: dict) -> bool:
    """检查服务是否健康"""
    url = service.get('health_url')
    if url:
        try:
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    # 无health_url时检查进程是否存在
    port = service.get('port')
    if port:
        try:
            resp = requests.get(f"http://localhost:{port}/api/stats", timeout=5)
            return resp.status_code == 200
        except Exception:
            pass
    return True


class ServiceManager:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.process = None
        self.restart_count = 0
        self.total_restarts = 0
        self.last_restart = 0

    def start(self):
        log(f"启动 {self.name}: {' '.join(self.config['cmd'][:3])}...")
        try:
            self.process = subprocess.Popen(
                self.config['cmd'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log(f"  {self.name} PID={self.process.pid}")
            return True
        except Exception as e:
            log(f"  {self.name} 启动失败: {e}")
            return False

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            log(f"  停止 {self.name} PID={self.process.pid}")

    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def should_restart(self) -> bool:
        max_restarts = self.config.get('max_restarts', 10)
        now = time.time()
        if now - self.last_restart > 300:
            self.restart_count = 0
        return self.restart_count < max_restarts

    def restart(self):
        self.stop()
        self.restart_count += 1
        self.total_restarts += 1
        self.last_restart = time.time()
        delay = self.config.get('restart_delay', 5)
        time.sleep(delay)
        self.start()


def main():
    log("=" * 50)
    log("服务看门狗启动")

    # 信号处理
    managers = {}

    def shutdown(sig, frame):
        log("收到关闭信号, 停止所有服务...")
        for name, mgr in managers.items():
            mgr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 启动所有服务
    for name, config in SERVICES.items():
        mgr = ServiceManager(name, config)
        mgr.start()
        managers[name] = mgr
        # 给服务启动时间
        time.sleep(3)

    log(f"监控 {len(managers)} 个服务")
    check_interval = 30  # 每30秒检查一次

    while True:
        time.sleep(check_interval)

        for name, mgr in managers.items():
            if not mgr.is_alive():
                log(f"❌ {name} 进程已停止 (退出码: {mgr.process.returncode if mgr.process else 'N/A'})")

                if mgr.should_restart():
                    log(f"  🔄 重启 {name} (第{mgr.restart_count}次)")
                    mgr.restart()
                else:
                    log(f"  ⛔ {name} 已达最大重启次数, 放弃")

            # 额外健康检查
            if mgr.is_alive() and mgr.config.get('health_url'):
                if not health_check(mgr.config):
                    log(f"  ⚠️ {name} 进程存活但健康检查失败, 准备重启")
                    if mgr.should_restart():
                        mgr.restart()

        # 每小时输出统计
        if int(time.time()) % 3600 < check_interval:
            log(f"统计:")
            for name, mgr in managers.items():
                status = "✅" if mgr.is_alive() else "❌"
                log(f"  {status} {name}: 总重启{mgr.total_restarts}次")


if __name__ == "__main__":
    main()