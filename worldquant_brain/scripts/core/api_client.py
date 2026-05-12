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

from platform_functions import BrainApiClient, SimulationSettings, SimulationData
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
        # 自动从配置文件加载凭据
        if credentials is None:
            credentials = self._load_credentials()
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

    def _load_credentials(self) -> Optional[Dict[str, str]]:
        """从配置文件加载凭据"""
        config_paths = [
            Path("/home/zxx/worldQuant/worldquant_brain/config/user_config.json"),
            Path.home() / ".worldquant_brain" / "user_config.json",
        ]
        for path in config_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        config = json.load(f)
                    if 'credentials' in config:
                        return config['credentials']
                    if 'email' in config and 'password' in config:
                        return {'email': config['email'], 'password': config['password']}
                except Exception:
                    pass
        return None

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
            # 同步credentials到内部client
            self.client.auth_credentials = {'email': email, 'password': password}
            self._authenticated = True
            logger.info("Authentication successful")
            self._save_session()  # 保存session
            return True

        raise AuthenticationError(f"Authentication failed: {result}")

    async def _check_auth_valid(self) -> bool:
        """检查当前认证是否有效 (轻量级验证)"""
        try:
            resp = self.client.session.get(
                f"{self.client.base_url}/users/self", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    async def ensure_authenticated(self):
        """确保已认证, 401时自动恢复"""
        if not self._authenticated:
            await self.authenticate_with_retry()
            return

        # 定期检查认证有效性 (~每15分钟)
        now = time.time()
        if not hasattr(self, '_last_auth_check'):
            self._last_auth_check = 0
        if now - self._last_auth_check > 900:  # 15分钟
            self._last_auth_check = now
            if not await self._check_auth_valid():
                logger.info("Auth expired, re-authenticating...")
                self._authenticated = False
                await self.authenticate_with_retry()
                logger.info("Auth recovered")

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

        # 从expression中推断dataset（从字段名推断，如 actual_eps_value_quarterly 来自 analyst4）
        dataset = self._infer_dataset(expression)
        if self.is_tested(expression, dataset, settings):
            cached = self.get_cached_result(expression, dataset, settings)
            if cached:
                logger.info(f"Skipping tested combination (cached): {expression[:40]}...")
                return cached

        # 使用 SimulationSettings 和 SimulationData 结构
        sim_settings = SimulationSettings(
            instrumentType=settings.get('instrumentType', 'EQUITY'),
            region=settings.get('region', 'USA'),
            universe=settings.get('universe', 'TOP3000'),
            delay=settings.get('delay', 1),
            decay=settings.get('decay', 0.0),
            neutralization=settings.get('neutralization', 'NONE'),
            truncation=settings.get('truncation', 0.08),
            pasteurization=settings.get('pasteurization', 'ON'),
            unitHandling=settings.get('unitHandling', 'VERIFY'),
            nanHandling=settings.get('nanHandling', 'OFF'),
            language=settings.get('language', 'FASTEXPR'),
            visualization=settings.get('visualization', False),
            testPeriod=settings.get('testPeriod', 'P0Y0M'),
            selectionHandling=settings.get('selectionHandling', 'POSITIVE'),
            selectionLimit=settings.get('selectionLimit', 1000),
            maxTrade=settings.get('maxTrade', 'OFF'),
            componentActivation=settings.get('componentActivation', 'IS'),
        )

        # 直接POST到API并轮询（不使用platform_functions的create_simulation，因为它有bug）
        settings_dict = sim_settings.model_dump()

        # REGULAR类型需要移除SUPER-specific字段
        settings_dict.pop('selectionHandling', None)
        settings_dict.pop('selectionLimit', None)
        settings_dict.pop('componentActivation', None)

        # 过滤None值
        settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

        payload = {
            'type': 'REGULAR',
            'settings': settings_dict,
            'regular': expression
        }

        resp = self.client.session.post(
            f'{self.client.base_url}/simulations',
            json=payload
        )

        # 处理限流
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

    def _infer_dataset(self, expression: str) -> str:
        """从表达式推断数据集"""
        # 常见数据集字段前缀映射
        dataset_fields = {
            'actual_eps': 'analyst4',
            'actual_sales': 'analyst4',
            'actual_cashflow': 'analyst4',
            'actual_dividend': 'analyst4',
            'actual_ebit': 'analyst4',
            'actual_ebitda': 'analyst4',
            'actual_net_income': 'analyst4',
            'actual_revenue': 'analyst4',
            'analyst4': 'analyst4',
            'mdl136': 'mdl136',
            'close': 'price',
            'open': 'price',
            'high': 'price',
            'low': 'price',
            'volume': 'price',
            'vwap': 'price',
            'return': 'price',
            'cap': 'shortable',
            'shortable': 'shortable',
            'industry': 'classifications',
            'sector': 'classifications',
            'subindustry': 'classifications',
            'region': 'classifications',
        }
        expr_lower = expression.lower()
        for field_prefix, dataset in dataset_fields.items():
            if field_prefix.lower() in expr_lower:
                return dataset
        return 'unknown'

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

            # Check for completion - API returns 'alpha' field when done
            alpha_id = data.get('alpha')
            if alpha_id:
                logger.info(f"Simulation completed, fetching alpha: {alpha_id}")
                alpha_data = await self.get_alpha_with_retry(alpha_id)
                return {
                    'status': 'COMPLETE',
                    'alpha_id': alpha_id,
                    **alpha_data
                }

            # Check for explicit status field (fallback)
            status = data.get('status')
            if status == 'COMPLETE':
                return {'status': 'COMPLETE', 'alpha_id': None}
            elif status == 'ERROR':
                return {
                    'status': 'ERROR',
                    'message': data.get('message', 'Unknown error')
                }

            # Log progress if available
            progress = data.get('progress')
            if progress:
                logger.info(f"Simulation progress: {progress:.0%}")

            # Check Retry-After header - when it's 0, simulation is likely complete
            # (but alpha might be in next request or same response)
            retry_after = r.headers.get('Retry-After')
            if retry_after:
                retry_val = float(retry_after)
                if retry_val == 0:
                    # Simulation might be complete, try getting alpha_id
                    logger.info("Retry-After=0, simulation may be complete")
                else:
                    intervals = min(retry_val, 10)

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