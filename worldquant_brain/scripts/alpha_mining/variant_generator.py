#!/usr/bin/env python3
"""
Variant Generator - Alpha变体生成器

基于模板和数据集字段生成Alpha变体表达式
"""

import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass

# 从核心模块导入模板
from ..core.templates import BASE_TEMPLATES, ADVANCED_TEMPLATES, COMPOSITE_TEMPLATES

logger = logging.getLogger(__name__)


@dataclass
class VariantTemplate:
    """变体模板"""
    expression: str
    name: str
    category: str  # 'base', 'advanced', 'composite'


class VariantGenerator:
    """Alpha变体生成器"""

    def __init__(
        self,
        base_templates: List[Tuple[str, str]] = None,
        advanced_templates: List[Tuple[str, str]] = None,
        composite_templates: List[Tuple[str, str]] = None
    ):
        self.base_templates = base_templates or BASE_TEMPLATES
        self.advanced_templates = advanced_templates or ADVANCED_TEMPLATES
        self.composite_templates = composite_templates or COMPOSITE_TEMPLATES

    def get_all_templates(self) -> List[VariantTemplate]:
        """获取所有模板"""
        templates = []

        for expr, name in self.base_templates:
            templates.append(VariantTemplate(expr, name, 'base'))

        for expr, name in self.advanced_templates:
            templates.append(VariantTemplate(expr, name, 'advanced'))

        for expr, name in self.composite_templates:
            templates.append(VariantTemplate(expr, name, 'composite'))

        return templates

    def generate_variants(
        self,
        field_id: str,
        category: str = None,
        include_advanced: bool = False
    ) -> List[VariantTemplate]:
        """为单个字段生成变体

        Args:
            field_id: 数据字段ID
            category: 筛选类别 ('base', 'advanced', 'composite', None表示全部)
            include_advanced: 是否包含高级模板

        Returns:
            List[VariantTemplate]: 变体模板列表
        """
        if category == 'base':
            templates = self.base_templates
        elif category == 'advanced':
            templates = self.advanced_templates
        elif category == 'composite':
            templates = self.composite_templates
        else:
            templates = self.base_templates
            if include_advanced:
                templates.extend(self.advanced_templates)
                templates.extend(self.composite_templates)

        variants = []
        for template_expr, template_name in templates:
            expr = template_expr.format(data=field_id)
            cat = 'base'
            if template_expr in [t[0] for t in self.advanced_templates]:
                cat = 'advanced'
            elif template_expr in [t[0] for t in self.composite_templates]:
                cat = 'composite'
            variants.append(VariantTemplate(expr, template_name, cat))

        return variants

    def generate_batch_variants(
        self,
        field_ids: List[str],
        category: str = None,
        include_advanced: bool = False
    ) -> Dict[str, List[VariantTemplate]]:
        """批量生成变体

        Args:
            field_ids: 字段ID列表
            category: 筛选类别
            include_advanced: 是否包含高级模板

        Returns:
            Dict[str, List[VariantTemplate]]: {field_id: variants}
        """
        result = {}
        for field_id in field_ids:
            result[field_id] = self.generate_variants(
                field_id,
                category=category,
                include_advanced=include_advanced
            )
            logger.debug(f"字段 {field_id} 生成 {len(result[field_id])} 个变体")

        return result

    def get_template_count(self, include_advanced: bool = False) -> int:
        """获取模板总数"""
        count = len(self.base_templates)
        if include_advanced:
            count += len(self.advanced_templates) + len(self.composite_templates)
        return count
