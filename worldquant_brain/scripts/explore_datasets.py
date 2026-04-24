#!/usr/bin/env python3
"""
数据集探索器 - 寻找高Sharpe且Margin>Turnover的数据集
测试多个数据集的基础特性
"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient


class DatasetExplorer:
    def __init__(self, email: str, password: str):
        self.client = BrainApiClient()
        self.email = email
        self.password = password

    async def authenticate(self):
        result = await self.client.authenticate(self.email, self.password)
        return result.get('status') == 'authenticated'

    async def get_datasets(self):
        """获取数据集列表"""
        datasets = await self.client.get_datasets()
        if datasets and 'results' in datasets:
            return datasets['results']
        return []

    async def test_dataset(self, dataset_id: str, templates: list) -> list:
        """测试单个数据集"""
        # 获取数据集字段
        fields_result = await self.client.get_datafields(dataset_id=dataset_id)
        if not fields_result or 'results' not in fields_result:
            return []

        fields = fields_result['results']
        if not fields:
            return []

        # 取前5个字段测试
        test_fields = fields[:5]
        results = []

        for field in test_fields:
            field_id = field['id']

            for template, name in templates:
                expr = template.format(data=field_id)

                settings = {
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

                payload = {'type': 'REGULAR', 'settings': settings, 'regular': expr}

                resp = self.client.session.post(
                    f'{self.client.base_url}/simulations', json=payload
                )

                if resp.status_code != 201:
                    continue

                location = resp.headers.get('Location', '')

                # 轮询等待
                for _ in range(80):
                    await asyncio.sleep(2)
                    r = self.client.session.get(location)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get('status') == 'COMPLETE':
                            alpha_id = data.get('alpha')
                            if alpha_id:
                                ar = self.client.session.get(
                                    f'{self.client.base_url}/alphas/{alpha_id}'
                                )
                                if ar.status_code == 200:
                                    alpha = ar.json()
                                    is_data = alpha.get('is', {})
                                    sharpe = is_data.get('sharpe', 0)
                                    fitness = is_data.get('fitness', 0)
                                    margin = is_data.get('margin', 0)
                                    turnover = is_data.get('turnover', 0)
                                    returns = is_data.get('returns', 0)

                                    margin_ratio = margin / turnover if turnover > 0.01 else 0

                                    result = {
                                        'dataset': dataset_id,
                                        'field': field_id,
                                        'template': name,
                                        'sharpe': sharpe,
                                        'fitness': fitness,
                                        'margin': margin,
                                        'turnover': turnover,
                                        'margin_ratio': margin_ratio,
                                        'alpha_id': alpha_id,
                                    }
                                    results.append(result)
                            break
                        elif data.get('status') == 'ERROR':
                            break
                await asyncio.sleep(0.5)

        return results

    async def explore(
        self,
        datasets: list,
        max_datasets: int = 5,
        templates: list = None
    ) -> list:
        """探索多个数据集"""

        if templates is None:
            templates = [
                ('winsorize({data})', 'winsorize'),
                ('ts_mean({data}, 20)', 'ts_mean_20'),
                ('ts_mean(winsorize({data}), 20)', 'mean_winsorize'),
            ]

        print("=" * 60)
        print("数据集探索器 - 寻找高Sharpe+好Margin的数据集")
        print("=" * 60)
        print(f"测试数据集: {max_datasets}个")
        print(f"模板: {[t[1] for t in templates]}")
        print()

        all_results = []
        tested = 0

        for ds in datasets[:max_datasets]:
            ds_id = ds['id']
            tested += 1
            print(f"[{tested}/{max_datasets}] 探索 {ds_id}...")

            results = await self.test_dataset(ds_id, templates)

            if results:
                # 找最优
                best = max(results, key=lambda x: x['sharpe'])
                print(f"    最优: Sharpe={best['sharpe']:.2f}, M/T={best['margin_ratio']:.2f}")

                for r in results:
                    r['tested_datasets'] = tested
                all_results.extend(results)
            else:
                print(f"    无有效结果")

            await asyncio.sleep(1)

        return all_results


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    explorer = DatasetExplorer(
        config['credentials']['email'],
        config['credentials']['password']
    )

    print("[1] 认证...")
    if not await explorer.authenticate():
        print("认证失败!")
        return
    print("✅ 认证成功!")

    print("\n[2] 获取数据集列表...")
    datasets = await explorer.get_datasets()
    print(f"获取到 {len(datasets)} 个数据集")

    # 优先测试的有价值数据集
    priority_datasets = [
        'mdl136',  # ETF，高Sharpe
        'pv87',    # 金融矩阵，M/T高
        'analyst10',  # 分析师
        'wds',     # 消息数据
        'pv1',     # 价格
        'pv13',    # 价格
    ]

    # 过滤存在的
    ds_dict = {ds['id']: ds for ds in datasets}
    test_datasets = []
    for pid in priority_datasets:
        if pid in ds_dict:
            test_datasets.append(ds_dict[pid])
            print(f"  加入测试: {pid}")

    # 添加其他数据集填充到5个
    if len(test_datasets) < 5:
        other_datasets = [ds for ds in datasets if ds['id'] not in priority_datasets]
        test_datasets.extend(other_datasets[:5 - len(test_datasets)])

    print(f"\n[3] 优先测试: {[ds['id'] for ds in test_datasets[:10]]}")

    templates = [
        ('winsorize({data})', 'winsorize'),
        ('ts_mean({data}, 20)', 'ts_mean_20'),
        ('ts_mean(winsorize({data}), 20)', 'mean_winsorize'),
    ]

    results = await explorer.explore(test_datasets, max_datasets=20, templates=templates)

    print("\n" + "=" * 60)
    print(f"探索完成! 共 {len(results)} 个结果")

    if results:
        # 按Sharpe排序
        results.sort(key=lambda x: x['sharpe'], reverse=True)

        print("\nTop 10 高Sharpe:")
        for r in results[:10]:
            print(f"  {r['dataset']}/{r['template']}: Sharpe={r['sharpe']:.2f}, "
                  f"M/T={r['margin_ratio']:.2f}, Margin={r['margin']:.4f}, T={r['turnover']:.4f}")

        # 按M/T排序
        results.sort(key=lambda x: x['margin_ratio'], reverse=True)

        print("\nTop 10 高Margin/Turnover:")
        for r in results[:10]:
            print(f"  {r['dataset']}/{r['template']}: M/T={r['margin_ratio']:.2f}, "
                  f"Sharpe={r['sharpe']:.2f}, Margin={r['margin']:.4f}, T={r['turnover']:.4f}")

        # 找同时满足高Sharpe和好M/T的
        good = [r for r in results if r['sharpe'] >= 1.0 and r['margin_ratio'] > 1.0]
        if good:
            print(f"\n🎉 找到 {len(good)} 个Sharpe>=1且M/T>1的候选:")
            for r in good[:5]:
                print(f"  {r['dataset']}/{r['template']}: Sharpe={r['sharpe']:.2f}, M/T={r['margin_ratio']:.2f}")

        # 保存结果
        output = {
            'all_results': results,
            'good_candidates': good,
            'tested_datasets': [ds['id'] for ds in test_datasets],
        }
        output_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'outputs', 'dataset_exploration.json'
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())