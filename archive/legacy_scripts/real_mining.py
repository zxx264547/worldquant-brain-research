#!/usr/bin/env python3
"""
真实的 Alpha 挖掘脚本 - 使用 BRAIN API
"""

import sys
import os
import asyncio
import json
import time

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings, SimulationData


class RealAlphaMiner:
    """真实Alpha挖掘器"""

    def __init__(self, email: str, password: str):
        self.client = BrainApiClient()
        self.email = email
        self.password = password
        self.is_authenticated = False

    async def authenticate(self):
        """认证"""
        result = await self.client.authenticate(self.email, self.password)
        self.is_authenticated = result.get('status') == 'authenticated'
        return self.is_authenticated

    async def get_datafields(self, dataset: str):
        """获取数据字段"""
        result = await self.client.get_datafields(dataset_id=dataset)
        if result and 'results' in result:
            return result['results']
        return []

    async def run_simulation(self, expression: str, region: str = "USA") -> dict:
        """运行模拟 - 手动创建和轮询"""
        settings = SimulationSettings(
            instrumentType="EQUITY",
            region=region,
            universe="TOP3000",
            delay=1,
            decay=0.0,
            neutralization="NONE",
            truncation=0.0,
            testPeriod="P0Y0M",
            unitHandling="VERIFY",
            nanHandling="OFF",
            language="FASTEXPR",
            visualization=False
        )

        # 构建payload
        settings_dict = settings.model_dump()
        settings_dict.pop('selectionHandling', None)
        settings_dict.pop('selectionLimit', None)
        settings_dict.pop('componentActivation', None)
        settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

        payload = {
            'type': 'REGULAR',
            'settings': settings_dict,
            'regular': expression
        }

        await self.client.ensure_authenticated()

        # 创建模拟
        response = self.client.session.post(
            f'{self.client.base_url}/simulations',
            json=payload
        )

        if response.status_code != 201:
            raise Exception(f"创建模拟失败: {response.status_code} - {response.text[:200]}")

        location = response.headers.get('Location', '')
        if not location:
            location = f"{self.client.base_url}/simulations/{response.json().get('id')}"

        # 轮询直到完成 (使用Retry-After header)
        max_attempts = 150
        for attempt in range(max_attempts):
            resp = self.client.session.get(location)
            if resp.status_code != 200:
                await asyncio.sleep(2)
                continue

            data = resp.json()
            status = data.get('status')

            if status in ('COMPLETE', 'SUCCESS'):
                alpha_id = data.get('alpha')
                if alpha_id:
                    # 获取alpha详情
                    alpha_resp = self.client.session.get(
                        f'{self.client.base_url}/alphas/{alpha_id}'
                    )
                    if alpha_resp.status_code == 200:
                        return alpha_resp.json()
                return data
            elif status == 'ERROR':
                raise Exception(f"模拟错误: {data.get('message', 'Unknown error')[:100]}")

            # 如果没有status字段，检查Retry-After header
            retry_after = resp.headers.get('Retry-After')
            if retry_after:
                wait_time = float(retry_after)
                if attempt % 10 == 0:
                    print(f"    进度: {data.get('progress', 'N/A')}, 等待 {wait_time:.0f}s", flush=True)
                await asyncio.sleep(min(wait_time, 10))
            else:
                # 没有Retry-After且没有status，继续等待
                if attempt % 10 == 0:
                    print(f"    等待中... ({attempt*2}s)", flush=True)
                await asyncio.sleep(2)

        raise Exception("模拟超时")

    async def get_sim_result(self, sim_id: str) -> dict:
        """获取模拟结果"""
        result = await self.client.get_alpha_details(sim_id)
        return result

    async def mine(self, region: str = "USA", max_tests: int = 20):
        """挖掘Alpha"""
        print("=" * 60)
        print("BRAIN Alpha 挖掘器")
        print("=" * 60)

        # 认证
        print("\n[1/4] 认证中...")
        if not await self.authenticate():
            print("❌ 认证失败!")
            return
        print("✅ 认证成功!")

        # 获取数据集和字段 (只用一个数据集避免限速)
        print("\n[2/4] 获取数据字段...")
        datasets = ["pv87"]  # 只用pv87避免429错误
        all_fields = {}

        for ds in datasets:
            fields = await self.get_datafields(ds)
            if fields:
                all_fields[ds] = fields
                print(f"  {ds}: {len(fields)} 个字段")

        if not all_fields:
            print("❌ 无法获取字段数据")
            return

        # Alpha模板 (使用有效的FASTEXPR操作符)
        templates = [
            ("rank(zscore({data}))", "rank_zscore"),
            ("rank(ts_zscore({data}, 20))", "rank_ts_zscore_20"),
            ("rank(ts_mean({data}, 20))", "rank_ts_mean_20"),
            ("rank(ts_max({data}, 20))", "rank_ts_max_20"),
            ("rank(ts_min({data}, 20))", "rank_ts_min_20"),
            ("rank(ts_std_dev({data}, 20))", "rank_ts_std_20"),
            ("rank(scale_down({data}))", "rank_scale_down"),
            ("-rank({data})", "rank_neg"),
        ]

        print(f"\n[3/4] 开始挖掘 (最多测试 {max_tests} 个表达式)...")

        results = []
        tested = 0

        for ds, fields in all_fields.items():
            if tested >= max_tests:
                break

            # 取前几个字段
            sample_fields = [f['id'] for f in fields[:3]]

            for field_id in sample_fields:
                if tested >= max_tests:
                    break

                data_expr = field_id  # 字段ID已包含数据集前缀

                for template, name in templates:
                    if tested >= max_tests:
                        break

                    expression = template.format(data=data_expr)
                    tested += 1

                    print(f"\n[{tested}] {name}: {expression[:60]}...")

                    try:
                        alpha_details = await self.run_simulation(expression, region)

                        if alpha_details and 'id' in alpha_details:
                            alpha_id = alpha_details['id']
                            print(f"    Alpha ID: {alpha_id}")

                            # 从is字段获取指标
                            is_data = alpha_details.get('is', {})
                            sharpe = is_data.get('sharpe', 0)
                            fitness = is_data.get('fitness', 0)
                            turnover = is_data.get('turnover', 1)
                            margin = is_data.get('margin', 0)

                            # PPC计算: margin / |returns| (或使用 margin/turnover)
                            returns = is_data.get('returns', 0)
                            ppc = abs(margin / returns) if returns != 0 else 1

                            print(f"    Sharpe: {sharpe:.3f}, Fitness: {fitness:.3f}")
                            print(f"    PPC: {ppc:.3f}, Turnover: {turnover:.3f}")

                            # PPA筛选 (放宽条件用于挖掘)
                            if ppc < 0.7 and sharpe >= 0.5 and fitness > 0.5:
                                results.append({
                                    'expression': expression,
                                    'sharpe': sharpe,
                                    'fitness': fitness,
                                    'turnover': turnover,
                                    'ppc': ppc,
                                    'margin': margin,
                                    'alpha_id': alpha_id
                                })
                                print(f"    ✅ 通过初步筛选!")
                    except Exception as e:
                        print(f"    ❌ 错误: {str(e)[:80]}")

                    await asyncio.sleep(1)

        # 结果
        print("\n" + "=" * 60)
        print(f"挖掘完成! 测试了 {tested} 个表达式，找到 {len(results)} 个候选Alpha")
        print("=" * 60)

        for i, alpha in enumerate(results, 1):
            print(f"\n[{i}] {alpha['expression']}")
            print(f"    Sharpe: {alpha['sharpe']:.3f}, Fitness: {alpha['fitness']:.3f}")
            print(f"    PPC: {alpha['ppc']:.3f}, Turnover: {alpha['turnover']:.3f}")
            print(f"    alpha_id: {alpha['alpha_id']}")

        # 保存结果
        if results:
            output_path = os.path.join(os.path.dirname(__file__), '..', 'mining_results.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n结果已保存到: {output_path}")

        return results


async def main():
    # 读取配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    miner = RealAlphaMiner(credentials['email'], credentials['password'])
    await miner.mine(max_tests=15)


if __name__ == "__main__":
    asyncio.run(main())
