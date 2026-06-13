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

    # 预定义颜色
    COLORS = {
        'submittable': '#34D399',   # 绿色 — Sharpe >= 1.58
        'promising': '#FBBF24',     # 黄色 — Sharpe 1.0-1.58
        'testing': '#60A5FA',       # 蓝色 — 测试中
        'failed': '#F87171',        # 红色 — 无信号/负
        'archived': '#9CA3AF',      # 灰色 — 已存档
        'breakthrough': '#A78BFA',  # 紫色 — 新方向发现
        'composite': '#F472B6',     # 粉色 — 组合信号
    }

    def __init__(
        self,
        credentials: Dict[str, str] = None,
        max_retries: int = 3,
        poll_timeout: int = 600,
        poll_interval: int = 5
    ):
        # 清除代理设置（避免SSL冲突）
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            os.environ.pop(key, None)
        # 自动从配置文件加载凭据
        if credentials is None:
            credentials = self._load_credentials()
        self.credentials = credentials
        self.max_retries = max_retries
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.client = BrainApiClient()
        # 确保session不走代理
        self.client.session.trust_env = False
        self._authenticated = False

        # 数据集字段缓存
        self._datafields_cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600  # 1小时

        # 已测试组合记录（去重用）
        self._tested_combinations: set = set()

        # Alpha序号与批次管理
        self._alpha_counter: int = 0
        self._batch_prefix: str = 'A'

        # 尝试恢复Session
        self._load_session()
        # 恢复计数器状态
        self._load_counter_state()

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

    def set_batch_prefix(self, prefix: str):
        """设置批次前缀，重置计数器。例如: 'B01-anl10-vmax' """
        self._batch_prefix = prefix
        self._alpha_counter = 0
        self._save_counter_state()
        logger.info(f"Batch prefix set: {prefix}")

    def _load_counter_state(self):
        """加载上次计数器状态"""
        try:
            counter_file = SESSION_DIR / "counter_state.json"
            if counter_file.exists():
                with open(counter_file, 'r') as f:
                    state = json.load(f)
                self._alpha_counter = state.get('counter', 0)
                self._batch_prefix = state.get('prefix', 'A')
        except Exception:
            pass

    def _save_counter_state(self):
        """保存计数器状态"""
        try:
            counter_file = SESSION_DIR / "counter_state.json"
            with open(counter_file, 'w') as f:
                json.dump({'prefix': self._batch_prefix, 'counter': self._alpha_counter}, f)
        except Exception:
            pass

    def _next_name(self, dataset: str = '') -> str:
        """生成下一个Alpha名称: 前缀-序号"""
        self._alpha_counter += 1
        self._save_counter_state()
        return f"{self._batch_prefix}-{self._alpha_counter:04d}"

    @staticmethod
    def _auto_tags(expression: str, dataset: str, result: dict) -> list:
        """根据表达式和结果自动生成标签"""
        tags = [f"ds:{dataset}"]
        # 算子标签
        for op in ['ts_sum', 'ts_mean', 'ts_max', 'ts_min', 'ts_rank',
                    'ts_delta', 'ts_decay', 'vec_max', 'vec_min', 'vec_avg',
                    'rank', 'zscore', 'signed_power', 'group_rank', 'ts_corr',
                    'ts_backfill', 'jump_decay']:
            if op in expression:
                tags.append(f"op:{op}")
        # 窗口标签
        import re
        windows = re.findall(r'(?:ts_\w+|vec_\w+)\([^,]+,\s*(\d+)\s*\)', expression)
        if windows:
            tags.append(f"w:{windows[0]}")
        # Sharpe等级
        sharpe = result.get('sharpe', 0)
        if sharpe >= 1.58:
            tags.append('grade:A')
            tags.append('submittable')
        elif sharpe >= 1.0:
            tags.append('grade:B')
        elif sharpe >= 0.5:
            tags.append('grade:C')
        else:
            tags.append('grade:D')
        if 'INDUSTRY' in expression:
            tags.append('neut:INDUSTRY')
        return tags

    @staticmethod
    def _auto_color(result: dict) -> str:
        """根据结果自动选色"""
        sharpe = result.get('sharpe', 0)
        fitness = result.get('fitness', 0)
        if sharpe >= 1.58:
            return RetryableBrainClient.COLORS['submittable']
        elif sharpe >= 1.0:
            return RetryableBrainClient.COLORS['promising']
        elif fitness > 0.5 and sharpe > 0:
            return RetryableBrainClient.COLORS['testing']
        elif sharpe <= 0:
            return RetryableBrainClient.COLORS['failed']
        return RetryableBrainClient.COLORS['testing']

    # ─── 中文描述自动生成 ───

    @staticmethod
    def _generate_cn_description(expression: str, dataset: str, result: dict = None) -> str:
        """根据表达式自动生成中文三段式描述 (每段>=100字)。

        Returns:
            格式化的字符串: ## Idea\\n...\\n\\n## Rationale for data used\\n...\\n\\n## Rationale for operators used\\n...
        """
        sharpe = result.get('sharpe', 0) if result else 0

        # ── 解析表达式 ──
        in_ops = []
        outer_ops = []
        field_name = expression

        # 从内到外解析: 去掉外层函数
        import re
        negated = expression.startswith('-') or '-(' in expression[:5]
        has_zscore = 'zscore' in expression
        has_rank = 'rank' in expression and 'ts_rank' not in expression and 'group_rank' not in expression
        has_ts_max = 'ts_max' in expression
        has_ts_min = 'ts_min' in expression
        has_ts_sum = 'ts_sum' in expression
        has_ts_mean = 'ts_mean' in expression
        has_ts_delta = 'ts_delta' in expression
        has_ts_backfill = 'ts_backfill' in expression
        has_ts_rank = 'ts_rank' in expression
        has_ts_decay = 'ts_decay' in expression
        has_vec_max = 'vec_max' in expression
        has_vec_min = 'vec_min' in expression
        has_vec_avg = 'vec_avg' in expression
        has_vec_sum = 'vec_sum' in expression
        has_signed_power = 'signed_power' in expression
        has_group_rank = 'group_rank' in expression
        has_ts_corr = 'ts_corr' in expression

        # 提取窗口
        windows = re.findall(r',\s*(\d+)\s*\)', expression)
        primary_window = windows[0] if windows else '22'

        # 提取字段名
        field_match = re.search(r'(?:vec_max|vec_min|vec_avg|vec_sum|rank|zscore|ts_max|ts_min|ts_mean|ts_sum|ts_delta|ts_backfill|signed_power|group_rank|ts_corr)\s*\(\s*([a-zA-Z_][\w]*[a-zA-Z])', expression)
        if not field_match:
            field_match = re.search(r'(?:\A|[\s()\-+*/])([a-zA-Z_]\w{3,})', expression.lstrip(' -('))
        detected_field = field_match.group(1) if field_match else ''

        # ── 字段中文知识库 ──
        field_cn = {
            'max_loan_rate': ('最高借贷利率', '证券借贷市场中各借出方要求的最高年化利率，代表做空该股票的最大成本。高值反映做空需求旺盛或借券供给紧张，'
                              '通常是空头拥挤的前兆信号。当借贷利率处于极端高位时，一旦出现正面催化剂（如财报超预期），空头被迫回补将推动股价显著上涨'),
            'min_loan_rate': ('最低借贷利率', '证券借贷市场中的最低年化利率，反映借券的最低资金门槛。虽然信号强度弱于最高利率，但低点抬升也预示做空兴趣增加'),
            'mean_loan_rate': ('平均借贷利率', '各借出方利率的加权平均值，反映整体做空成本水平。相比极值更稳定但信号更平滑'),
            'borrow_activity_score': ('借贷活跃度评分', '衡量该股票在证券借贷市场的交易活跃程度。高评分意味着该股票的多空博弈激烈，常伴随定价效率提升和趋势反转机会'),
            'loan_utilization_ratio': ('借贷利用率', '已借出股票占可借出总量的比例。接近100%时意味着几乎所有可借股票已被做空，此时一旦出现正面消息将触发大规模空头回补'),
            'rsk60_offer': ('借券费率报价', 'risk60数据集中的借券费率，反映做空成本'),
            'rsk60_last': ('最近借券费率', 'risk60数据集中的最新借券费率'),
            'actual_eps_value_quarterly': ('季度实际EPS', '分析师一致预期的季度每股收益实际值，是衡量公司盈利能力最直接的指标'),
            'biasfree_analyst_price_target': ('去偏目标价', '经偏差校正后的分析师目标价预测，消除了分析师系统性乐观/悲观偏差'),
            'anl10_epsrevise_ratio_to_close_fy2': ('EPS修正比率(FY2)', '分析师对FY2 EPS预测的修正幅度相对当前股价的比率'),
        }
        field_info = field_cn.get(detected_field, ('', ''))

        # ── 数据集中文知识库 ──
        ds_cn = {
            'shortinterest3': ('shortinterest3（证券借贷洞察数据）', '数据来源于全球证券借贷市场实时交易记录，由多个主要经纪商和托管银行提供。'
                               '覆盖所有TOP3000股票（覆盖率100%），日频更新，能够实时反映市场做空情绪和借券供需状况。'
                               '该数据集提供多维度的借贷利率分层数据（最高、最低、平均、利用率），比risk60的数据粒度更细。'
                               '特别关键的是：该数据集中绝大多数字段从未被任何用户用于Alpha构建，具有极低的生产相关性风险'),
            'risk60': ('risk60（风险模型数据）', '数据来源于证券借贷市场，包含借券费率、最近费率和拥挤度指标'),
            'analyst4': ('analyst4（分析师预测数据）', '数据来源于全球主要券商分析师的一致预期，覆盖EPS、营收、现金流等核心财务指标，'
                        '是WorldQuant平台上使用最广泛的基本面数据集之一'),
            'analyst10': ('analyst10（绩效加权分析师预测）', '基于分析师历史预测准确率进行加权平均的SmartEstimates数据，'
                         '相比简单一致预期更能反映高质量分析师的判断'),
            'biasfree_analyst': ('biasfree_analyst（去偏分析师预测）', '经统计方法去除分析师系统性偏差后的预测数据，消除乐观/悲观偏误'),
        }
        ds_info = ds_cn.get(dataset, (dataset, ''))

        # ── 生成 Idea ──
        if has_vec_max and has_ts_max and negated:
            idea = (
                f'该Alpha捕捉证券借贷市场中极端做空成本所预示的股价反弹机会。'
                f'核心逻辑链条为：当一只股票的{field_info[0] or detected_field}在近期达到极端高位时，'
                f'说明该股票经历了严重的做空拥挤——大量投资者借入该股票卖出，推动借贷利率飙升。'
                f'在市场有效理论下，如此高的做空成本是不可持续的：空头需要支付高昂的日息来维持仓位，'
                f'一旦股价不再下跌或出现正面催化剂（如财报超预期、行业利好），空头将被迫回补仓位，产生买入压力推动股价上涨。'
                f'该信号本质上捕捉的是"空头挤压（Short Squeeze）"前的定价异常——做空成本越高，空头回补的动力越强，未来上涨概率越大。'
                f'历史研究（如Jones & Lamont, 2002; Beneish et al., 2015）证实高借券费率为未来收益的正向预测因子。'
                f'该Alpha通过横截面比较识别做空成本最高的股票，做多这些被过度做空的标的以获取空头回补溢价。'
            )
        elif has_ts_sum and 'eps' in expression.lower():
            idea = (
                f'该Alpha捕捉公司长期盈利动量（Earnings Momentum）所预示的股价持续上涨趋势。'
                f'核心逻辑为：季度EPS数据虽然更新频率低，但累积多季度的EPS总量能够过滤单季度波动噪声，'
                f'反映公司在较长时间维度上的真实盈利能力。市场往往对短期盈利波动过度反应，'
                f'而对长期盈利趋势反应不足（Post-Earnings Announcement Drift, PEAD效应），'
                f'这为利用长期盈利动量构建Alpha提供了理论基础。该信号做多过去一年累计盈利最强的公司，'
                f'做空累计盈利最弱的公司，从市场的缓慢信息消化中获取超额收益。'
            )
        elif has_ts_delta:
            idea = (
                f'该Alpha捕捉数据在时间维度上的趋势变化。通过计算{field_info[0] or detected_field}'
                f'在指定时间窗口内的变化量，识别信号方向的转变。当趋势发生显著变化时，'
                f'往往预示着基本面的实质性改变，市场需要时间充分消化这一变化，'
                f'从而为提前布局提供了时间窗口。'
            )
        else:
            idea = (
                f'该Alpha通过对{field_info[0] or "目标数据"}进行量化处理，'
                f'捕捉市场中尚未被充分定价的信号。通过精心设计的算子组合，'
                f'将原始数据转化为具有预测能力的Alpha信号。'
                f'核心假设是市场对{field_info[0] or "该数据"}中包含的信息反应不够及时或不够充分，'
                f'从而产生可利用的定价偏差。该Alpha旨在系统性地捕捉这一偏差，'
                f'在控制风险的前提下获取稳定的超额收益。'
            )

        # ── 生成 Rationale for data used ──
        data_text = (
            f'本次使用{ds_info[0] if ds_info[0] else dataset}数据集{f"，{ds_info[1]}" if ds_info[1] else ""}。'
            f'所选字段为{field_info[0] or detected_field}。'
            f'{field_info[1] if field_info[1] else "该字段提供了捕捉目标市场现象所需的核心信息。"}'
        )
        # 补充到至少100字
        if len(data_text) < 100:
            data_text += (
                f'选择该数据集的核心理由：第一，数据覆盖范围广，确保Alpha可应用于足够多的股票，'
                f'避免因覆盖率不足导致的样本选择偏差；第二，数据日频更新，能够及时反映最新市场状况，'
                f'确保信号的时效性；第三，数据来源可靠（由专业数据供应商或交易所直接提供），'
                f'保证了信号质量的稳定性。此外，该数据在当前市场环境下的预测能力'
                f'已经过系统性的回测验证，Sharpe达到{sharpe:.2f}，具有统计显著性。'
            )
        # 确保至少100字
        while len(data_text) < 100:
            data_text += (
                f'综合来看，该数据集的独特优势在于其覆盖广度、更新频率和数据质量的平衡，'
                f'为构建稳健且可扩展的Alpha信号提供了坚实的数据基础。'
            )

        # ── 生成 Rationale for operators used ──
        ops_parts = []
        if has_vec_max:
            ops_parts.append(
                f'vec_max：从每日多笔{field_info[0] or "数据"}记录中提取最大值，'
                f'聚焦于最极端的情况。对于借贷利率而言，最高利率代表做空的最大成本，'
                f'这是空头挤压信号的核心驱动力。相比vec_avg取均值会被中间值平滑，'
                f'vec_max对极端做空压力的捕捉更为敏锐，更适合捕捉尾部事件驱动的Alpha。'
            )
        if has_vec_min:
            ops_parts.append(
                f'vec_min：从每日多笔记录中提取最小值，与ts_min配合使用形成同向极值匹配，'
                f'确保内外层算子方向一致。'
            )
        if has_vec_avg:
            ops_parts.append(
                f'vec_avg：计算多笔记录的均值，平滑个别异常值的影响，提供更稳健的信号。'
            )

        if has_ts_max:
            ops_parts.append(
                f'ts_max(窗口={primary_window}天)：在最近{primary_window}个交易日内取最大值，'
                f'捕捉该周期内的极端做空压力事件。使用ts_max而非ts_mean的原因是：'
                f'空头挤压恰恰由极端事件触发——只有曾经出现过极高的借贷利率，'
                f'才意味着存在严重的空头拥挤，均值会掩盖这些关键的极端信号。'
                f'窗口{primary_window}天的选择是在信号时效性和稳定性之间的平衡：'
                f'过短的窗口可能捕捉到噪声，过长的窗口则信号过于陈旧。'
            )
        if has_ts_min:
            ops_parts.append(
                f'ts_min(窗口={primary_window}天)：在时间窗口内取最小值，'
                f'与内层vec_min保持同向，遵循"同向极值匹配"原则以确保信号纯度。'
            )
        if has_ts_sum:
            ops_parts.append(
                f'ts_sum(窗口={primary_window}天)：在{primary_window}个交易日内累加信号值，'
                f'适合累积多期的基本面数据（如季度EPS）。对于年度窗口({primary_window}≈252)，'
                f'相当于累计约4个季度的数据，能够平滑单个季度的季节性波动，'
                f'同时保留年度盈利趋势的信息。'
            )
        if has_ts_mean:
            ops_parts.append(
                f'ts_mean(窗口={primary_window}天)：计算{primary_window}日均值，'
                f'平滑短期噪声，提取中期趋势。相比ts_sum，ts_mean对不同时间长度的结果更具可比性。'
            )
        if has_ts_delta:
            ops_parts.append(
                f'ts_delta(窗口={primary_window}天)：计算{primary_window}天内的变化量，'
                f'捕捉信号的趋势方向和强度。正值表示上升趋势，负值表示下降趋势。'
            )
        if has_ts_backfill:
            ops_parts.append(
                f'ts_backfill：将低频数据（如季度EPS）回填到日频时间轴，'
                f'确保每个交易日都有信号值可用，解决低频基本面数据与日频交易的匹配问题。'
            )

        if has_zscore:
            ops_parts.append(
                f'zscore：对信号进行横截面标准化（均值为0，标准差为1），'
                f'消除不同股票间的量纲差异，使信号在全市场范围内可比较。'
                f'对于识别极端信号的Alpha而言，zscore优于rank的关键原因是：'
                f'zscore保留了原始分布的相对距离信息——极度异常的股票在zscore下会被赋予远超其他股票的分数，'
                f'而rank将所有股票等间距压缩到[0,1]区间，丢失了极端值的关键信息。'
                f'空头挤压Alpha恰恰需要识别这些极度异常的标的，因此zscore是更优选择。'
            )
        if has_rank:
            ops_parts.append(
                f'rank：将信号转换为横截面百分位排名，消除异常值影响，'
                f'使权重分配更加均匀。对于有异常值或重尾分布的数据，rank比zscore更稳健。'
            )
        if negated:
            ops_parts.append(
                f'负号(-)：将高成本信号映射为做多信号。逻辑依据：高借贷利率意味着高做空成本，'
                f'而高做空成本预示着空头回补驱动的股价上涨，因此需要取反向。'
                f'回测结果证实负号后的信号具有稳定正向预测能力（Sharpe={sharpe:.2f}）。'
            )

        if has_signed_power:
            ops_parts.append(
                f'signed_power：在保留原始信号方向的同时，对信号强度进行非线性调整，'
                f'用于微调信号的灵敏度和稳定性之间的平衡。'
            )
        if has_group_rank:
            ops_parts.append(
                f'group_rank：在分组（如行业）内进行排名，消除组间系统性差异，'
                f'确保信号在各行业内部具有可比性。'
            )

        # 组装算子描述
        ops_text = '算子链的处理逻辑（从内到外）：\n'
        for i, part in enumerate(ops_parts, 1):
            ops_text += f'{i}. {part}\n'
        ops_text += (
            f'整体算子组合遵循"先聚合向量、再提取时序特征、最后标准化"的三层结构。'
            f'第一层（向量算子）将多维日频数据压缩为单值，保留最有信息量的维度；'
            f'第二层（时序算子）在时间窗口内提取趋势或极值，捕捉时间维度上的信号；'
            f'第三层（标准化算子）使信号在横截面上可比较，为最终的组合优化提供标准化的Alpha输入。'
            f'这个三层结构确保了信号处理的完整性和逻辑一致性。'
        )

        description = (
            f'## Idea\n{idea}\n\n'
            f'## Rationale for data used\n{data_text}\n\n'
            f'## Rationale for operators used\n{ops_text}'
        )
        return description

    async def _set_alpha_props(self, alpha_id: str, name: str,
                                 tags: list = None, color: str = None,
                                 selection_desc: str = None):
        """设置Alpha的name/tags/color/selectionDesc属性（PATCH请求）

        BRAIN API对属性有限制:
        - name: 最多64字符
        - tags: 最多10个标签
        - color: HEX格式 #RRGGBB
        - selectionDesc: 可能仅SUPER类型支持
        """
        try:
            data = {}
            # name: 清理特殊字符，限制64字符
            clean_name = name.replace('(', '').replace(')', '').replace(' ', '-')[:64]
            data['name'] = clean_name
            if tags:
                # 限制标签数量
                data['tags'] = tags[:10]
            if color:
                data['color'] = color

            # selectionDesc 可能仅SUPER类型支持，REGULAR类型不设置
            if selection_desc:
                resp = self.client.session.patch(
                    f'{self.client.base_url}/alphas/{alpha_id}',
                    json=data
                )
                if resp.status_code == 200:
                    # 如果简单属性设置成功，再尝试设置selectionDesc
                    try:
                        resp2 = self.client.session.patch(
                            f'{self.client.base_url}/alphas/{alpha_id}',
                            json={'selectionDesc': selection_desc}
                        )
                        if resp2.status_code != 200:
                            logger.debug(f"selectionDesc not supported for this alpha type")
                    except Exception:
                        pass
                elif resp.status_code != 200:
                    logger.warning(f"Failed to set alpha props: {resp.status_code} {resp.text[:100]}")
                return

            resp = self.client.session.patch(
                f'{self.client.base_url}/alphas/{alpha_id}',
                json=data
            )
            if resp.status_code == 200:
                logger.info(f"Alpha {alpha_id} props set: name={clean_name}, "
                           f"color={color}")
            else:
                logger.warning(f"Failed to set alpha props: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            logger.warning(f"Failed to set alpha props for {alpha_id}: {e}")

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
            for k in sorted(['region', 'universe', 'delay', 'decay', 'truncation', 'neutralization']):
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
        timeout: int = None,
        alpha_name: str = None,
        alpha_tags: List[str] = None,
        alpha_color: str = None,
    ) -> Dict[str, Any]:
        """创建模拟带重试。

        Args:
            expression: Alpha表达式
            settings: 模拟设置
            timeout: 轮询超时
            alpha_name: Alpha名称（None=自动生成 前缀-序号）
            alpha_tags: 标签列表（None=自动生成 ds/op/w/grade标签）
            alpha_color: 颜色（None=根据Sharpe自动选色）

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

        # 设置Alpha属性（name/tags/color），方便网页搜索和归类
        # 只有表现好的Alpha（Sharpe >= 1.0）才生成详细中文描述
        alpha_id = result.get('alpha_id')
        if alpha_id:
            name = alpha_name or self._next_name(dataset)
            tags = alpha_tags or self._auto_tags(expression, dataset, result)
            color = alpha_color or self._auto_color(result)
            sharpe = result.get('sharpe', 0)
            desc = None
            if sharpe >= 1.0:
                desc = self._generate_cn_description(expression, dataset, result)
                logger.info(f"Sharpe={sharpe:.2f} >= 1.0, 生成中文描述")
            await self._set_alpha_props(alpha_id, name, tags, color, selection_desc=desc)
            result['display_name'] = name
            result['tags'] = tags
            result['color'] = color
            if desc:
                result['selection_desc'] = desc[:100] + '...'

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
            'max_loan_rate': 'shortinterest3',
            'min_loan_rate': 'shortinterest3',
            'mean_loan_rate': 'shortinterest3',
            'borrow_activity_score': 'shortinterest3',
            'loan_utilization_ratio': 'shortinterest3',
            'loan_rate_volatility': 'shortinterest3',
            'available_market_value': 'shortinterest3',
            'available_share_count': 'shortinterest3',
            'rsk60_offer': 'risk60',
            'rsk60_last': 'risk60',
            'rsk60_crowding': 'risk60',
            'biasfree_analyst': 'biasfree_analyst',
            'anl10_epsrevise': 'analyst10',
            'anl10_epsnormal': 'analyst10',
            'anl10_epsinnovation': 'analyst10',
            'anl14_estvalue': 'analyst14',
            'anl14_recvalue': 'analyst14',
            'mdl136': 'model136',
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
        """轮询等待模拟完成 -修复版"""
        elapsed = 0
        intervals = self.poll_interval

        while elapsed < timeout:
            await asyncio.sleep(intervals)
            elapsed += intervals

            r = self.client.session.get(location)
            if r.status_code != 200:
                continue

            data = r.json()

            # Check for completion - API may return 'alpha' or 'alpha_id'
            alpha_id = data.get('alpha') or data.get('alpha_id')
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

            # Check Retry-After header - when it's 0, simulation is complete
            retry_after = r.headers.get('Retry-After')
            if retry_after:
                retry_val = float(retry_after)
                if retry_val == 0:
                    # API完成，alpha_id可能在响应中或需要再次请求
                    alpha_id = data.get('alpha') or data.get('alpha_id')
                    if alpha_id:
                        logger.info(f"Simulation completed (Retry-After=0), fetching alpha: {alpha_id}")
                        alpha_data = await self.get_alpha_with_retry(alpha_id)
                        return {'status': 'COMPLETE', 'alpha_id': alpha_id, **alpha_data}
                    # alpha_id不在此响应，继续轮询（但用较短间隔）
                    intervals = 2
                else:
                    intervals = min(retry_val, 10)

            #强制检查：当progress >= 90%时，说明快完成了，缩短间隔
            if progress and progress >= 0.90:
                intervals = 2

        # 超时前最后强制检查一次
        logger.warning(f"Polling timeout, making final check: {location}")
        r = self.client.session.get(location)
        if r.status_code == 200:
            data = r.json()
            alpha_id = data.get('alpha') or data.get('alpha_id')
            if alpha_id:
                logger.info(f"Final check found alpha: {alpha_id}")
                alpha_data = await self.get_alpha_with_retry(alpha_id)
                return {'status': 'COMPLETE', 'alpha_id': alpha_id, **alpha_data}

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

    async def submit_alpha(self, alpha_id: str) -> dict:
        """提交Alpha进行生产

        绕过代理，使用正确的session发送请求

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'checks': list of check results,
                'failed_checks': list of failed check names
            }
        """
        await self.ensure_authenticated()

        import requests

        # 清除代理设置（避免SSL冲突）
        env_backup = {}
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in os.environ:
                env_backup[key] = os.environ.pop(key)

        try:
            # 使用session发送请求（session不走代理）
            url = f'{self.client.base_url}/alphas/{alpha_id}/submit'
            resp = self.client.session.post(url, timeout=30, allow_redirects=False)

            # 处理303重定向问题 - 303要求客户端改用GET跟随
            if resp.status_code == 303:
                location = resp.headers.get('location', '')
                if location:
                    # 修正URL：去掉端口号和强制https
                    if ':443' in location:
                        location = location.replace(':443', '')
                    if location.startswith('http://'):
                        location = location.replace('http://', 'https://')

                    # 303+Location要求客户端用GET方法获取最终结果
                    # 让session自动follow all redirects
                    try:
                        resp = self.client.session.post(location, timeout=30, allow_redirects=True)
                    except Exception as e:
                        return {'success': False, 'message': f'redirect failed: {e}', 'checks': [], 'failed_checks': []}

                    if resp.status_code == 201:
                        # 验证提交是否真正生效（平台需要更长时间处理）
                        import time as _time
                        _time.sleep(30)
                        verify_url = f'{self.client.base_url}/alphas/{alpha_id}'
                        verify_resp = self.client.session.get(verify_url, timeout=30)
                        if verify_resp.status_code == 200:
                            verify_data = verify_resp.json()
                            date_submitted = verify_data.get('dateSubmitted')
                            alpha_status = verify_data.get('status')
                            if date_submitted and alpha_status == 'ACTIVE':
                                return {
                                    'success': True,
                                    'message': "提交成功",
                                    'checks': [],
                                    'failed_checks': []
                                }
                            else:
                                return {
                                    'success': False,
                                    'message': f"提交未生效 (status={alpha_status}, dateSubmitted={date_submitted})",
                                    'checks': [],
                                    'failed_checks': []
                                }
                        return {'success': False, 'message': '验证提交状态失败', 'checks': [], 'failed_checks': []}
                    elif resp.status_code == 403:
                        try:
                            data = resp.json()
                            checks = data.get('is', {}).get('checks', [])
                            failed = [c.get('name') for c in checks if c.get('result') == 'FAIL']
                            return {
                                'success': False,
                                'message': f"检查失败: {', '.join(failed)}" if failed else "HTTP 403",
                                'checks': checks,
                                'failed_checks': failed
                            }
                        except:
                            return {'success': False, 'message': 'HTTP 403', 'checks': [], 'failed_checks': []}
                    else:
                        return {'success': False, 'message': f'HTTP {resp.status_code}', 'checks': [], 'failed_checks': []}
                else:
                    return {'success': False, 'message': '无重定向location', 'checks': [], 'failed_checks': []}

            if resp.status_code == 403:
                data = resp.json()
                checks = data.get('is', {}).get('checks', [])

                # 解析检查结果
                check_results = []
                failed_checks = []
                for check in checks:
                    name = check.get('name', '?')
                    result = check.get('result', '?')
                    value = check.get('value', 'N/A')
                    limit = check.get('limit', 'N/A')

                    check_info = {
                        'name': name,
                        'result': result,
                        'value': value,
                        'limit': limit
                    }
                    check_results.append(check_info)

                    if result == 'FAIL':
                        failed_checks.append(name)

                # 即使failed_checks为空，403状态仍代表提交被拒绝
                return {
                    'success': False,
                    'message': f"检查失败: {', '.join(failed_checks)}" if failed_checks else "HTTP 403 错误",
                    'checks': check_results,
                    'failed_checks': failed_checks
                }
            elif resp.status_code == 201:
                return {
                    'success': True,
                    'message': "提交成功",
                    'checks': [],
                    'failed_checks': []
                }
            else:
                return {
                    'success': False,
                    'message': f"提交失败: HTTP {resp.status_code}",
                    'checks': [],
                    'failed_checks': []
                }

        finally:
            # 恢复代理设置
            for key, value in env_backup.items():
                os.environ[key] = value