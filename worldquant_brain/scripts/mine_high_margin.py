#!/usr/bin/env python3
"""
挖掘高Margin Alpha - 解决Margin<Turnover问题
策略：使用不同数据集，寻找Margin > Turnover的Alpha
"""

import sys
import os
import asyncio
import json

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings


class HighMarginMiner:
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
            pasteurization='ON', unitHandling='VERIFY', nanHandling='OFF',
            language='FASTEXPR', visualization=False
        )

        settings_dict = settings.model_dump()
        for k in ['selectionHandling', 'selectionLimit', 'componentActivation', 'visualization']:
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

    def check_submission(self, alpha: dict) -> dict:
        """检查Alpha是否满足提交条件"""
        is_data = alpha.get('is', {})
        sharpe = is_data.get('sharpe', 0)
        fitness = is_data.get('fitness', 0)
        turnover = is_data.get('turnover', 1)
        margin = is_data.get('margin', 0)
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

        return {
            'alpha_id': alpha.get('id'),
            'sharpe': sharpe,
            'fitness': fitness,
            'ppc': ppc,
            'margin': margin,
            'turnover': turnover,
            'returns': returns_val,
            'checks': checks,
            'all_pass': all_pass,
            'expression': alpha.get('expression', ''),
            'field_id': alpha.get('field_id', ''),
        }

    async def mine(self, max_tests: int = 50):
        """挖掘高Margin Alpha"""
        print("=" * 60)
        print("高Margin Alpha挖掘器")
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
        dataset_ids = [ds['id'] for ds in datasets['results'][:30]]
        print(f"获取到 {len(dataset_ids)} 个数据集")

        # 优先挖掘高Margin的数据集和字段
        # 论坛经验：winsorize, ts_backfill 等预处理可以提高margin
        templates = [
            # 使用winsorize预处理
            ('winsorize({data})', 'winsorize'),
            ('winsorize(ts_backfill({data}))', 'winsorize_backfill'),
            # 使用ts_decay降低换手
            ('ts_decay_linear({data}, 10)', 'decay_10'),
            ('ts_decay_linear({data}, 20)', 'decay_20'),
            # 使用ts_mean平滑
            ('ts_mean({data}, 20)', 'ts_mean_20'),
            # 使用signed_power稳定化
            ('signed_power({data}, 1.3)', 'signed_power'),
            # 组合：预处理+平滑
            ('ts_mean(winsorize({data}), 20)', 'mean_winsorize'),
            ('ts_decay_linear(winsorize({data}), 10)', 'decay_winsorize'),
        ]

        results = []
        tested = 0
        found_submittable = []

        print(f"\n开始挖掘 (最多 {max_tests} 个)...")

        for ds in dataset_ids:
            if tested >= max_tests:
                break
            if found_submittable:
                break

            print(f"\n获取 {ds} 的字段...")
            fields_result = await self.client.get_datafields(dataset_id=ds)
            if not fields_result or 'results' not in fields_result:
                continue

            fields = fields_result['results'][:8]  # 每个数据集取8个字段

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
                        result = self.check_submission(alpha)
                        margin_ratio = result['margin'] / result['turnover'] if result['turnover'] > 0 else 0
                        print(f"    Sharpe={result['sharpe']:.2f}, Fitness={result['fitness']:.2f}")
                        print(f"    PPC={result['ppc']:.3f}, Margin={result['margin']:.4f}, Turnover={result['turnover']:.4f}")
                        print(f"    Margin/Turnover={margin_ratio:.2f}")

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
            output_path = os.path.join(os.path.dirname(__file__), '..', 'high_margin_alphas.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(passing, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")

        return passing


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = HighMarginMiner(credentials['email'], credentials['password'])
    await miner.mine(max_tests=50)


if __name__ == "__main__":
    asyncio.run(main())