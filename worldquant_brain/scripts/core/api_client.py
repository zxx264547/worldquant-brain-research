"""带重试逻辑的BRAIN API客户端封装"""

import sys
import os
import asyncio
import logging
import json
import random
import time
from pathlib import Path
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

# Session持久化路径
SESSION_DIR = Path.home() / ".worldquant_brain"
SESSION_FILE = SESSION_DIR / "session.json"
SESSION_DIR.mkdir(exist_ok=True)


class RetryableBrainClient:
    """带重试逻辑的API客户端"""

    def __init__(
        self,
        credentials: Dict[str, str] = None,
        max_retries: int = 3,
        poll_timeout: int = 600,
        poll_interval: int = 5
    ):
        self.credentials = credentials
        self.max_retries = max_retries
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.client = BrainApiClient()
        self._authenticated = False

        # 数据集字段缓存
        self._datafields_cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600  # 1小时

        # 已测试组合记录（去重用）
        self._tested_combinations: set = set()

        # 尝试恢复Session
        self._load_session()

    def _save_session(self):
        """保存session到本地文件"""
        try:
            session_data = {
                'cookies': dict(self.client.session.cookies),
                'headers': dict(self.client.session.headers),
            }
            with open(SESSION_FILE, 'w') as f:
                json.dump(session_data, f)
            logger.info("Session saved to disk")
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def _load_session(self) -> bool:
        """从本地文件恢复session"""
        if not SESSION_FILE.exists():
            return False
        try:
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
            self.client.session.cookies.update(session_data.get('cookies', {}))
            # 验证session是否仍然有效
            if self.client.is_authenticated():
                self._authenticated = True
                logger.info("Session restored from disk")
                return True
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
        return False

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._datafields_cache:
            return False
        _, timestamp = self._datafields_cache[key]
        return (time.time() - timestamp) < self._cache_ttl

    def is_tested(self, expression: str, dataset: str, settings: dict = None) -> bool:
        """检查组合是否已测试过"""
        key = self._make_key(expression, dataset, settings)
        return key in self._tested_combinations

    def record_tested(self, expression: str, dataset: str, settings: dict = None, result: dict = None):
        """记录已测试的组合"""
        key = self._make_key(expression, dataset, settings)
        self._tested_combinations.add(key)
        if result:
            # 同时保存结果到本地文件
            self._save_result(key, result)

    def _make_key(self, expression: str, dataset: str, settings: dict = None) -> str:
        """生成组合唯一键"""
        parts = [expression, dataset]
        if settings:
            # 按固定顺序添加关键参数
            for k in sorted(['region', 'universe', 'delay', 'decay', 'truncation']):
                if k in settings:
                    parts.append(f"{k}={settings[k]}")
        return "|".join(parts)

    def _save_result(self, key: str, result: dict):
        """保存测试结果到本地缓存"""
        try:
            cache_file = SESSION_DIR / "results_cache.json"
            cache = {}
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
            cache[key] = result
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            logger.warning(f"Failed to save result cache: {e}")

    def get_cached_result(self, expression: str, dataset: str, settings: dict = None) -> Optional[dict]:
        """获取缓存的测试结果"""
        key = self._make_key(expression, dataset, settings)
        try:
            cache_file = SESSION_DIR / "results_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                return cache.get(key)
        except Exception:
            pass
        return None

    def load_results_cache(self):
        """从文件加载已测试组合到内存"""
        cache_file = SESSION_DIR / "results_cache.json"
        if not cache_file.exists():
            return
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
            for key in cache.keys():
                self._tested_combinations.add(key)
            logger.info(f"Loaded {len(cache)} cached results")
        except Exception as e:
            logger.warning(f"Failed to load results cache: {e}")

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
            self._save_session()  # 保存session
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

        # 检查是否已测试过
        dataset = settings.get('dataset', 'unknown')
        if self.is_tested(expression, dataset, settings):
            cached = self.get_cached_result(expression, dataset, settings)
            if cached:
                logger.info(f"Skipping tested combination (cached): {expression[:40]}...")
                return cached

        payload = {
            'type': 'REGULAR',
            'settings': settings,
            'regular': expression
        }

        resp = self.client.session.post(
            f'{self.client.base_url}/simulations',
            json=payload
        )

        # 处理限流 - 使用Retry-After header
        if resp.status_code == 429:
            retry_after = resp.headers.get('Retry-After')
            if retry_after:
                wait_time = min(float(retry_after), 60)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            raise RateLimitError("Rate limit exceeded")
        elif resp.status_code != 201:
            raise SimulationError(f"Failed to create simulation: {resp.status_code} {resp.text[:200]}")

        location = resp.headers.get('Location', '')
        logger.info(f"Simulation created, polling: {location[:50]}...")

        result = await self._poll_for_completion(location, timeout or self.poll_timeout)

        if result.get('status') == 'ERROR':
            raise SimulationError(f"Simulation error: {result.get('message', 'Unknown')[:100]}")

        # 记录已测试
        self.record_tested(expression, dataset, settings, result)

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
        """获取数据集字段带重试（带缓存）"""
        # 检查缓存
        if self._is_cache_valid(dataset_id):
            logger.info(f"Using cached datafields for {dataset_id}")
            return self._datafields_cache[dataset_id][0]

        await self.ensure_authenticated()

        result = await self.client.get_datafields(dataset_id=dataset_id)

        if not result or 'results' not in result:
            raise BrainAPIError(f"Failed to get datafields for {dataset_id}")

        fields = result['results']
        # 更新缓存
        self._datafields_cache[dataset_id] = (fields, time.time())
        logger.info(f"Cached datafields for {dataset_id}: {len(fields)} fields")

        return fields

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