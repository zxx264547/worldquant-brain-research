#!/usr/bin/env python3
"""
激进Alpha挖掘策略
- 更短回溯期(ts_mean 5/10 而非 20)
- 尝试pv87数据集
- 更激进的模板
"""

import sys
import os
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient


@dataclass
class AlphaResult:
    alpha_id: str = ""
    expression: str = ""
    template: str = ""
    field_id: str = ""
    dataset: str = ""
    sharpe: float = 0.0
    fitness: float = 0.0
    margin: float = 0.0
    turnover: float = 0.0
    ppc: float = 0.0
    returns: float = 0.0
    checks: Dict[str, bool] = field(default_factory=dict)
    all_pass: bool = False


class AggressiveMiner:
    def __init__(self, email: str, password: str, max_workers: int = 4):
        self.email = email
        self.password = password
        self.max_workers = max_workers
        self.results: List[AlphaResult] = []
        self.lock = Lock()
        self.passing: List[AlphaResult] = []
        self.tested_count = 0
        self.stop_on_first = True

    def authenticate_sync(self) -> BrainApiClient:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = BrainApiClient()
        loop.run_until_complete(client.authenticate(self.email, self.password))
        return client

    def create_and_wait_alpha_sync(self, client: BrainApiClient, expression: str,
                                    field_id: str, dataset: str,
                                    template: str, timeout: int = 600) -> Optional[AlphaResult]:
        settings_dict = {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': 1,
            'decay': 0.0,
            'neutralization': 'NONE',
            'truncation': 0.0,
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False
        }

        payload = {
            'type': 'REGULAR',
            'settings': settings_dict,
            'regular': expression
        }

        resp = client.session.post(f'{client.base_url}/simulations', json=payload)
        if resp.status_code != 201:
            return None

        location = resp.headers.get('Location', '')
        start_time = time.time()

        while time.time() - start_time < timeout:
            time.sleep(4)
            r = client.session.get(location)
            if r.status_code == 200:
                data = r.json()
                status = data.get('status')
                if status == 'COMPLETE':
                    alpha_id = data.get('alpha')
                    if alpha_id:
                        ar = client.session.get(f'{client.base_url}/alphas/{alpha_id}')
                        if ar.status_code == 200:
                            alpha = ar.json()
                            return self._process_alpha(alpha, expression, field_id, dataset, template)
                    return None
                elif status == 'ERROR':
                    return None

        return None

    def _process_alpha(self, alpha: dict, expression: str, field_id: str,
                       dataset: str, template: str) -> AlphaResult:
        is_data = alpha.get('is', {})
        sharpe = is_data.get('sharpe', 0)
        fitness = is_data.get('fitness', 0)
        margin = is_data.get('margin', 0)
        turnover = is_data.get('turnover', 0)
        returns_val = is_data.get('returns', 0)
        ppc = abs(margin / returns_val) if returns_val != 0 else 1

        checks = {
            'sharpe': sharpe >= 1.58,
            'fitness': fitness > 0.5,
            'ppc': ppc < 0.5,
            'margin_gt_turnover': margin > turnover,
            'turnover': turnover > 0.01,
        }
        all_pass = all(checks.values())

        result = AlphaResult(
            alpha_id=alpha.get('id', ''),
            expression=expression,
            template=template,
            field_id=field_id,
            dataset=dataset,
            sharpe=sharpe,
            fitness=fitness,
            margin=margin,
            turnover=turnover,
            ppc=ppc,
            returns=returns_val,
            checks=checks,
            all_pass=all_pass
        )

        with self.lock:
            self.results.append(result)
            self.tested_count += 1
            if all_pass and result not in self.passing:
                self.passing.append(result)

        return result

    def worker(self, work_item: Dict[str, Any]) -> Optional[AlphaResult]:
        expression = work_item['expression']
        field_id = work_item['field_id']
        dataset = work_item['dataset']
        template = work_item['template']

        try:
            client = self.authenticate_sync()
            result = self.create_and_wait_alpha_sync(
                client, expression, field_id, dataset, template
            )
            return result
        except Exception as e:
            with self.lock:
                self.tested_count += 1
            return None

    async def mine(self, max_tests: int = 100):
        print("=" * 60)
        print("激进Alpha挖掘 v2 - 短回溯期 + pv87")
        print(f"并发数: {self.max_workers}")
        print("=" * 60)

        # 初始化客户端
        client = BrainApiClient()
        with open('config/user_config.json') as f:
            config = json.load(f)
        await client.authenticate(config['credentials']['email'], config['credentials']['password'])

        # 目标数据集 - 优先pv87和其他有潜力的
        target_datasets = ['pv87', 'pv1', 'pv13', 'analyst4', 'fundamental6']

        # 获取各数据集的字段
        print("\n[1] 获取字段...")
        all_fields: Dict[str, List] = {}
        for ds_id in target_datasets:
            try:
                fields_result = await client.get_datafields(dataset_id=ds_id)
                if fields_result and 'results' in fields_result:
                    all_fields[ds_id] = fields_result['results'][:12]
                    print(f"  {ds_id}: {len(all_fields[ds_id])} 字段")
            except Exception as e:
                print(f"  ❌ {ds_id}: {str(e)[:30]}")
            await asyncio.sleep(1)

        # 激进模板 - 短回溯期和激进组合
        templates = [
            # 短回溯期
            ('ts_mean({data}, 5)', 'ts5'),
            ('ts_mean({data}, 10)', 'ts10'),
            ('ts_mean({data}, 20)', 'ts20'),
            # rank+短回溯
            ('rank(ts_mean({data}, 5))', 'rank_ts5'),
            ('rank(ts_mean({data}, 10))', 'rank_ts10'),
            # 激进组合
            ('rank({data}) * ts_mean({data}, 5)', 'rank*ts5'),
            ('ts_zscore({data}, 5)', 'zscore5'),
            ('ts_zscore({data}, 10)', 'zscore10'),
            # winsorize+短回溯
            ('winsorize(ts_mean({data}, 5))', 'win_ts5'),
            ('winsorize(ts_mean({data}, 10))', 'win_ts10'),
        ]

        # 生成工作项
        print(f"\n[2] 生成测试任务...")
        work_items = []
        for ds_id, fields in all_fields.items():
            for field in fields:
                for template_expr, template_name in templates:
                    if len(work_items) >= max_tests:
                        break
                    work_items.append({
                        'expression': template_expr.format(data=field['id']),
                        'field_id': field['id'],
                        'dataset': ds_id,
                        'template': template_name,
                    })
            if len(work_items) >= max_tests:
                break

        print(f"  共 {len(work_items)} 个任务")

        # 并行执行
        print(f"\n[3] 开始挖掘...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.worker, item): item for item in work_items}

            for future in as_completed(futures):
                if self.stop_on_first and len(self.passing) > 0:
                    print("🎉 找到可提交Alpha!")
                    for f in futures:
                        f.cancel()
                    break

                result = future.result()
                if result:
                    mr = result.margin / result.turnover if result.turnover > 0 else 0
                    checks_passed = sum(1 for v in result.checks.values() if v)
                    print(f"[{self.tested_count}] {result.template}: "
                          f"Sharpe={result.sharpe:.2f}, "
                          f"M/T={mr:.1f}, "
                          f"PPC={result.ppc:.2f}, "
                          f"({checks_passed}/5) | "
                          f"{result.expression[:35]}...")

        elapsed = time.time() - start_time

        # 汇总
        print(f"\n{'='*60}")
        print(f"完成! 用时 {elapsed/60:.1f}分钟")
        print(f"总计: {self.tested_count}, 通过: {len(self.passing)}")

        # 分析结果
        good_results = [r for r in self.results
                        if r.margin > r.turnover and r.ppc < 0.5 and r.sharpe > 0]
        good_results.sort(key=lambda x: x.sharpe, reverse=True)

        print(f"\n满足 M/T>1, PPC<0.5 的Top 10:")
        for r in good_results[:10]:
            mr = r.margin / r.turnover if r.turnover > 0 else 0
            print(f"  Sharpe={r.sharpe:.2f}, M/T={mr:.1f}, PPC={r.ppc:.3f} | {r.template}")

        # 保存
        output = {
            'all_results': [vars(r) for r in self.results],
            'passing': [vars(r) for r in self.passing],
            'good_results': [vars(r) for r in good_results],
        }
        output_path = os.path.join(os.path.dirname(__file__), '..', 'aggressive_results.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n已保存: {output_path}")

        return good_results


async def main():
    with open('config/user_config.json') as f:
        config = json.load(f)

    miner = AggressiveMiner(config['credentials']['email'], config['credentials']['password'], max_workers=4)
    results = await miner.mine(max_tests=120)

    if results:
        best = results[0]
        print(f"\n🎯 最佳Alpha: Sharpe={best.sharpe:.2f}")
        print(f"   表达式: {best.expression}")


if __name__ == "__main__":
    asyncio.run(main())