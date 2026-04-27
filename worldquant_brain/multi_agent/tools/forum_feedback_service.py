"""
论坛反馈服务 - 独立反馈服务
当Alpha表现差时，搜索论坛获取解决方案，并积累到知识库
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加cnhkmcp路径
FORUM_PATH = "/home/zxx/wq_env/lib/python3.12/site-packages/cnhkmcp/untracked"
sys.path.insert(0, FORUM_PATH)

from forum_functions import ForumClient

# 路径常量
KNOWLEDGE_BASE_DIR = Path("/home/zxx/worldQuant/worldquant_brain/knowledge_base/memory")
RESEARCH_MEMORY_FILE = KNOWLEDGE_BASE_DIR / "research_memory.json"
FORUM_CACHE_FILE = Path("/tmp/multi_agent/forum_discovery_cache.json")


class ForumFeedbackService:
    """独立反馈服务 - 搜索论坛获取Alpha优化方案"""

    # 问题类型到搜索词的映射
    SEARCH_TEMPLATES = {
        "fitness_low": [
            "alpha fitness optimization decay neutralization",
            "fitness less than 1 alpha improve",
            "alpha decay neutralization fitness"
        ],
        "turnover_high": [
            "alpha high turnover reduce smoothing",
            "alpha turnover smoothing ts_mean",
            "reduce alpha turnover decay"
        ],
        "weight_concentration": [
            "alpha weight concentration diversify",
            "alpha weight concentration ts_backfill",
            "group_rank alpha concentration"
        ],
        "correlation_fail": [
            "alpha correlation fix uncorrelated",
            "alpha correlation reduce dataset field",
            "uncorrelated alpha optimization"
        ],
        "sharpe_low": [
            "alpha sharpe improve optimization",
            "alpha performance improve tips",
            "sharpe ratio alpha optimization"
        ]
    }

    # 从帖子中提取的解决方案模式
    ACTION_PATTERNS = [
        r"decay\s*=\s*(\d+)",
        r"neutralization\s*=\s*(\w+)",
        r"truncation\s*=\s*([\d.]+)",
        r"trade_when\s*=\s*([^,\s]+)",
        r"ts_mean\s*\([^,]+,\s*(\d+)\)",
        r"ts_decay\s*\([^,]+,\s*(\d+)\)",
        r"ts_delta\s*\([^,]+,\s*(\d+)\)",
        r"ts_rank\s*\([^)]+\)",
        r"rank\s*\([^)]+\)",
        r"signed_power\s*\([^,]+,\s*([\d.]+)\)",
        r"group_rank\s*\([^)]+\)",
        r"group_backfill\s*\([^)]+\)",
    ]

    def __init__(self, brain_client):
        """
        初始化论坛反馈服务

        Args:
            brain_client: BRAIN API客户端（用于获取认证信息）
        """
        self.forum = ForumClient()
        self.brain_client = brain_client
        self._load_cache()

    def _load_cache(self):
        """加载论坛发现缓存"""
        if FORUM_CACHE_FILE.exists():
            try:
                with open(FORUM_CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        """保存论坛发现缓存"""
        try:
            FORUM_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FORUM_CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save forum cache: {e}")

    def generate_search_query(self, problem_type: str, alpha_metrics: Optional[Dict] = None) -> str:
        """
        根据问题类型生成搜索词

        Args:
            problem_type: 问题类型 (fitness_low, turnover_high, etc.)
            alpha_metrics: Alpha指标（可选，用于生成更精准的搜索词）

        Returns:
            str: 搜索查询字符串
        """
        templates = self.SEARCH_TEMPLATES.get(problem_type, self.SEARCH_TEMPLATES["fitness_low"])

        # 如果有alpha_metrics，可以生成更精准的搜索词
        if alpha_metrics and problem_type == "fitness_low":
            fitness = alpha_metrics.get('fitness', 0)
            if fitness < 0:
                templates = [
                    f"alpha fitness {fitness:.2f} negative improve",
                    f"fitness negative alpha optimization",
                    "alpha negative fitness fix"
                ]

        # 随机选择一个模板
        import random
        query = random.choice(templates)

        # 如果有数据集信息，添加到搜索词
        if alpha_metrics and 'dataset' in alpha_metrics:
            query = f"{query} {alpha_metrics['dataset']}"

        return query

    async def search_before_optimize(
        self,
        problem_type: str,
        alpha_metrics: Optional[Dict] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        优化前搜索论坛，返回候选方案

        Args:
            problem_type: 问题类型
            alpha_metrics: Alpha指标
            max_results: 最大返回结果数

        Returns:
            List[dict]: 候选方案列表
        """
        # 生成搜索词
        search_query = self.generate_search_query(problem_type, alpha_metrics)

        # 检查缓存
        cache_key = f"{problem_type}_{search_query}"
        if cache_key in self.cache:
            print(f"Using cached forum results for: {search_query}")
            return self.cache[cache_key]

        # 获取认证信息
        credentials = self._get_credentials()
        if not credentials:
            print("Warning: No credentials available for forum search")
            return []

        try:
            # 搜索论坛
            results = await self.forum.search_forum_posts(
                email=credentials['email'],
                password=credentials['password'],
                search_query=search_query,
                max_results=max_results,
                locale="zh-cn"
            )

            if not results.get('success'):
                print(f"Forum search failed: {results}")
                return []

            solutions = self._parse_search_results(results, search_query, problem_type)

            # 缓存结果
            self.cache[cache_key] = solutions
            self._save_cache()

            return solutions

        except Exception as e:
            print(f"Error searching forum: {e}")
            return []

    def _get_credentials(self) -> Optional[Dict[str, str]]:
        """获取认证信息"""
        # 尝试从brain_client获取
        if hasattr(self.brain_client, 'credentials'):
            return self.brain_client.credentials

        # 尝试从配置文件读取
        config_path = Path("/home/zxx/worldQuant/worldquant_brain/config/user_config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return {
                        'email': config.get('email', ''),
                        'password': config.get('password', '')
                    }
            except Exception:
                pass

        return None

    def _parse_search_results(
        self,
        results: Dict,
        search_query: str,
        problem_type: str
    ) -> List[Dict[str, Any]]:
        """解析搜索结果，提取解决方案"""
        solutions = []

        for result in results.get('results', []):
            solution = {
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'votes': result.get('votes', 0),
                'author': result.get('author', ''),
                'date': result.get('date', ''),
                'search_query': search_query,
                'problem_type': problem_type
            }

            # 提取post_id
            post_id = self._extract_post_id(result.get('link', ''))
            if post_id:
                solution['post_id'] = post_id

            solutions.append(solution)

        # 按投票数排序
        solutions.sort(key=lambda x: x.get('votes', 0), reverse=True)

        return solutions

    def _extract_post_id(self, url: str) -> Optional[str]:
        """从URL提取帖子ID"""
        # URL格式: https://support.worldquantbrain.com/hc/zh-cn/community/posts/123456
        match = re.search(r'/community/posts/(\d+)', url)
        if match:
            return match.group(1)
        return None

    async def get_solution_details(self, post_id: str) -> Dict[str, Any]:
        """获取帖子详细内容"""
        credentials = self._get_credentials()
        if not credentials:
            return {'success': False, 'error': 'No credentials'}

        try:
            post_data = await self.forum.read_full_forum_post(
                email=credentials['email'],
                password=credentials['password'],
                post_url_or_id=post_id,
                include_comments=True
            )

            return post_data

        except Exception as e:
            print(f"Error getting post details: {e}")
            return {'success': False, 'error': str(e)}

    def extract_actions(self, post_body: str) -> List[str]:
        """
        从帖子正文中提取可应用的操作

        Args:
            post_body: 帖子正文

        Returns:
            List[str]: 提取的操作列表
        """
        actions = []

        for pattern in self.ACTION_PATTERNS:
            matches = re.findall(pattern, post_body, re.IGNORECASE)
            for match in matches:
                # 将匹配转换为标准化格式
                if 'decay' in pattern.lower() and match:
                    actions.append(f"decay={match}")
                elif 'neutralization' in pattern.lower() and match:
                    actions.append(f"neutralization={match}")
                elif 'truncation' in pattern.lower() and match:
                    actions.append(f"truncation={match}")
                elif 'trade_when' in pattern.lower() and match:
                    actions.append(f"trade_when={match}")
                elif 'ts_mean' in pattern.lower() and match:
                    actions.append(f"ts_mean={match}")
                elif 'ts_decay' in pattern.lower() and match:
                    actions.append(f"ts_decay={match}")
                elif 'ts_delta' in pattern.lower() and match:
                    actions.append(f"ts_delta={match}")
                elif 'ts_rank' in pattern.lower():
                    actions.append("ts_rank")
                elif 'rank' in pattern.lower() and 'group_rank' not in pattern.lower():
                    actions.append("rank")
                elif 'signed_power' in pattern.lower() and match:
                    actions.append(f"signed_power={match}")
                elif 'group_rank' in pattern.lower():
                    actions.append("group_rank")
                elif 'group_backfill' in pattern.lower():
                    actions.append("group_backfill")

        # 去重
        return list(set(actions))

    async def search_and_extract_actions(
        self,
        problem_type: str,
        alpha_metrics: Optional[Dict] = None,
        max_posts: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索论坛并提取解决方案

        Args:
            problem_type: 问题类型
            alpha_metrics: Alpha指标
            max_posts: 最多获取几个帖子的详细内容

        Returns:
            List[dict]: 包含提取操作的解决方案列表
        """
        # 搜索论坛
        solutions = await self.search_before_optimize(problem_type, alpha_metrics)

        if not solutions:
            return []

        # 获取前max_posts个帖子的详细内容
        detailed_solutions = []
        for solution in solutions[:max_posts]:
            if 'post_id' not in solution:
                continue

            post_data = await self.get_solution_details(solution['post_id'])

            if post_data.get('success'):
                body = post_data.get('post', {}).get('body', '')
                actions = self.extract_actions(body)

                solution['actions'] = actions
                solution['full_body'] = body[:500]  # 只保留前500字符
                detailed_solutions.append(solution)

        return detailed_solutions

    def write_discovery(
        self,
        discovery: Dict[str, Any],
        effective: Optional[bool] = None
    ):
        """
        将论坛发现写入知识库

        Args:
            discovery: 发现的内容
            effective: 是否有效（None表示待验证）
        """
        self._write_to_daily(discovery, effective)
        self._write_to_research_memory(discovery, effective)

    def _write_to_daily(self, discovery: Dict[str, Any], effective: Optional[bool]):
        """写入每日记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = KNOWLEDGE_BASE_DIR / "daily" / f"{today}.md"

        # 确保目录存在
        daily_file.parent.mkdir(parents=True, exist_ok=True)

        # 读取现有内容
        existing_content = ""
        if daily_file.exists():
            existing_content = daily_file.read_text()

        # 构建新条目
        time_str = datetime.now().strftime("%H:%M")
        effective_str = "有效" if effective else ("无效" if effective is not None else "待验证")

        new_entry = f"""
### 论坛反馈 [{time_str}]
- 问题类型: {discovery.get('problem_type', 'unknown')}
- 搜索词: "{discovery.get('search_query', '')}"
- 来源: {discovery.get('title', '')} (post_id: {discovery.get('post_id', '')}, 投票: {discovery.get('votes', 0)})
- 提取的操作: {', '.join(discovery.get('actions', []))}
- 有效性: {effective_str}
"""

        # 追加到文件
        with open(daily_file, 'a') as f:
            f.write(new_entry)

    def _write_to_research_memory(self, discovery: Dict[str, Any], effective: Optional[bool]):
        """写入结构化知识库"""
        # 读取现有数据
        data = {'forum_insights': []}
        if RESEARCH_MEMORY_FILE.exists():
            try:
                with open(RESEARCH_MEMORY_FILE, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass

        # 构建新条目
        insight = {
            'timestamp': datetime.now().isoformat(),
            'problem_type': discovery.get('problem_type', 'unknown'),
            'search_query': discovery.get('search_query', ''),
            'source_title': discovery.get('title', ''),
            'source_url': discovery.get('link', ''),
            'post_id': discovery.get('post_id', ''),
            'source_votes': discovery.get('votes', 0),
            'actions': discovery.get('actions', []),
            'snippet': discovery.get('snippet', ''),
            'effective': effective  # None表示待验证
        }

        data['forum_insights'].append(insight)

        # 写入文件
        try:
            with open(RESEARCH_MEMORY_FILE, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to write to research_memory.json: {e}")

    def write_result(self, discovery: Dict[str, Any], result_metrics: Dict[str, Any]):
        """
        写入优化结果到知识库

        Args:
            discovery: 论坛发现
            result_metrics: 优化后的指标 {'sharpe': X, 'fitness': Y, ...}
        """
        # 判断是否有效：Sharpe提升或Fitness提升
        before_sharpe = discovery.get('before_sharpe', 0)
        after_sharpe = result_metrics.get('sharpe', 0)

        effective = (after_sharpe > before_sharpe) if before_sharpe else None

        # 添加结果信息到discovery
        discovery['after_sharpe'] = after_sharpe
        discovery['after_fitness'] = result_metrics.get('fitness', 0)
        discovery['after_turnover'] = result_metrics.get('turnover', 0)
        discovery['result_sharpe_improvement'] = after_sharpe - before_sharpe if before_sharpe else 0

        self.write_discovery(discovery, effective)


# 便捷函数
async def search_forum_solutions(
    problem_type: str,
    alpha_metrics: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    搜索论坛获取解决方案

    Args:
        problem_type: 问题类型
        alpha_metrics: Alpha指标

    Returns:
        List[dict]: 解决方案列表
    """
    from worldquant_brain.scripts.core.api_client import RetryableBrainClient

    client = RetryableBrainClient()
    service = ForumFeedbackService(client)

    return await service.search_and_extract_actions(problem_type, alpha_metrics)


if __name__ == "__main__":
    # 测试代码
    import asyncio

    async def test():
        from worldquant_brain.scripts.core.api_client import RetryableBrainClient

        client = RetryableBrainClient()
        service = ForumFeedbackService(client)

        # 测试搜索
        solutions = await service.search_before_optimize(
            problem_type="fitness_low",
            alpha_metrics={'fitness': 0.5, 'dataset': 'analyst4'}
        )

        print(f"Found {len(solutions)} solutions")
        for s in solutions[:3]:
            print(f"  - {s.get('title')}: {s.get('votes')} votes")

    asyncio.run(test())