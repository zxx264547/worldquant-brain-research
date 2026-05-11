#!/usr/bin/env python3
"""知识图谱引导挖掘策略 — 利用wq-forum-rag知识图谱发现新模式"""

from pathlib import Path

from worldquant_brain.strategies.base import MiningStrategy
from worldquant_brain.engine import ExpressionTemplates

FORUM_DB = Path(__file__).parent.parent / "data" / "forum.sqlite3"


class KnowledgeGuidedStrategy(MiningStrategy):
    """基于知识图谱的Alpha探索

    流程:
        1. 搜索知识库找成功Alpha模式
        2. 用graph_query遍历关联的知识节点
        3. 从图谱中提取新的候选方向
    """

    name = "knowledge_guided"
    description = "知识图谱引导: 从成功模式推断新方向"

    async def pre_generate_research(self, context: dict) -> dict:
        """搜索知识库, 用知识图谱增强上下文"""
        if not FORUM_DB.exists():
            return context

        try:
            from wq_forum_rag.evolution import EvolutionService
            evo = EvolutionService(str(FORUM_DB))

            # 搜索已沉淀的成功Alpha
            results = evo.search_knowledge("sharpe high alpha", top_k=10)

            discovered = []
            for r in results:
                slug = r.get('slug', '')
                summary = r.get('summary', '')
                if slug and summary:
                    # 遍历知识图谱找关联节点
                    try:
                        graph = evo.graph_query(slug, depth=1)
                        related = graph.get('nodes', [])
                        for node in related:
                            if node.get('slug') != slug:
                                discovered.append({
                                    'source': slug,
                                    'related': node.get('slug'),
                                    'relation': node.get('relation_type', ''),
                                    'summary': node.get('summary', summary[:100])
                                })
                    except Exception:
                        pass

            context['kg_discoveries'] = discovered
            context['kg_successful_patterns'] = results

            print(f"[{self.name}] 知识图谱: {len(results)} 个成功模式, "
                  f"{len(discovered)} 个关联发现")

        except Exception as e:
            print(f"[{self.name}] 知识图谱异常: {e}")

        return context

    def generate_candidates(self, context: dict):
        discoveries = context.get('kg_discoveries', [])

        # 从知识图谱发现中提取技术信号模式
        techs_from_kg = set()
        for d in discoveries:
            related = d.get('related', '')
            summary = d.get('summary', '')
            text = f"{related} {summary}"

            # 从文本中提取常见技术信号
            for signal in ['beta', 'vol', 'rsi', 'momentum', 'trend',
                           'volume_trend', 'corr', 'ts_delta', 'ts_mean']:
                if signal in text.lower():
                    techs_from_kg.add(signal)

        # 从成功模式中提取表达式片段
        successful = context.get('kg_successful_patterns', [])
        for pat in successful:
            body = pat.get('body', '') or pat.get('summary', '')
            if 'ts_corr' in body:
                techs_from_kg.add('corr')
            if 'ts_std_dev' in body:
                techs_from_kg.add('vol')
            if 'ts_delta(close' in body:
                techs_from_kg.add('momentum')

        # 如果没有发现, 使用默认集合
        if not techs_from_kg:
            techs_from_kg = {'corr', 'vol', 'momentum'}

        # 用发现的技术信号生成候选
        bases = [
            ("eps_252_09", ExpressionTemplates.eps_basic()),
            ("eps_win180", ExpressionTemplates.eps_basic(180)),
        ]

        tech_map = {
            'corr': ("beta_120", ExpressionTemplates.tech_beta(120)),
            'vol': ("vol_120", ExpressionTemplates.tech_vol(120)),
            'momentum': ("mom_60", ExpressionTemplates.tech_momentum(60)),
            'rsi': ("rsi_14", ExpressionTemplates.tech_rsi(14)),
        }

        weights = [0.15, 0.2, 0.25, 0.3]
        for signal_name in techs_from_kg:
            if signal_name not in tech_map:
                continue
            tech_entry = tech_map[signal_name]
            for base_name, base_expr in bases:
                for w in weights:
                    expr = f"(({base_expr})) * (1 + (({tech_entry[1]})) * {w})"
                    name = f"kg_{base_name}_{tech_entry[0]}_w{int(w*100)}"
                    yield expr, {}, name
