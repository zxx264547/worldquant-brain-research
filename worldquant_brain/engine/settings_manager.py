#!/usr/bin/env python3
"""配置管理器 — 替代30+个脚本中重复的 SETTINGS_BASE"""

from typing import Optional


# 默认回测配置 — 唯一真实来源
DEFAULT_SETTINGS = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 0,
    "truncation": 0.08,
    "neutralization": "NONE",
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": False
}


def get_settings(**overrides) -> dict:
    """获取回测配置 (默认值 + 覆盖)"""
    settings = DEFAULT_SETTINGS.copy()
    settings.update(overrides)
    return settings


def settings_for_region(region: str) -> dict:
    """根据市场获取预设配置"""
    region_presets = {
        "USA": {"region": "USA", "universe": "TOP3000"},
        "CHINA": {"region": "CHN", "universe": "TOP3000"},
        "HK": {"region": "HKG", "universe": "TOP1000"},
        "EUROPE": {"region": "EUR", "universe": "TOP1000"},
        "JAPAN": {"region": "JPN", "universe": "TOP1000"},
    }
    return get_settings(**(region_presets.get(region, {})))


def settings_for_optimization(decay: int = 2, neutralization: str = "INDUSTRY",
                              truncation: float = 0.05) -> dict:
    """优化场景预设"""
    return get_settings(decay=decay, neutralization=neutralization,
                        truncation=truncation)


def settings_for_submission() -> dict:
    """提交前最终优化预设"""
    return get_settings(decay=2, neutralization="NONE",
                        truncation=0.08, pasteurization="ON")


class SettingsManager:
    """配置管理器"""

    def __init__(self):
        self._base = DEFAULT_SETTINGS.copy()

    def with_region(self, region: str) -> 'SettingsManager':
        self._base.update(settings_for_region(region))
        return self

    def with_decay(self, decay: int) -> 'SettingsManager':
        self._base['decay'] = decay
        return self

    def with_truncation(self, truncation: float) -> 'SettingsManager':
        self._base['truncation'] = truncation
        return self

    def with_neutralization(self, neut: str) -> 'SettingsManager':
        self._base['neutralization'] = neut
        return self

    def with_description(self, desc: str) -> 'SettingsManager':
        self._base['description'] = desc
        return self

    def build(self) -> dict:
        return self._base.copy()
