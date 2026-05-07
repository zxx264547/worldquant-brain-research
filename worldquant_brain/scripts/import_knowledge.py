#!/usr/bin/env python3
"""导入 knowledge_base 到 wq-forum-rag 知识库"""

import sys
sys.path.insert(0, '/home/zxx/worldQuant/worldquant_brain/wq_forum_rag/src')

from wq_forum_rag.evolution import EvolutionService

DB_PATH = '/home/zxx/worldQuant/worldquant_brain/data/forum.sqlite3'

def import_knowledge():
    evo = EvolutionService(DB_PATH)

    knowledge_pages = [
        {
            "slug": "ppa-factor-standards",
            "title": "PPA因子标准",
            "summary": "WorldQuant BRAIN PPA因子提交标准",
            "body": """PPA因子筛选标准：

| 指标 | 标准 | 说明 |
|------|------|------|
| PPC | < 0.5 | 核心门槛 |
| Sharpe | >= 1.0 | 建议 >= 1.05 |
| Fitness | > 0.5 | 必须 |
| Margin | > Turnover | 必须 |

优化建议：
- Fitness < 1.0：尝试 Decay=2, Neut=Industry, Trunc=0.01
- Turnover > 70%：使用 trade_when, Decay=3-5, ts_mean
- Weight Concentration：rank()包裹, Trunc=0.01
- Correlation Fail：改窗口, 换字段, 换算子""",
            "confidence": 0.95,
            "source_topic_ids": ["1677", "1678", "1679", "1680", "1681"]
        },
        {
            "slug": "dataset-quick-reference",
            "title": "数据集速查",
            "summary": "常用数据集频次排名及说明",
            "body": """数据集频次排名：
- pv1: 5次 - 价格/成交量
- pv87: 3次 - 综合技术面指标
- fundamental6: 2次 - 基本面数据
- analyst10: 1次 - 分析师数据
- wds: 1次 - 全球市场数据

常用场景：
| 数据集 | 说明 | 常用场景 |
|--------|------|----------|
| pv87 | 综合技术面指标 | 短期Alpha |
| mdl136 | 分析师评级 | 基本面Alpha |
| analyst10 | 分析师数据 | 评级类Alpha |
| pv1 | 价格/成交量 | 基础Alpha |
| pv13 | 价格/成交量扩展 | 波动率Alpha |
| fundamental6 | 基本面数据 | 价值Alpha |
| wds | 全球市场数据 | 宏观Alpha |""",
            "confidence": 0.90,
            "source_topic_ids": ["1677", "1678", "1679", "1680", "1681"]
        },
        {
            "slug": "template-functions",
            "title": "模板函数",
            "summary": "常用Alpha算子频次排名",
            "body": """Alpha常用算子频次排名：

| 算子 | 频次 | 用途 |
|------|------|------|
| rank() | 19 | 横截面排名 |
| ts_mean() | 17 | 时间序列均值 |
| winsorize() | 12 | 去极值 |
| ts_rank() | 11 | 时间序列排名 |
| decay_linear() | 10 | 线性衰减 |
| signed_power() | 9 | 符号幂变换 |
| ts_delta() | 8 | 时间序列变化 |
| correlation() | 3 | 相关性 |
| ts_corr() | 2 | 滚动相关性 |

注意：VECTOR类型字段不支持ts_mean/rank等算子""",
            "confidence": 0.90,
            "source_topic_ids": ["1677", "1678", "1679", "1680", "1681"]
        },
        {
            "slug": "alpha-optimization-tips",
            "title": "Alpha优化技巧",
            "summary": "实战经验总结",
            "body": """Alpha优化实战经验：

1. 不同风险中性化：
   - 常用crowding中性化，速度快，找到低PC alpha概率大
   - 信号测试先用crowding，确认有信号再试其他中性化

2. Fitness处理：
   - < 0.6：放弃
   - > 0.6：尝试group_op，优先group_rank和signed_power

3. 因子分散：
   - 不能只在一个category做因子
   - 避免容易过拟合的category如pv、model
   - 因子尽量分散在不同category

4. 其他技巧：
   - 模型越强，裸信号质量通常越高
   - 不要迷信AI一定能出结果
   - 用户阶段多提交alpha，累计够100个可提交super alpha""",
            "confidence": 0.85,
            "source_topic_ids": ["1677", "1678", "1679", "1680", "1681"]
        },
        {
            "slug": "troubleshooting-guide",
            "title": "故障排查表",
            "summary": "常见Alpha问题及解决方案",
            "body": """Alpha常见问题解决方案：

| 症状 | 解决方案 |
|------|---------|
| Fitness < 1.0 | Decay=2, Neut=Industry, Trunc=0.01 |
| Turnover > 70% | trade_when, Decay=3-5, ts_mean |
| Weight Concentration | rank()包裹, Trunc=0.01 |
| Correlation Fail | 改窗口, 换字段, 换算子 |

增量复杂度原则：
- 0-op: rank/zscore（裸信号）
- 1-op: ts_mean/ts_decay/ts_delta
- 2-op+: ts_rank(ts_delta())等嵌套

时间窗口仅用：5, 22, 66, 120, 252, 504""",
            "confidence": 0.90,
            "source_topic_ids": ["1677", "1678", "1679", "1680", "1681"]
        },
    ]

    for page in knowledge_pages:
        try:
            result = evo.propose_knowledge_page(
                slug=page["slug"],
                title=page["title"],
                summary=page["summary"],
                body=page["body"],
                source_topic_ids=page["source_topic_ids"],
                confidence=page["confidence"],
                auto_publish=True,
            )
            status = "published" if result["auto_published"] else "draft"
            print(f"✓ {page['slug']} ({status})")
        except Exception as e:
            print(f"✗ {page['slug']}: {e}")

if __name__ == "__main__":
    import_knowledge()
