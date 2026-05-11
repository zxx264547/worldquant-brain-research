#!/usr/bin/env python3
"""挖掘策略基类"""

from abc import ABC, abstractmethod
from typing import Iterator


class MiningStrategy(ABC):
    """Alpha挖掘策略基类

    每个策略需要实现 generate_candidates() 方法。
    引擎负责回测执行、结果存储、去重、知识沉淀。

    生命周期:
        1. pre_generate_research(context) — 可选: 搜索知识库
        2. generate_candidates(context) — 必须: 生成候选表达式
        3. on_result(result) — 可选: 单个结果回调
        4. on_batch_complete(results) — 可选: 批次完成回调
    """

    name: str = "base"
    description: str = "基础策略"

    async def pre_generate_research(self, context: dict) -> dict:
        """生成候选前: 搜索知识库获取相关经验

        子类可重写以定制搜索策略。
        返回增强后的上下文 (合并 knowledge_context)。
        """
        knowledge = context.get('knowledge_context', {})
        if knowledge:
            patterns = knowledge.get('key_patterns', [])
            if patterns:
                print(f"[{self.name}] 知识增强: {len(patterns)} 条已知模式")
        return context

    @abstractmethod
    def generate_candidates(self, context: dict) -> Iterator[tuple]:
        """生成候选 (expression, settings, name) 三元组

        Args:
            context: 上下文 (可能包含 knowledge_context 知识增强)

        Yields:
            (expression, settings_override, name) 元组
        """
        yield from ()  # pragma: no cover

    def on_result(self, result: dict):
        """单个Alpha结果回调 — 子类可重写"""
        pass

    def on_batch_complete(self, results: list[dict]):
        """批次完成回调 — 子类可重写"""
        pass

    def get_config(self) -> dict:
        """返回策略配置 (用于实验记录)"""
        return {"name": self.name, "description": self.description}
