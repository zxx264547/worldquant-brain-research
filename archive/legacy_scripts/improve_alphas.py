#!/usr/bin/env python3
"""
Alpha优化脚本 - 基于论坛经验
技巧: signed_power(1.3), scale, decay, ts_delay 降低换手率
"""

import sys
import os
import asyncio
import json
import time

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient, SimulationSettings, SimulationData


class AlphaOptimizer:
    """Alpha优化器 - 基于论坛经验"""

    def __init__(self, email: str, password: str):
        self.client = BrainApiClient()
        self.email = email
        self.password = password

    async def authenticate(self):
        result = await self.client.authenticate(self.email, self.password)
        return result.get('status') == 'authenticated'

    async def create_alpha(self, expression: str, region: str = "USA") -> dict:
        """创建并等待Alpha完成"""
        settings = SimulationSettings(
            instrumentType='EQUITY',
            region=region,
            universe='TOP3000',
            delay=1,
            decay=0.0,
            neutralization='NONE',
            truncation=0.0,
            testPeriod='P0Y0M',
            unitHandling='VERIFY',
            nanHandling='OFF',
            language='FASTEXPR',
            visualization=False
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
            raise Exception(f"创建失败: {resp.status_code}")

        location = resp.headers.get('Location', '')

        # 轮询
        for _ in range(150):
            await asyncio.sleep(2)
            r = self.client.session.get(location)
            if r.status_code != 200:
                continue

            data = r.json()
            status = data.get('status')

            if status in ('COMPLETE', 'SUCCESS'):
                alpha_id = data.get('alpha')
                if alpha_id:
                    ar = self.client.session.get(f'{self.client.base_url}/alphas/{alpha_id}')
                    if ar.status_code == 200:
                        return ar.json()
                return data
            elif status == 'ERROR':
                raise Exception(f"错误: {data.get('message', '')[:100]}")

            retry_after = r.headers.get('Retry-After')
            if retry_after:
                await asyncio.sleep(min(float(retry_after), 10))

        raise Exception("超时")

    async def improve_alpha(self, base_expression: str, field_id: str, region: str = "USA"):
        """改进Alpha - 基于论坛技巧"""
        improvements = [
            # 原始版本
            (base_expression.format(data=field_id), "原始"),
            # 添加signed_power稳定化 (论坛技巧: 设为1.3左右有效果)
            (f"signed_power({base_expression.format(data=field_id)}, 1.3)", "signed_power_1.3"),
            # 使用scale标准化
            (f"scale({base_expression.format(data=field_id)})", "scale"),
            # 添加decay降低换手率
            (f"ts_decay_linear({base_expression.format(data=field_id)}, 5)", "decay_5"),
            (f"ts_decay_linear({base_expression.format(data=field_id)}, 10)", "decay_10"),
            # 组合: signed_power + scale
            (f"scale(signed_power({base_expression.format(data=field_id)}, 1.3))", "power_scale"),
            # 组合: scale + decay
            (f"ts_decay_linear(scale({base_expression.format(data=field_id)}), 5)", "scale_decay"),
        ]

        results = []

        for expr, name in improvements:
            print(f"  测试: {name}", flush=True)
            try:
                alpha = await self.create_alpha(expr, region)
                alpha_id = alpha.get('id')
                is_data = alpha.get('is', {})

                sharpe = is_data.get('sharpe', 0)
                fitness = is_data.get('fitness', 0)
                turnover = is_data.get('turnover', 1)
                margin = is_data.get('margin', 0)
                returns_val = is_data.get('returns', 0)
                ppc = abs(margin / returns_val) if returns_val != 0 else 1

                result = {
                    'name': name,
                    'expression': expr,
                    'alpha_id': alpha_id,
                    'sharpe': sharpe,
                    'fitness': fitness,
                    'turnover': turnover,
                    'margin': margin,
                    'ppc': ppc,
                    'margin_vs_turnover': margin > turnover
                }

                # PPA标准: PPC<0.5, Sharpe>=1.0, Fitness>0.5, Margin>Turnover
                can_submit = (ppc < 0.5 and sharpe >= 1.0 and
                             fitness > 0.5 and margin > turnover)

                if can_submit:
                    result['can_submit'] = True
                    print(f"    ✅ 可提交! Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, PPC={ppc:.2f}, Margin={margin:.4f}>T={turnover:.4f}")

                results.append(result)

            except Exception as e:
                print(f"    ❌ 错误: {str(e)[:50]}")

            await asyncio.sleep(1)

        return results

    async def optimize_field(self, field_id: str, region: str = "USA"):
        """优化单个字段的所有变体"""
        print(f"\n优化字段: {field_id}")

        # 基于字段类型选择优化模板
        base_templates = [
            'rank(zscore({data}))',
            'rank(ts_mean({data}, 20))',
        ]

        all_results = []

        for template in base_templates:
            print(f"\n  模板: {template}")
            results = await self.improve_alpha(template, field_id, region)
            all_results.extend(results)

        # 找最佳
        if all_results:
            # 按sharpe排序
            all_results.sort(key=lambda x: x['sharpe'], reverse=True)

            print(f"\n  最佳结果:")
            for r in all_results[:3]:
                status = "✅" if r.get('can_submit') else "❌"
                print(f"    {status} {r['name']}: Sharpe={r['sharpe']:.2f}, Fitness={r['fitness']:.2f}, PPC={r['ppc']:.2f}, Margin={r['margin']:.4f}>T={r['turnover']:.4f}")

        return all_results


async def main():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    optimizer = AlphaOptimizer(credentials['email'], credentials['password'])

    print("=" * 60)
    print("Alpha 优化器 - 基于论坛经验")
    print("=" * 60)

    print("\n认证中...")
    if not await optimizer.authenticate():
        print("认证失败!")
        return
    print("✅ 认证成功!")

    # 获取优质字段进行优化
    print("\n获取候选Alpha...")
    alphas = await optimizer.client.get_user_alphas(stage='IS', limit=20, order='-dateCreated')

    if alphas and 'results' in alphas:
        candidates = []
        for a in alphas['results'][:10]:
            alpha_id = a.get('id')
            details = await optimizer.client.get_alpha_details(alpha_id)
            if details:
                is_data = details.get('is', {})
                sharpe = is_data.get('sharpe', 0)
                fitness = is_data.get('fitness', 0)
                turnover = is_data.get('turnover', 1)
                margin = is_data.get('margin', 0)
                returns_val = is_data.get('returns', 0)
                ppc = abs(margin / returns_val) if returns_val != 0 else 1

                reg = details.get('regular', {})
                if isinstance(reg, dict):
                    code = reg.get('code', '')
                else:
                    code = str(reg)

                # 找高Sharpe低Margin的Alpha进行优化
                if sharpe >= 1.5 and margin < turnover:
                    candidates.append({
                        'alpha_id': alpha_id,
                        'expression': code,
                        'sharpe': sharpe,
                        'fitness': fitness,
                        'ppc': ppc,
                        'margin': margin,
                        'turnover': turnover
                    })

        print(f"\n找到 {len(candidates)} 个候选优化对象")

        for c in candidates[:3]:
            print(f"\n优化Alpha: {c['alpha_id']}")
            print(f"  原始: Sharpe={c['sharpe']:.2f}, PPC={c['ppc']:.2f}, Margin={c['margin']:.4f}<T={c['turnover']:.4f}")
            print(f"  表达式: {c['expression'][:60]}...")

            # 提取字段ID进行优化
            # 从表达式中提取字段
            expr = c['expression']
            # 简单提取最后一个括号内的内容作为字段
            import re
            match = re.search(r'\(([a-zA-Z0-9_.]+)\)', expr)
            if match:
                field = match.group(1)
                print(f"  提取字段: {field}")
                # 这里可以进一步优化...

    print("\n优化完成!")


if __name__ == "__main__":
    asyncio.run(main())
