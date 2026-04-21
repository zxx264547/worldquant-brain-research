#!/usr/bin/env python3
"""
并行多线程Alpha挖掘系统
- 并行测试多个数据集和模板
- 根据结果自动调整策略
- 找到可提交Alpha后自动提交
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

    def margin_ratio(self) -> float:
        return self.margin / self.turnover if self.turnover > 0 else 0


class ParallelAlphaMiner:
    def __init__(self, email: str, password: str, max_workers: int = 5):
        self.email = email
        self.password = password
        self.max_workers = max_workers
        self.results: List[AlphaResult] = []
        self.lock = Lock()
        self.passing: List[AlphaResult] = []
        self.tested_count = 0
        self.stop_on_first = True  # 找到可提交的后是否停止

    def authenticate_sync(self) -> BrainApiClient:
        """同步认证"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = BrainApiClient()
        loop.run_until_complete(client.authenticate(self.email, self.password))
        return client

    def create_and_wait_alpha_sync(self, client: BrainApiClient, expression: str,
                                    field_id: str, dataset: str,
                                    template: str, timeout: int = 600) -> Optional[AlphaResult]:
        """同步创建并等待Alpha"""
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
            time.sleep(5)
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
            elif r.status_code == 202:
                continue

        return None

    def _process_alpha(self, alpha: dict, expression: str, field_id: str,
                       dataset: str, template: str) -> AlphaResult:
        """处理Alpha结果"""
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
                print(f"\n{'='*60}")
                print(f"🎉 找到可提交Alpha! 总计已测试: {self.tested_count}")
                print(f"    Alpha ID: {result.alpha_id}")
                print(f"    Sharpe={result.sharpe:.2f}, Fitness={result.fitness:.2f}")
                print(f"    Margin={result.margin:.4f} > Turnover={result.turnover:.4f}")
                print(f"    PPC={result.ppc:.3f}")
                print(f"    表达式: {expression[:60]}...")
                print(f"{'='*60}\n")

        return result

    def worker(self, work_item: Dict[str, Any]) -> Optional[AlphaResult]:
        """工作线程"""
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
            print(f"  ❌ 错误: {str(e)[:50]}")
            return None

    async def mine(self, max_tests: int = 100):
        """主挖掘流程"""
        print("=" * 60)
        print("并行Alpha挖掘系统 v2")
        print(f"并发数: {self.max_workers}")
        print("=" * 60)

        # 获取数据集
        print("\n[1] 获取数据集...")
        client = BrainApiClient()
        with open('config/user_config.json') as f:
            config = json.load(f)
        await client.authenticate(config['credentials']['email'], config['credentials']['password'])

        datasets_result = await client.get_datasets()
        if not datasets_result or 'results' not in datasets_result:
            print("❌ 获取数据集失败")
            return []

        all_datasets = datasets_result['results']
        print(f"获取到 {len(all_datasets)} 个数据集")

        # 优先选择高价值数据集（根据alphaCount和userCount排序）
        priority_datasets = sorted(all_datasets,
                                    key=lambda x: x.get('alphaCount', 0) + x.get('userCount', 0) * 10,
                                    reverse=True)[:30]

        # 选择数据集
        selected_datasets = []
        for ds in priority_datasets:
            ds_id = ds['id']
            if ds_id in ['pv87', 'mdl136', 'fci', '公公，事业']:  # 跳过有问题的
                continue
            selected_datasets.append(ds)
            if len(selected_datasets) >= 8:
                break

        print(f"选择 {len(selected_datasets)} 个数据集:")
        for ds in selected_datasets:
            print(f"  - {ds['id']}: {ds.get('name', 'N/A')[:40]}")

        # 收集字段（带重试）
        print("\n[2] 获取字段...")
        all_fields: Dict[str, List] = {}
        for i, ds in enumerate(selected_datasets):
            for retry in range(3):
                try:
                    fields_result = await client.get_datafields(dataset_id=ds['id'])
                    if fields_result and 'results' in fields_result:
                        all_fields[ds['id']] = fields_result['results'][:15]
                        print(f"  {ds['id']}: {len(all_fields[ds['id']])} 字段")
                    else:
                        print(f"  ⚠️ {ds['id']}: 无字段")
                    break
                except Exception as e:
                    if '429' in str(e) or 'Too Many Requests' in str(e):
                        print(f"  ⏳ 限流，等待{10*(retry+1)}秒重试...")
                        await asyncio.sleep(10 * (retry + 1))
                    else:
                        print(f"  ❌ {ds['id']}: {str(e)[:30]}")
                        break
            await asyncio.sleep(1)

        # 定义模板（根据之前经验，winsorize和ts_mean效果好）
        templates = [
            ('winsorize({data})', 'winsorize'),
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            ('ts_mean(winsorize({data}), 20)', 'mean_win'),
            ('rank({data})', 'rank'),
            ('rank(ts_mean({data}, 20))', 'rank_ts'),
            ('ts_zscore({data}, 20)', 'zscore'),
            ('signed_power({data}, 0.5)', 'signed_pow'),
            ('winsorize(ts_backfill({data}))', 'win_backfill'),
        ]

        # 生成工作项
        work_items = []
        for ds in selected_datasets:
            if ds['id'] not in all_fields:
                continue
            for field in all_fields[ds['id']]:
                for template_expr, template_name in templates:
                    if len(work_items) >= max_tests:
                        break
                    work_items.append({
                        'expression': template_expr.format(data=field['id']),
                        'field_id': field['id'],
                        'dataset': ds['id'],
                        'template': template_name,
                        'field_desc': field.get('description', '')[:30]
                    })
                if len(work_items) >= max_tests:
                    break
            if len(work_items) >= max_tests:
                break

        print(f"\n[3] 生成 {len(work_items)} 个测试任务")

        # 并行执行
        print(f"\n[4] 开始并行挖掘 (并发={self.max_workers})...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.worker, item): item for item in work_items}

            for future in as_completed(futures):
                if self.stop_on_first and len(self.passing) > 0:
                    print("找到可提交Alpha，停止挖掘！")
                    # 取消其他任务
                    for f in futures:
                        f.cancel()
                    break

                result = future.result()
                if result:
                    mr = result.margin_ratio()
                    print(f"[{self.tested_count}] {result.template}: "
                          f"Sharpe={result.sharpe:.2f}, "
                          f"M/T={mr:.1f}, "
                          f"PPC={result.ppc:.2f} | "
                          f"{result.expression[:40]}...")

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"挖掘完成! 用时 {elapsed/60:.1f}分钟")
        print(f"总计测试: {self.tested_count}")
        print(f"通过检验: {len(self.passing)}")

        # 排序输出
        self.results.sort(key=lambda x: x.sharpe, reverse=True)

        print("\nTop 10 Sharpe:")
        for r in self.results[:10]:
            mr = r.margin_ratio()
            status = "✅" if r.all_pass else "❌"
            print(f"  {status} Sharpe={r.sharpe:.2f}, M/T={mr:.1f}, "
                  f"M={r.margin:.4f}, T={r.turnover:.4f} | {r.template}")

        # 保存结果
        output = {
            'all_results': [vars(r) for r in self.results],
            'passing': [vars(r) for r in self.passing],
            'summary': {
                'tested': self.tested_count,
                'passing': len(self.passing),
                'elapsed_minutes': elapsed / 60
            }
        }
        output_path = os.path.join(os.path.dirname(__file__), '..', 'parallel_mining_results.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存: {output_path}")

        return self.passing


async def main():
    with open('config/user_config.json') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = ParallelAlphaMiner(
        credentials['email'],
        credentials['password'],
        max_workers=3  # 限制并发数避免API限制
    )

    passing = await miner.mine(max_tests=150)

    if passing:
        print("\n" + "="*60)
        print("🎉 可提交Alpha列表:")
        for p in passing:
            print(f"\n  Alpha ID: {p.alpha_id}")
            print(f"  Sharpe: {p.sharpe:.4f}")
            print(f"  Fitness: {p.fitness:.4f}")
            print(f"  Margin: {p.margin:.4f}")
            print(f"  Turnover: {p.turnover:.4f}")
            print(f"  PPC: {p.ppc:.4f}")
            print(f"  表达式: {p.expression}")


if __name__ == "__main__":
    asyncio.run(main())