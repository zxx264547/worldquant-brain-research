#!/usr/bin/env python3
"""
定向挖掘脚本 - 寻找满足PPA条件的Alpha
目标: Sharpe≥1.58, Fitness>0.5, PPC<0.5, Margin>Turnover, Turnover>0.01
"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings


class TargetedMiner:
    def __init__(self, email: str, password: str):
        self.client = BrainApiClient()
        self.email = email
        self.password = password

    async def authenticate(self):
        result = await self.client.authenticate(self.email, self.password)
        return result.get('status') == 'authenticated'

    async def create_alpha(self, expression: str, field_id: str) -> dict:
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
                            alpha = ar.json()
                            alpha['field_id'] = field_id
                            alpha['expression'] = expression
                            return alpha
                elif data.get('status') == 'ERROR':
                    return None

            retry_after = r.headers.get('Retry-After')
            if retry_after:
                await asyncio.sleep(min(float(retry_after), 10))

        return None

    def check_ppa(self, alpha: dict) -> dict:
        """检查Alpha是否满足PPA条件"""
        is_data = alpha.get('is', {})
        sharpe = is_data.get('sharpe', 0)
        fitness = is_data.get('fitness', 0)
        turnover = is_data.get('turnover', 1)
        margin = is_data.get('margin', 0)
        returns_val = is_data.get('returns', 0)
        ppc = abs(margin / returns_val) if returns_val != 0 else 1

        # PPA标准
        checks = {
            'sharpe': sharpe >= 1.58,
            'fitness': fitness > 0.5,
            'ppc': ppc < 0.5,
            'margin_gt_turnover': margin > turnover,
            'turnover': turnover > 0.01,
        }

        all_pass = all(checks.values())

        return {
            'alpha_id': alpha.get('id'),
            'sharpe': sharpe,
            'fitness': fitness,
            'ppc': ppc,
            'margin': margin,
            'turnover': turnover,
            'checks': checks,
            'all_pass': all_pass,
            'expression': alpha.get('expression', ''),
            'field_id': alpha.get('field_id', ''),
        }

    async def mine(self, max_tests: int = 30):
        """定向挖掘"""
        print("=" * 60)
        print("定向Alpha挖掘 - 寻找可提交Alpha")
        print("=" * 60)

        print("\n认证中...")
        if not await self.authenticate():
            print("认证失败!")
            return []
        print("✅ 认证成功!")

        # 获取数据集
        print("\n获取数据集...")
        datasets = await self.client.get_datasets()
        if not datasets or 'results' not in datasets:
            print("获取数据集失败")
            return []
        dataset_ids = [ds['id'] for ds in datasets['results'][:20]]
        print(f"获取到 {len(dataset_ids)} 个数据集")

        # 针对性模板 - 尝试不同的组合
        templates = [
            # 基础模板
            ('rank(zscore({data}))', 'rank_zscore'),
            ('rank(ts_mean({data}, 20))', 'rank_ts_mean20'),
            ('rank(ts_zscore({data}, 20))', 'rank_ts_zscore20'),

            # 高Sharpe模板
            ('ts_rank({data}, 10)', 'ts_rank_10'),
            ('ts_rank({data}, 20)', 'ts_rank_20'),
            ('ts_rank(ts_max({data}, 10), 60)', 'ts_rank_max'),

            # 组合模板
            ('rank({data}) * ts_rank({data}, 20)', 'rank_times_ts_rank'),
            ('ts_mean({data}, 20) / ts_std_dev({data}, 20)', 'mean_div_std'),
        ]

        results = []
        tested = 0
        found_submittable = []

        print(f"\n开始挖掘 (最多 {max_tests} 个)...")

        for ds in dataset_ids:
            if tested >= max_tests:
                break
            if found_submittable:
                break  # 找到可提交的就停止

            print(f"\n获取 {ds} 的字段...")
            fields_result = await self.client.get_datafields(dataset_id=ds)
            if not fields_result or 'results' not in fields_result:
                continue

            fields = fields_result['results'][:5]  # 每个数据集取5个字段

            for f in fields:
                if tested >= max_tests:
                    break
                if found_submittable:
                    break

                field_id = f['id']

                for template, template_name in templates:
                    if tested >= max_tests:
                        break
                    if found_submittable:
                        break

                    expr = template.format(data=field_id)
                    tested += 1

                    print(f"\n[{tested}] {ds}/{template_name}: {field_id[:25]}...")
                    print(f"    {expr[:55]}...")

                    alpha = await self.create_alpha(expr, field_id)

                    if alpha:
                        result = self.check_ppa(alpha)
                        print(f"    Sharpe={result['sharpe']:.2f}, Fitness={result['fitness']:.2f}")
                        print(f"    PPC={result['ppc']:.3f}, Margin={result['margin']:.4f}, Turnover={result['turnover']:.4f}")

                        # 显示各条件结果
                        status = []
                        for k, v in result['checks'].items():
                            status.append(f"{k}:{'✅' if v else '❌'}")
                        print(f"    {', '.join(status)}")

                        results.append(result)

                        if result['all_pass']:
                            print(f"    🎉 找到可提交Alpha!")
                            found_submittable.append(result)
                            break
                    else:
                        print(f"    ❌ 创建失败")

                    await asyncio.sleep(1)

        # 输出汇总
        print("\n" + "=" * 60)
        print(f"挖掘完成! 测试了 {tested} 个")

        passing = [r for r in results if r['all_pass']]
        print(f"通过PPA: {len(passing)} 个")

        if passing:
            print("\n🎉 可提交Alpha:")
            for p in passing:
                print(f"  {p['alpha_id']}: Sharpe={p['sharpe']:.2f}, Fitness={p['fitness']:.2f}")
                print(f"    PPC={p['ppc']:.3f}, Margin={p['margin']:.4f}>T={p['turnover']:.4f}")
                print(f"    {p['expression'][:60]}...")

            # 保存结果
            output_path = os.path.join(os.path.dirname(__file__), '..', 'submittable_alphas.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(passing, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")

        return passing


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = TargetedMiner(credentials['email'], credentials['password'])
    await miner.mine(max_tests=30)


if __name__ == "__main__":
    asyncio.run(main())
