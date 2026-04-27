#!/usr/bin/env python3
"""
Multi-Agent Worker 服务
每个Worker独立运行，处理分配给自己的ideas
支持daemon模式和单次执行模式

用法:
    # Daemon模式 (持续运行):
    python worker_service.py --worker_id 1 --daemon

    # 单次执行 (被cron调用):
    python worker_service.py --worker_id 1 --once
"""

import json
import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from worldquant_brain.multi_agent.message_bus import MessageBus, Event, EventType

BASE_DIR = Path("/tmp/multi_agent")
IDEAS_FILE = BASE_DIR / "ideas.json"
RESULTS_FILE = BASE_DIR / "results.json"
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"


class WorkerService:
    """Worker服务"""

    def __init__(self, worker_id: int):
        self.worker_id = f"worker_{worker_id}"
        self.worker_num = worker_id
        self.msg_bus = MessageBus()
        self.logger = self._setup_logger()
        self.brain_client = None  # 延迟初始化

    def _setup_logger(self):
        """设置日志"""
        log_file = LOG_DIR / f"{self.worker_id}.log"
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        class Logger:
            def __init__(self, file):
                self.file = file
            def log(self, msg):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                line = f"[{ts}] {msg}"
                print(line)
                with open(self.file, 'a') as f:
                    f.write(line + "\n")
        return Logger(log_file)

    def _init_brain_client(self):
        """初始化BRAIN API客户端"""
        if self.brain_client is None:
            # 添加site-packages路径
            sys.path.insert(0, '/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked')
            from platform_functions import BrainApiClient, SimulationData, SimulationSettings

            # 使用BrainApiClient
            self.brain_client = BrainApiClient()
            self.sim_settings = SimulationSettings
            self.sim_data = SimulationData
            self._authenticated = False
            self.logger.log("BRAIN API client initialized")

    def run_daemon(self, poll_interval: int = 10):
        """Daemon模式：持续监听并处理任务"""
        self.logger.log(f"{self.worker_id} daemon started (poll_interval={poll_interval}s)")

        while True:
            try:
                # 发布busy状态
                self._report_status("busy")

                # 获取分配给本worker的ideas
                ideas = self._get_assigned_ideas()

                if ideas:
                    self.logger.log(f"Found {len(ideas)} ideas to process")
                    for idea in ideas:
                        self._process_idea(idea)
                else:
                    self.logger.log("No ideas assigned, sleeping...")

                # 发布idle状态
                self._report_status("idle")

                # 等待下次轮询
                time.sleep(poll_interval)

            except KeyboardInterrupt:
                self.logger.log("Received shutdown signal")
                break
            except Exception as e:
                self.logger.log(f"ERROR in daemon loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(poll_interval)

    def run_once(self):
        """单次执行模式：处理一次任务后退出"""
        self.logger.log(f"{self.worker_id} single run started")

        try:
            # 发布busy状态
            self._report_status("busy")

            # 获取分配给本worker的ideas
            ideas = self._get_assigned_ideas()

            if ideas:
                self.logger.log(f"Found {len(ideas)} ideas to process")
                for idea in ideas:
                    self._process_idea(idea)
            else:
                self.logger.log("No ideas assigned")

            # 发布idle状态
            self._report_status("idle")
            self.logger.log("Single run completed")

        except Exception as e:
            self.logger.log(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            self._report_status("idle")

    def _get_assigned_ideas(self) -> List[dict]:
        """获取分配给本worker的ideas - 从state.json读取分配信息"""
        try:
            if not IDEAS_FILE.exists() or not STATE_FILE.exists():
                return []

            # 读取ideas
            with open(IDEAS_FILE, 'r') as f:
                ideas_data = json.load(f)
            ideas_map = {idea.get('id'): idea for idea in ideas_data.get('ideas', [])}

            # 读取state获取分配信息
            with open(STATE_FILE, 'r') as f:
                state_data = json.load(f)

            ideas_status = state_data.get('ideas_status', {})

            # 找出分配给本worker的in_progress ideas
            assigned = []
            for idea_id_str, status_info in ideas_status.items():
                # Handle both string IDs (like "idea_1") and integer IDs
                try:
                    idea_id = int(idea_id_str) if idea_id_str.isdigit() else idea_id_str
                except ValueError:
                    idea_id = idea_id_str
                if (status_info.get('assigned_worker') == self.worker_id and
                    status_info.get('status') == 'in_progress'):
                    if idea_id in ideas_map or idea_id_str in ideas_map:
                        idea = ideas_map.get(idea_id) or ideas_map.get(idea_id_str)
                        if idea:
                            idea = idea.copy()
                            idea['status'] = 'in_progress'
                            assigned.append(idea)

            return assigned

        except Exception as e:
            self.logger.log(f"Error loading ideas: {e}")
            return []

    def _process_idea(self, idea: dict):
        """处理单个idea"""
        idea_id = idea.get('id')
        field = idea.get('field')
        operator = idea.get('operator')
        window = idea.get('window')

        self.logger.log(f"Processing idea {idea_id}: field={field}, op={operator}, window={window}")

        # 更新idea状态为进行中
        self._update_idea_status(idea_id, 'in_progress')

        try:
            # 构建表达式
            expr = self._build_expression(field, operator, window, idea)
            self.logger.log(f"Expression: {expr}")

            # 运行模拟
            result = self._run_simulation(expr, idea)

            # 保存结果
            self._save_result(idea_id, result)

            # 更新idea状态为完成
            self._update_idea_status(idea_id, 'completed')

            # 发布结果事件
            self._publish_result(idea_id, result)

        except Exception as e:
            self.logger.log(f"ERROR processing idea {idea_id}: {e}")
            self._update_idea_status(idea_id, 'failed')
            import traceback
            traceback.print_exc()

    def _build_expression(self, field: str, operator: str, window, idea: dict) -> str:
        """构建Alpha表达式"""
        # 优先使用预存的expression或expr
        if 'expression' in idea and idea['expression']:
            return idea['expression']
        if 'expr' in idea and idea['expr']:
            return idea['expr']

        complexity = idea.get('complexity', idea.get('stage', '1-op'))

        # 基础表达式
        if complexity == '0-op':
            return f"rank({field})"

        # 1-op: ts_mean/ts_decay/ts_delta
        if operator == 'ts_mean' or operator is None:
            w = window or 22
            return f"ts_mean({field}, {w})"
        elif operator == 'ts_decay_linear':
            w = window or 22
            return f"ts_decay_linear({field}, {w})"
        elif operator == 'ts_delta':
            w = window or 5
            return f"ts_delta({field}, {w})"
        elif operator == 'ts_sum':
            w = window or 22
            return f"ts_sum({field}, {w}) / {w}"

        # 2-op+: 嵌套
        if complexity == '2-op':
            inner_op = idea.get('inner_operator', 'ts_delta')
            inner_window = idea.get('inner_window', 5)
            outer_op = operator or 'ts_rank'
            outer_window = window or 22
            inner_expr = f"{inner_op}({field}, {inner_window})"
            return f"ts_rank({inner_expr}, {outer_window})"

        # 默认
        w = window or 22
        return f"ts_mean({field}, {w})"

    def _run_simulation(self, expr: str, idea: dict) -> dict:
        """运行模拟 - 使用asyncio调用异步API"""
        self._init_brain_client()

        self.logger.log(f"Running simulation: {expr[:80]}...")

        max_retries = 3
        retry_delay = 60

        for attempt in range(max_retries):
            try:
                import asyncio

                async def run_sim():
                    # 认证
                    if not self._authenticated:
                        await self.brain_client.authenticate(
                            '2645471525@qq.com',
                            '20001025ZHANG'
                        )
                        self._authenticated = True

                    settings = self.sim_settings(
                        instrumentType='EQUITY',
                        region=idea.get('region', 'USA'),
                        universe=idea.get('universe', 'TOP3000'),
                        delay=idea.get('delay', 1),
                        decay=float(idea.get('decay', 0)),
                        truncation=float(idea.get('truncation', 0.25)),
                        neutralization=idea.get('neutralization', 'NONE'),
                        language='FASTEXPR',
                        visualization=False
                    )

                    data = self.sim_data(type='REGULAR', settings=settings, regular=expr)
                    result = await self.brain_client.create_simulation(data)
                    return result

                result = asyncio.run(run_sim())

                # DEBUG: Log result structure
                self.logger.log(f"Result type: {type(result).__name__}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

                # create_simulation返回alpha的完整JSON，包含is字段
                # 提取IS阶段的数据
                is_data = result.get('is', {})
                sharpe = is_data.get('sharpe')
                fitness = is_data.get('fitness')
                turnover = is_data.get('turnover')
                ppc = is_data.get('ppc')
                margin = is_data.get('margin')
                alpha_id = result.get('alpha') or result.get('id')

                self.logger.log(f"Simulation completed: sharpe={sharpe}, fitness={fitness}")

                return {
                    'alpha_id': alpha_id,
                    'expression': expr,
                    'sharpe': sharpe or 0,
                    'fitness': fitness or 0,
                    'turnover': turnover or 0,
                    'ppc': ppc or 0,
                    'margin': margin or 0,
                    'status': 'completed',
                }

            except Exception as e:
                error_str = str(e)
                if '429' in error_str or 'Too Many Requests' in error_str:
                    self.logger.log(f"Rate limited, waiting {retry_delay}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                self.logger.log(f"Simulation error: {e}")
                return {
                    'expression': expr,
                    'status': 'error',
                    'error': error_str
                }

        return {
            'expression': expr,
            'status': 'api_timeout',
            'error': 'Rate limited after retries'
        }
        return {
            'expression': expr,
            'status': 'api_timeout',
            'error': 'Rate limited after retries'
        }

    def _wait_for_simulation(self, sim_id: str, timeout: int = 900) -> str:
        """等待模拟完成"""
        start = time.time()
        check_interval = 30

        while time.time() - start < timeout:
            try:
                status = self.brain_client.check_simulation_status(sim_id)
                state = status.get('state') or status.get('status', 'UNKNOWN')
                self.logger.log(f"Check {sim_id}: {state}")

                if state in ('COMPLETED', 'FAILED', 'ERROR'):
                    return state

                time.sleep(check_interval)
            except Exception as e:
                self.logger.log(f"Error checking status: {e}")
                time.sleep(check_interval)

        return "TIMEOUT"

    def _save_result(self, idea_id: int, result: dict):
        """保存结果到results.json"""
        try:
            # 读取现有结果
            data = {'results': []}
            if RESULTS_FILE.exists():
                with open(RESULTS_FILE, 'r') as f:
                    data = json.load(f)

            # 添加新结果
            data['results'].append({
                'idea_id': idea_id,
                'worker_id': self.worker_id,
                'timestamp': datetime.now().isoformat(),
                **result
            })

            # 保存
            with open(RESULTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.log(f"Result saved for idea {idea_id}")

        except Exception as e:
            self.logger.log(f"Error saving result: {e}")

    def _publish_result(self, idea_id: int, result: dict):
        """发布结果事件"""
        event = Event(
            event_type=EventType.WORKER_RESULT.value,
            source=self.worker_id,
            data={
                'idea_id': idea_id,
                'result': result,
            }
        )
        self.msg_bus.publish(event)
        self.logger.log(f"Result event published for idea {idea_id}")

    def _report_status(self, status: str):
        """报告worker状态"""
        event_type = EventType.WORKER_BUSY.value if status == "busy" else EventType.WORKER_IDLE.value
        event = Event(
            event_type=event_type,
            source=self.worker_id,
            data={}
        )
        self.msg_bus.publish(event)

    def _update_idea_status(self, idea_id: int, status: str):
        """更新idea状态"""
        try:
            if STATE_FILE.exists():
                with open(STATE_FILE, 'r') as f:
                    state_data = json.load(f)

                ideas_status = state_data.get('ideas_status', {})
                if str(idea_id) in ideas_status:
                    ideas_status[str(idea_id)]['status'] = status
                    ideas_status[str(idea_id)]['last_updated'] = datetime.now().isoformat()

                    with open(STATE_FILE, 'w') as f:
                        json.dump(state_data, f, indent=2)

        except Exception as e:
            self.logger.log(f"Error updating idea status: {e}")


def main():
    parser = argparse.ArgumentParser(description='Worker Service')
    parser.add_argument('--worker_id', type=int, required=True, help='Worker ID (1-8)')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--poll_interval', type=int, default=10, help='Poll interval in seconds (daemon mode)')
    args = parser.parse_args()

    worker = WorkerService(args.worker_id)

    if args.daemon:
        worker.run_daemon(poll_interval=args.poll_interval)
    elif args.once:
        worker.run_once()
    else:
        print("Must specify --daemon or --once")
        sys.exit(1)


if __name__ == "__main__":
    main()