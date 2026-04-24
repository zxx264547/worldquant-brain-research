#!/usr/bin/env python3
"""
知识整合器 - 将分散的知识整合为结构化知识库
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

class KnowledgeIntegrator:
    """知识整合器"""

    def __init__(self, config: dict):
        self.emails_file = Path(config.get('emails_file', 'data/raw/emails_raw.json'))
        self.posts_file = Path(config.get('posts_file', 'data/raw/posts_categorized.json'))
        self.output_dir = Path(config.get('output_dir', 'knowledge_base'))
        
        self.emails = []
        self.posts = {}
        self.knowledge = defaultdict(list)
        
        self.load_data()
        self.extract_knowledge()
        self.integrate()

    def load_data(self):
        """加载数据"""
        # 加载邮件
        if self.emails_file.exists():
            with open(self.emails_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.emails = data.get('emails', [])
        
        # 加载帖子
        if self.posts_file.exists():
            with open(self.posts_file, 'r', encoding='utf-8') as f:
                self.posts = json.load(f)

    def extract_knowledge(self):
        """提取知识"""
        self._extract_from_emails()
        self._extract_from_posts()

    def _extract_from_emails(self):
        """从邮件提取知识"""
        wq_keywords = ['worldquantbrain', 'worldquant', 'brain support', 'wqb', 
                       'alpha', '回测', '因子', '策略']
        
        for e in self.emails:
            sender = e.get('sender', '').lower()
            subject = e.get('subject', '')
            text = e.get('text', '')
            
            # 过滤WQB相关
            if not any(k in subject.lower() + sender for k in wq_keywords):
                continue
            
            # 提取数据集
            datasets = re.findall(r'\b(pv87|mdl136|analyst10|pv1|pv13|fundamental6|wds|mdl99|mdl100|mdl140)\b', text)
            for ds in set(datasets):
                self.knowledge['datasets'].append({'name': ds, 'source': 'email', 'context': subject[:50]})
            
            # 提取模板函数
            templates = re.findall(r'(ts_mean|ts_delta|ts_rank|winsorize|rank|industry_relative|decay_linear|signed_power|correlation|ts_corr|ts_regression|clip)\s*\(', text)
            for t in set(templates):
                self.knowledge['templates'].append({'name': t, 'source': 'email', 'context': subject[:50]})
            
            # 提取指标
            metrics = re.findall(r'(Sharpe|Fitness|Margin|Turnover|PPC|OS)\s*[=><]?\s*[\d.]+', text)
            for m in set(metrics):
                self.knowledge['metrics'].append({'pattern': m, 'source': 'email', 'context': subject[:50]})
            
            # 提取建议
            suggestions = re.findall(r'建议[:：]\s*([^\n。]+)', text)
            for s in suggestions[:2]:
                self.knowledge['suggestions'].append({'text': s[:100], 'source': 'email', 'context': subject[:50]})

    def _extract_from_posts(self):
        """从帖子提取知识"""
        for category, posts in self.posts.items():
            for post in posts:
                subject = post.get('subject', '')
                content = post.get('content', '')
                
                # 数据集
                datasets = re.findall(r'\b(pv87|mdl136|analyst10|pv1|pv13|fundamental6|wds|mdl99|mdl100|mdl140)\b', content)
                for ds in set(datasets):
                    self.knowledge['datasets'].append({'name': ds, 'source': 'forum', 'context': subject[:50]})
                
                # 模板
                templates = re.findall(r'(ts_mean|ts_delta|ts_rank|winsorize|rank|industry_relative|decay_linear|signed_power)\s*\(', content)
                for t in set(templates):
                    self.knowledge['templates'].append({'name': t, 'source': 'forum', 'context': subject[:50]})
                
                # 指标
                metrics = re.findall(r'(Sharpe|Fitness|Margin|Turnover|PPC)\s*[=><]?\s*[\d.]+', content)
                for m in set(metrics):
                    self.knowledge['metrics'].append({'pattern': m, 'source': 'forum', 'context': subject[:50]})
                
                # 建议
                suggestions = re.findall(r'(建议|心得|经验|技巧)[:：]\s*([^\n。]+)', content)
                for _, s in suggestions[:2]:
                    self.knowledge['suggestions'].append({'text': s[:100], 'source': 'forum', 'context': subject[:50]})

    def integrate(self):
        """整合知识"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成综合知识文档
        self._generate_master_knowledge()
        
        # 生成数据集知识
        self._generate_dataset_knowledge()
        
        # 生成模板知识
        self._generate_template_knowledge()
        
        # 生成经验知识
        self._generate_experience_knowledge()

    def _generate_master_knowledge(self):
        """生成综合知识文档"""
        lines = [
            "# WorldQuant BRAIN 知识库",
            "",
            f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"数据来源: {len(self.emails)} 封邮件 + {sum(len(v) for v in self.posts.values())} 篇帖子",
            "",
            "---",
            "",
            "## 目录",
            "",
            "1. [数据集速查](#数据集速查)",
            "2. [模板函数](#模板函数)",
            "3. [指标标准](#指标标准)",
            "4. [实战经验](#实战经验)",
            "",
            "---",
            ""
        ]
        
        # 数据集速查
        lines.extend(self._format_datasets())
        
        # 模板函数
        lines.extend(self._format_templates())
        
        # 指标标准
        lines.extend(self._format_metrics())
        
        # 实战经验
        lines.extend(self._format_experiences())
        
        output_file = self.output_dir / 'MASTER_KNOWLEDGE.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"综合知识库已生成: {output_file}")

    def _format_datasets(self):
        """格式化数据集"""
        lines = ["## 数据集速查", "", "| 数据集 | 频次 | 说明 |", "|--------|------|------|"]
        
        counter = Counter(k['name'] for k in self.knowledge['datasets'])
        descriptions = {
            'pv87': '综合技术面数据',
            'mdl136': '分析师评级数据',
            'analyst10': '分析师数据',
            'pv1': '价格/成交量',
            'pv13': '价格/成交量扩展',
            'fundamental6': '基本面数据',
            'wds': '全球市场数据',
            'mdl99': '分析师情绪',
            'mdl100': '分析师覆盖',
            'mdl140': '分析师盈利预测'
        }
        
        for ds, cnt in counter.most_common():
            desc = descriptions.get(ds, '待补充')
            lines.append(f"| `{ds}` | {cnt} | {desc} |")
        
        lines.append("")
        return lines

    def _format_templates(self):
        """格式化模板函数"""
        lines = ["## 模板函数", "", "| 函数 | 频次 | 用途 |", "|------|------|------|"]
        
        counter = Counter(k['name'] for k in self.knowledge['templates'])
        descriptions = {
            'ts_mean': '时间序列均值',
            'ts_delta': '时间序列变化',
            'ts_rank': '时间序列排名',
            'winsorize': '去极值',
            'rank': '横截面排名',
            'industry_relative': '行业相对化',
            'decay_linear': '线性衰减',
            'signed_power': '符号幂变换',
            'ts_corr': '滚动相关性',
            'ts_regression': '滚动回归',
            'clip': '截断'
        }
        
        for tmpl, cnt in counter.most_common():
            desc = descriptions.get(tmpl, '待补充')
            lines.append(f"| `{tmpl}()` | {cnt} | {desc} |")
        
        lines.append("")
        return lines

    def _format_metrics(self):
        """格式化指标"""
        lines = ["## 指标标准", "", "### PPA因子标准", "", "| 指标 | 标准 | 说明 |", "|------|------|------|", "| PPC | < 0.5 | 核心门槛 |", "| Sharpe | >= 1.0 | 建议 >= 1.05 |", "| Fitness | > 0.5 | 必须 |", "| Margin | > Turnover | 必须 |", "", "### 常见指标模式", ""]
        
        for m in self.knowledge['metrics'][:20]:
            lines.append(f"- {m['pattern']} (来源: {m['source']})")
        
        lines.append("")
        return lines

    def _format_experiences(self):
        """格式化经验"""
        lines = ["## 实战经验", ""]
        
        for exp in self.knowledge['suggestions'][:30]:
            lines.append(f"- {exp['text']} (来源: {exp['source']})")
        
        lines.append("")
        return lines

    def _generate_dataset_knowledge(self):
        """生成数据集知识"""
        output_file = self.output_dir / 'DATASETS.md'
        
        counter = Counter(k['name'] for k in self.knowledge['datasets'])
        
        lines = [
            "# 数据集速查",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 频次排名",
            ""
        ]
        
        for ds, cnt in counter.most_common():
            lines.append(f"- **{ds}**: {cnt}次")
        
        lines.extend([
            "",
            "## 说明",
            "",
            "| 数据集 | 说明 | 常用场景 |",
            "|--------|------|----------|",
            "| pv87 | 综合技术面指标 | 短期Alpha |",
            "| mdl136 | 分析师评级 | 基本面Alpha |",
            "| analyst10 | 分析师数据 | 评级类Alpha |",
            "| pv1 | 价格/成交量 | 基础Alpha |",
            "| pv13 | 价格/成交量扩展 | 波动率Alpha |",
            "| fundamental6 | 基本面数据 | 价值Alpha |",
            "| wds | 全球市场数据 | 宏观Alpha |",
        ])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"数据集知识已生成: {output_file}")

    def _generate_template_knowledge(self):
        """生成模板知识"""
        output_file = self.output_dir / 'TEMPLATES.md'
        
        counter = Counter(k['name'] for k in self.knowledge['templates'])
        
        lines = [
            "# 模板函数速查",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 频次排名",
            ""
        ]
        
        for tmpl, cnt in counter.most_common():
            lines.append(f"- **{tmpl}()**: {cnt}次")
        
        lines.extend([
            "",
            "## 函数说明",
            "",
            "| 函数 | 语法 | 说明 |",
            "|------|------|------|",
            "| ts_mean | `ts_mean(x, N)` | 计算x的N日均值 |",
            "| ts_delta | `ts_delta(x, N)` | 计算x的N日变化 |",
            "| ts_rank | `ts_rank(x, N)` | 计算x的N日排名 |",
            "| winsorize | `winsorize(x)` | 去除极端值 |",
            "| rank | `rank(x)` | 横截面排名 |",
            "| industry_relative | `industry_relative(x)` | 行业相对化 |",
            "| decay_linear | `decay_linear(x, N)` | N日线性衰减 |",
            "| signed_power | `signed_power(x, a)` | 符号幂变换 |",
        ])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"模板知识已生成: {output_file}")

    def _generate_experience_knowledge(self):
        """生成经验知识"""
        output_file = self.output_dir / 'EXPERIENCES.md'
        
        lines = [
            "# 实战经验汇总",
            "",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 经验心得",
            ""
        ]
        
        seen = set()
        count = 0
        for exp in self.knowledge['suggestions']:
            text = exp['text']
            if text and text not in seen and len(text) > 10:
                seen.add(text)
                lines.append(f"- {text}")
                count += 1
                if count >= 50:
                    break
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"经验知识已生成: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='知识整合器')
    parser.add_argument('--emails', type=str, default='data/raw/emails_raw.json')
    parser.add_argument('--posts', type=str, default='data/raw/posts_categorized.json')
    parser.add_argument('--output', type=str, default='knowledge_base')
    args = parser.parse_args()
    
    config = {
        'emails_file': args.emails,
        'posts_file': args.posts,
        'output_dir': args.output
    }
    
    integrator = KnowledgeIntegrator(config)
    print("知识整合完成!")


if __name__ == "__main__":
    main()
