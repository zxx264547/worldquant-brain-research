#!/usr/bin/env python3
"""测试 BRAIN API 连接"""

import sys
import os

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient
import json

def test_api():
    # 读取配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    credentials = config['credentials']

    print(f"尝试登录: {credentials['email']}")

    # 创建客户端
    client = BrainApiClient()

    # 尝试认证（异步）
    import asyncio

    async def do_auth():
        result = await client.authenticate(credentials['email'], credentials['password'])
        return result

    result = asyncio.run(do_auth())

    if result.get('status') == 'authenticated' and result.get('has_jwt'):
        print("✅ API 连接成功！")
        print(f"用户: {result['user']['email']}")
        print(f"权限: {result['permissions']}")
    else:
        print(f"❌ 认证失败: {result}")

if __name__ == "__main__":
    test_api()
