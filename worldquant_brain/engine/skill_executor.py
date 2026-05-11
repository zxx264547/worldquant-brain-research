#!/usr/bin/env python3
"""Skills运行时加载器 — 让JSON Skill定义真正可执行"""

import json
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path("/tmp/multi_agent/skills")

# 内置Skill定义 (当JSON文件不存在时使用)
BUILTIN_SKILLS = {
    "handle_fitness_low": {
        "name": "handle_fitness_low",
        "description": "低Fitness修复",
        "trigger": {"metric": "fitness", "condition": "lt", "value": 1.0},
        "steps": [
            {"action": "set_decay", "value": 2},
            {"action": "set_neutralization", "value": "INDUSTRY"},
            {"action": "set_truncation", "value": 0.01},
        ],
        "priority": 1,
    },
    "handle_turnover_high": {
        "name": "handle_turnover_high",
        "description": "高换手率修复",
        "trigger": {"metric": "turnover", "condition": "gt", "value": 0.05},
        "steps": [
            {"action": "set_decay", "value": 5},
            {"action": "set_operator", "value": "ts_mean"},
            {"action": "set_window", "value": 66},
        ],
        "priority": 2,
    },
    "handle_margin_low": {
        "name": "handle_margin_low",
        "description": "低Margin修复",
        "trigger": {"metric": "margin", "condition": "lt", "value": 0.05},
        "steps": [
            {"action": "set_neutralization", "value": "NONE"},
            {"action": "set_truncation", "value": 0.08},
        ],
        "priority": 3,
    },
    "handle_ppc_high": {
        "name": "handle_ppc_high",
        "description": "高PPC修复",
        "trigger": {"metric": "ppc", "condition": "gt", "value": 0.5},
        "steps": [
            {"action": "wrap_rank", "value": True},
            {"action": "set_truncation", "value": 0.05},
        ],
        "priority": 4,
    },
}


class SkillExecutor:
    """Skill运行时 — 加载JSON定义并自动应用修复策略"""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = Path(skills_dir) if skills_dir else SKILLS_DIR
        self._skills = None

    @property
    def skills(self) -> dict:
        if self._skills is None:
            self._skills = self._load_all()
        return self._skills

    def _load_all(self) -> dict:
        """加载所有Skill定义 (JSON优先, 内置兜底)"""
        skills = dict(BUILTIN_SKILLS)

        if self.skills_dir.exists():
            for f in self.skills_dir.glob("*.json"):
                try:
                    with open(f) as fp:
                        skill = json.load(fp)
                    name = skill.get('name', f.stem)
                    skills[name] = skill
                except Exception:
                    pass

        return skills

    def diagnose(self, result: dict) -> list[dict]:
        """诊断Alpha问题, 返回匹配的Skill列表"""
        matched = []
        for name, skill in self.skills.items():
            trigger = skill.get('trigger', {})
            if not isinstance(trigger, dict):
                continue
            metric = trigger.get('metric', '')
            condition = trigger.get('condition', 'lt')
            threshold = trigger.get('value', 0)

            value = result.get(metric, 0)

            if condition == 'lt' and value < threshold:
                matched.append({
                    'skill': name,
                    'metric': metric,
                    'value': value,
                    'threshold': threshold,
                    'priority': skill.get('priority', 99)
                })
            elif condition == 'gt' and value > threshold:
                matched.append({
                    'skill': name,
                    'metric': metric,
                    'value': value,
                    'threshold': threshold,
                    'priority': skill.get('priority', 99)
                })

        matched.sort(key=lambda x: x['priority'])
        return matched

    def get_fixes(self, diagnoses: list[dict]) -> list[dict]:
        """从诊断结果生成修复建议列表"""
        fixes = []
        for d in diagnoses:
            skill_name = d['skill']
            skill = self.skills.get(skill_name, {})
            for step in skill.get('steps', []):
                fixes.append({
                    'type': step['action'],
                    'value': step['value'],
                    'source_skill': skill_name,
                    'reason': f"{d['metric']}={d['value']:.3f} "
                             f"(threshold: {d['threshold']})"
                })
        return fixes

    def apply_fix(self, result: dict, fix: dict) -> Optional[dict]:
        """应用单个修复, 返回新的settings字典"""
        settings = result.get('settings', {}).copy()
        action = fix['type']
        value = fix['value']

        if action == 'set_decay':
            settings['decay'] = value
        elif action == 'set_neutralization':
            settings['neutralization'] = value
        elif action == 'set_truncation':
            settings['truncation'] = value
        elif action == 'set_window':
            settings['window'] = value
        elif action == 'set_operator':
            settings['operator'] = value
        elif action == 'wrap_rank':
            # 标记表达式需要rank包裹 (需要在调用处处理)
            settings['_wrap_rank'] = value
        else:
            return None

        return settings

    def list_skills(self) -> list[dict]:
        """列出所有可用Skills"""
        return [{
            'name': name,
            'description': s.get('description', ''),
            'trigger': s.get('trigger', {}),
            'steps': len(s.get('steps', []))
        } for name, s in self.skills.items()]


# ─── 便捷函数 ───

def diagnose_alpha(result: dict) -> dict:
    """一站式诊断: 输入Alpha结果 → 输出问题和修复建议"""
    executor = SkillExecutor()
    issues = executor.diagnose(result)
    fixes = executor.get_fixes(issues)
    return {
        'alpha_id': result.get('alpha_id', ''),
        'sharpe': result.get('sharpe', 0),
        'issues': issues,
        'fixes': [f"{f['type']}={f['value']} ({f['reason']})" for f in fixes],
        'needs_fix': len(issues) > 0
    }


if __name__ == "__main__":
    # 测试
    test_result = {
        'alpha_id': 'TEST123',
        'sharpe': 0.8,
        'fitness': 0.3,
        'turnover': 0.08,
        'margin': 0.02,
        'ppc': 0.6,
    }
    report = diagnose_alpha(test_result)
    print("诊断结果:")
    for issue in report['issues']:
        print(f"  {issue['skill']}: {issue['metric']}={issue['value']:.3f}")
    print("修复建议:")
    for f in report['fixes']:
        print(f"  {f}")
