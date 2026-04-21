"""带重试逻辑的BRAIN API客户端封装"""

import sys
import os
import asyncio
import logging
from typing import Optional, Dict, Any, List

FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from platform_functions import BrainApiClient
from .exceptions import (
    BrainAPIError, AuthenticationError, SimulationTimeoutError,
    RateLimitError, SimulationError, AlphaNotFoundError
)
from .retry import async_retry

logger = logging.getLogger(__name__)


class RetryableBrainClient:
    """带重试逻辑的API客户端"""

    def __init__(
        self,
        credentials: Dict[str, str] = None,
        max_retries: int = 3,
        poll_timeout: int = 180,
        poll_interval: int = 2
    ):
        self.credentials = credentials
        self.max_retries = max_retries
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.client = BrainApiClient()
        self._authenticated = False

    @async_retry(max_attempts=3, delay=2)
    async def authenticate_with_retry(self, email: str = None, password: str = None) -> bool:
        """认证带重试"""
        if email is None and self.credentials:
            email = self.credentials.get('email')
            password = self.credentials.get('password')

        if email is None or password is None:
            raise AuthenticationError("Email or password not provided")

        logger.info("Authenticating...")
        result = await self.client.authenticate(email, password)

        if result.get('status') == 'authenticated':
            self._authenticated = True
            logger.info("Authentication successful")
            return True

        raise AuthenticationError(f"Authentication failed: {result}")

    async def ensure_authenticated(self):
        """确保已认证"""
        if not self._authenticated:
            await self.authenticate_with_retry()

    @async_retry(max_attempts=3, delay=3, backoff=3.0)
    async def create_simulation_with_retry(
        self,
        expression: str,
        settings: Dict[str, Any],
        timeout: int = None
    ) -> Dict[str, Any]:
        """创建模拟带重试

        Returns:
            dict: 包含 alpha_id, sharpe, fitness, turnover, ppc, margin 等
        """
        await self.ensure_authenticated()

        payload = {
            'type': 'REGULAR',
            'settings': settings,
            'regular': expression
        }

        resp = self.client.session.post(
            f'{self.client.base_url}/simulations',
            json=payload
        )

        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif resp.status_code != 201:
            raise SimulationError(f"Failed to create simulation: {resp.status_code} {resp.text[:200]}")

        location = resp.headers.get('Location', '')
        logger.info(f"Simulation created, polling: {location[:50]}...")

        result = await self._poll_for_completion(location, timeout or self.poll_timeout)

        if result.get('status') == 'ERROR':
            raise SimulationError(f"Simulation error: {result.get('message', 'Unknown')[:100]}")

        return result

    async def _poll_for_completion(self, location: str, timeout: int) -> Dict[str, Any]:
        """轮询等待模拟完成"""
        elapsed = 0
        intervals = self.poll_interval

        while elapsed < timeout:
            await asyncio.sleep(intervals)
            elapsed += intervals

            r = self.client.session.get(location)
            if r.status_code != 200:
                continue

            data = r.json()
            status = data.get('status')

            if status == 'COMPLETE':
                alpha_id = data.get('alpha')
                if alpha_id:
                    alpha_data = await self.get_alpha_with_retry(alpha_id)
                    return {
                        'status': 'COMPLETE',
                        'alpha_id': alpha_id,
                        **alpha_data
                    }
                return {'status': 'COMPLETE', 'alpha_id': None}

            elif status == 'ERROR':
                return {
                    'status': 'ERROR',
                    'message': data.get('message', 'Unknown error')
                }

            retry_after = r.headers.get('Retry-After')
            if retry_after:
                intervals = min(float(retry_after), 10)

        raise SimulationTimeoutError(f"Simulation polling timed out after {timeout}s")

    @async_retry(max_attempts=3, delay=2)
    async def get_alpha_with_retry(self, alpha_id: str) -> Dict[str, Any]:
        """获取Alpha详情带重试"""
        await self.ensure_authenticated()

        resp = self.client.session.get(f'{self.client.base_url}/alphas/{alpha_id}')

        if resp.status_code == 404:
            raise AlphaNotFoundError(f"Alpha not found: {alpha_id}")
        elif resp.status_code != 200:
            raise BrainAPIError(f"Failed to get alpha: {resp.status_code}")

        alpha = resp.json()
        is_data = alpha.get('is', {})

        returns = is_data.get('returns', 0)
        margin = is_data.get('margin', 0)

        return {
            'alpha_id': alpha_id,
            'sharpe': is_data.get('sharpe', 0),
            'fitness': is_data.get('fitness', 0),
            'margin': margin,
            'turnover': is_data.get('turnover', 0),
            'returns': returns,
            'ppc': abs(margin / returns) if returns != 0 else 1,
            'expression': alpha.get('expression', ''),
            'name': alpha.get('name', ''),
        }

    @async_retry(max_attempts=3, delay=1)
    async def get_datafields_with_retry(self, dataset_id: str) -> List[Dict[str, Any]]:
        """获取数据集字段带重试"""
        await self.ensure_authenticated()

        result = await self.client.get_datafields(dataset_id=dataset_id)

        if not result or 'results' not in result:
            raise BrainAPIError(f"Failed to get datafields for {dataset_id}")

        return result['results']

    @async_retry(max_attempts=3, delay=1)
    async def get_datasets_with_retry(self) -> List[Dict[str, Any]]:
        """获取数据集列表带重试"""
        await self.ensure_authenticated()

        result = await self.client.get_datasets()

        if not result or 'results' not in result:
            raise BrainAPIError("Failed to get datasets")

        return result['results']

    async def get_pnl_with_retry(self, alpha_id: str) -> List[float]:
        """获取Alpha的PnL序列

        注意：WorldQuant BRAIN API 可能不直接提供PnL序列获取。
        此方法尝试从Alpha详情中获取，如果不可用则返回空列表。
        """
        await self.ensure_authenticated()

        try:
            # 尝试获取Alpha详情
            resp = self.client.session.get(f'{self.client.base_url}/alphas/{alpha_id}')

            if resp.status_code == 404:
                raise AlphaNotFoundError(f"Alpha not found: {alpha_id}")
            elif resp.status_code != 200:
                raise BrainAPIError(f"Failed to get alpha: {resp.status_code}")

            alpha = resp.json()

            # 尝试从alpha详情中获取pnl字段
            # WorldQuant API 可能不直接提供，需要通过其他方式
            pnl = alpha.get('pnl', [])
            if pnl:
                return pnl

            # 如果没有pnl字段，尝试从is数据中推断
            # 这种情况下返回空列表，由调用方处理
            logger.warning(f"PnL not directly available for alpha {alpha_id}")
            return []

        except Exception as e:
            logger.warning(f"Could not fetch PnL for {alpha_id}: {e}")
            return []