#!/usr/bin/env python3
"""
Alpha挖掘脚本 V2 - 顺序执行更稳定
1. 扩大数据集 - 获取更多数据集
2. 调整模板 - 使用更有效的表达式模板
3. 深度挖掘 - 更多字段和模板组合
"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings


class AlphaMinerV2:
    def __init__(self, email: str, password: str):
        self.client = BrainApiClient()
        self.email = email
        self.password = password

    async def authenticate(self):
        result = await self.client.authenticate(self.email, self.password)
        return result.get('status') == 'authenticated'

    async def get_datasets(self):
        """获取所有数据集"""
        result = await self.client.get_datasets()
        if result and 'results' in result:
            return [ds['id'] for ds in result['results']]
        return []

    async def get_fields(self, dataset_id: str, limit: int = 20):
        """获取数据集的字段"""
        result = await self.client.get_datafields(dataset_id=dataset_id)
        if result and 'results' in result:
            return result['results'][:limit]
        return []

    async def create_alpha(self, expression: str) -> dict:
        """创建并等待Alpha"""
        settings = SimulationSettings(
            instrumentType='EQUITY', region='USA', universe='TOP3000',
            delay=1, decay=0.0, neutralization='NONE', truncation=0.0,
            testPeriod='P0Y0M', unitHandling='VERIFY', nanHandling='OFF',
            language='FASTEXPR', visualization=False
        )

        settings_dict = settings.model_dump()
        for k in ['selectionHandling', 'selectionLimit', 'componentActivation']:
            settings_dict.pop(k, None)
        settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

        payload = {
            'type': 'REGULAR',
            'settings': settings_dict,
            'regular': expression
        }

        await self.client.ensure_authenticated()
        resp = self.client.session.post(f'{self.client.base_url}/simulations', json=payload)

        if resp.status_code != 201:
            return None

        location = resp.headers.get('Location', '')

        for _ in range(100):
            await asyncio.sleep(3)
            r = self.client.session.get(location)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'COMPLETE':
                    alpha_id = data.get('alpha')
                    if alpha_id:
                        ar = self.client.session.get(f'{self.client.base_url}/alphas/{alpha_id}')
                        if ar.status_code == 200:
                            return ar.json()
                elif data.get('status') == 'ERROR':
                    return None

            retry_after = r.headers.get('Retry-After')
            if retry_after:
                await asyncio.sleep(min(float(retry_after), 10))

        return None

    async def mine(self, max_tests: int = 50):
        """挖掘Alpha"""
        print("=" * 60)
        print("Alpha 挖掘器 V2")
        print("=" * 60)

        print("\n认证中...")
        if not await self.authenticate():
            print("认证失败!")
            return []
        print("✅ 认证成功!")

        # 获取数据集
        print("\n获取数据集...")
        datasets = await self.get_datasets()
        print(f"获取到 {len(datasets)} 个数据集")

        # 有效模板 (基于论坛经验)
        templates = [
            ('rank(zscore({data}))', 'rank_zscore'),
            ('rank(ts_mean({data}, 20))', 'rank_ts_mean20'),
            ('rank(ts_max({data}, 20))', 'rank_ts_max20'),
            ('rank(ts_zscore({data}, 20))', 'rank_ts_zscore20'),
            ('-ts_rank(ts_max({data}, 60), 250)', 'neg_ts_rank_max'),
            ('ts_rank(ts_max({data}, 60), 250)', 'ts_rank_max'),
            ('ts_decay_linear(rank({data}), 5)', 'decay_rank_5'),
            ('ts_decay_linear(rank({data}), 10)', 'decay_rank_10'),
        ]

        results = []
        tested = 0

        print(f"\n开始挖掘 (最多 {max_tests} 个)...")

        for ds in datasets:
            if tested >= max_tests:
                break

            fields = await self.get_fields(ds, limit=10)
            if not fields:
                continue

            for f in fields:
                if tested >= max_tests:
                    break

                field_id = f['id']

                for template, template_name in templates:
                    if tested >= max_tests:
                        break

                    expr = template.format(data=field_id)
                    tested += 1

                    print(f"\n[{tested}] {ds}/{template_name}: {field_id[:30]}...")
                    print(f"    {expr[:60]}...")

                    alpha = await self.create_alpha(expr)

                    if alpha:
                        is_data = alpha.get('is', {})
                        sharpe = is_data.get('sharpe', 0)
                        fitness = is_data.get('fitness', 0)
                        turnover = is_data.get('turnover', 1)
                        margin = is_data.get('margin', 0)
                        returns_val = is_data.get('returns', 0)
                        ppc = abs(margin / returns_val) if returns_val != 0 else 1
                        alpha_id = alpha.get('id')

                        mvt = margin > turnover
                        can_submit = ppc < 0.5 and sharpe >= 0.7 and fitness > 0.5 and mvt

                        print(f"    Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, PPC={ppc:.2f}")
                        print(f"    Margin={margin:.4f}, Turnover={turnover:.4f} {'✅' if mvt else '❌'}")

                        if can_submit:
                            print(f"    ✅ 可提交!")
                            results.append({
                                'alpha_id': alpha_id,
                                'expression': expr,
                                'dataset': ds,
                                'field': field_id,
                                'sharpe': sharpe,
                                'fitness': fitness,
                                'ppc': ppc,
                                'margin': margin,
                                'turnover': turnover
                            })
                    else:
                        print(f"    ❌ 创建失败")

                    await asyncio.sleep(1)

        # 输出结果
        print("\n" + "=" * 60)
        print(f"挖掘完成! 测试了 {tested} 个, 通过筛选: {len(results)}")

        if results:
            print("\n可提交Alpha:")
            for r in results:
                print(f"  {r['alpha_id']}: Sharpe={r['sharpe']:.2f}, PPC={r['ppc']:.2f}")
                print(f"    {r['expression'][:60]}...")

            output_path = os.path.join(os.path.dirname(__file__), '..', 'mining_results_v2.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")

        return results


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = AlphaMinerV2(credentials['email'], credentials['password'])
    await miner.mine(max_tests=50)


if __name__ == "__main__":
    asyncio.run(main())
