#!/usr/bin/env python3
"""
知识搜索循环 - 从论坛帖子和邮件中提取知识

不跑回测，纯知识积累
"""

import json
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('knowledge_loop')


class KnowledgeSearcher:
    """知识搜索器"""

    def __init__(self, posts_file: str = None, emails_file: str = None):
        self.posts = {}
        self.emails = []
        self.processed_post_ids: Set[str] = set()
        self.processed_email_uids: Set[str] = set()
        self.categories = [
            'Alpha挖掘', 'ValueFactor(VF)', 'Combine', 'OS/OSM',
            'PPA因子', 'Alpha筛选', '数据处理', '经验心得', 'AI工具'
        ]

        if posts_file:
            self.posts = self._load_posts(posts_file)
        if emails_file:
            self.emails = self._load_emails(emails_file)

        total = sum(len(v) for v in self.posts.values()) + len(self.emails)
        logger.info(f"加载了 {len(self.posts)} 个分类帖子 + {len(self.emails)} 封邮件，共 {total} 条数据")

    def _load_posts(self, posts_file: str) -> dict:
        posts_file = Path(posts_file)
        if not posts_file.exists():
            logger.warning(f"帖子文件不存在: {posts_file}")
            return {}
        with open(posts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"加载帖子: {sum(len(v) for v in data.values())} 篇")
        return data

    def _load_emails(self, emails_file: str) -> list:
        emails_file = Path(emails_file)
        if not emails_file.exists():
            logger.warning(f"邮件文件不存在: {emails_file}")
            return []
        with open(emails_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        emails = data.get('emails', [])
        logger.info(f"加载邮件: {len(emails)} 封")
        return emails

    def get_unprocessed_posts(self) -> List[Tuple[str, dict]]:
        unprocessed = []
        for category, posts in self.posts.items():
            for post in posts:
                pid = post.get('id', '')
                if pid and pid not in self.processed_post_ids:
                    unprocessed.append((category, post))
        return unprocessed

    def get_unprocessed_emails(self) -> List[dict]:
        return [e for e in self.emails if e.get('uid', '') not in self.processed_email_uids]

    def extract_knowledge(self, category: str, post: dict) -> List[Dict]:
        """从帖子提取知识"""
        knowledge_items = []
        subject = post.get('subject', '')
        content = post.get('content', '')
        author = post.get('author', '')
        date = post.get('date', '')

        if category == 'Alpha挖掘':
            items = self._extract_alpha_mining_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'ValueFactor(VF)':
            items = self._extract_vf_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'Combine':
            items = self._extract_combine_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'OS/OSM':
            items = self._extract_os_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'PPA因子':
            items = self._extract_ppa_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'Alpha筛选':
            items = self._extract_screening_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == '数据处理':
            items = self._extract_data_processing_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == '经验心得':
            items = self._extract_experience_knowledge(subject, content, author, date)
            knowledge_items.extend(items)
        elif category == 'AI工具':
            items = self._extract_ai_tools_knowledge(subject, content, author, date)
            knowledge_items.extend(items)

        return knowledge_items

    def extract_email_knowledge(self, email: dict) -> List[Dict]:
        """从邮件提取知识"""
        knowledge_items = []
        subject = email.get('subject', '')
        text = email.get('text', '')
        sender = email.get('sender', '')
        date = email.get('date', '')

        full_text = subject + ' ' + text

        # 数据集
        datasets = re.findall(r'\b(pv87|mdl136|analyst10|pv1|pv13|fundamental6|wds|mdl99|mdl100|mdl140)\b', full_text)
        for ds in set(datasets):
            knowledge_items.append({
                'type': 'dataset_mention', 'value': ds,
                'source': subject[:50], 'author': sender, 'date': date
            })

        # 模板
        templates = re.findall(r'(ts_mean|ts_delta|ts_rank|winsorize|rank|industry_relative|decay_linear|signed_power|correlation)\s*\(', full_text)
        for tmpl in set(templates):
            knowledge_items.append({
                'type': 'template_mention', 'value': tmpl,
                'source': subject[:50], 'author': sender, 'date': date
            })

        # 指标
        metrics = re.findall(r'(Sharpe|Fitness|Margin|Turnover|PPC|OS)\s*[=><]\s*[\d.]+', full_text)
        if metrics:
            knowledge_items.append({
                'type': 'metrics_pattern', 'value': ' | '.join(metrics[:3]),
                'source': subject[:50], 'author': sender, 'date': date
            })

        # 建议
        suggestions = re.findall(r'(建议|不要|应该|千万|一定|必须)\s*[^。]+', text)
        for s in suggestions[:2]:
            knowledge_items.append({
                'type': 'experience_suggestion', 'value': s[:100],
                'source': subject[:50], 'author': sender, 'date': date
            })

        return knowledge_items

    def _extract_alpha_mining_knowledge(self, subject, content, author, date):
        items = []
        datasets = re.findall(r'\b(pv87|mdl136|analyst10|pv1|pv13|fundamental6|wds)\b', content)
        for ds in set(datasets):
            items.append({'type': 'dataset_mention', 'value': ds, 'source': subject[:50], 'author': author, 'date': date})
        templates = re.findall(r'(ts_mean|ts_delta|ts_rank|winsorize|rank|industry_relative)\s*\(', content)
        for tmpl in set(templates):
            items.append({'type': 'template_mention', 'value': tmpl, 'source': subject[:50], 'author': author, 'date': date})
        metrics = re.findall(r'(Sharpe|Fitness|Margin)\s*[=><]\s*[\d.]+', content)
        if metrics:
            items.append({'type': 'metrics_pattern', 'value': ' | '.join(metrics[:3]), 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_vf_knowledge(self, subject, content, author, date):
        items = []
        strategies = re.findall(r'(VF|ValueFactor|base|加成|赛季)', content)
        if strategies:
            items.append({'type': 'vf_strategy_mention', 'value': ' '.join(set(strategies)), 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_combine_knowledge(self, subject, content, author, date):
        items = []
        alpha_counts = re.findall(r'(\d+)\s*[个条]?\s*alpha', content)
        if alpha_counts:
            items.append({'type': 'combine_alpha_count', 'value': alpha_counts[0], 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_os_knowledge(self, subject, content, author, date):
        items = []
        if '续航' in content or 'margin' in content.lower():
            items.append({'type': 'os_longevity', 'value': '提到续航力', 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_ppa_knowledge(self, subject, content, author, date):
        items = []
        standards = re.findall(r'(Sharpe|Fitness|Margin|PPC)\s*(>=|>|=<|<)\s*[\d.]+', content)
        for s in standards:
            items.append({'type': 'ppa_metric_standard', 'value': f"{s[0]}{s[1]}", 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_screening_knowledge(self, subject, content, author, date):
        items = []
        methods = re.findall(r'(分族|去重|筛选|过滤)', content)
        if methods:
            items.append({'type': 'screening_method', 'value': ' '.join(set(methods)), 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_data_processing_knowledge(self, subject, content, author, date):
        items = []
        funcs = re.findall(r'(ts_backfill|winsorize|rank|zscore)\s*\(', content)
        for f in set(funcs):
            items.append({'type': 'data_processing_func', 'value': f, 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_experience_knowledge(self, subject, content, author, date):
        items = []
        suggestions = re.findall(r'(建议|不要|应该)\s*[^。]+', content)
        for s in suggestions[:2]:
            items.append({'type': 'experience_suggestion', 'value': s[:100], 'source': subject[:50], 'author': author, 'date': date})
        return items

    def _extract_ai_tools_knowledge(self, subject, content, author, date):
        items = []
        tools = re.findall(r'(Claude|GPT|Gemini|WQ助手|AutoGPT)', content)
        for t in set(tools):
            items.append({'type': 'ai_tool_mention', 'value': t, 'source': subject[:50], 'author': author, 'date': date})
        return items


class KnowledgeBaseUpdater:
    """知识库更新器"""

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def update_daily_log(self, source: str, items: List[Dict], count: int):
        today = datetime.now().strftime('%Y-%m-%d')
        daily_file = self.knowledge_dir / 'memory' / 'daily' / f'{today}.md'
        daily_file.parent.mkdir(parents=True, exist_ok=True)

        with open(daily_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M:%S')} - {source}\n")
            f.write(f"处理了 {count} 条数据，提取了 {len(items)} 条知识\n")
            by_type = defaultdict(list)
            for item in items:
                by_type[item['type']].append(item['value'])
            for item_type, values in by_type.items():
                f.write(f"\n### {item_type}\n")
                for v in list(set(values))[:5]:
                    f.write(f"- {v}\n")

    def update_knowledge_summary(self, all_knowledge: Dict[str, List]):
        summary_file = self.knowledge_dir / 'memory' / 'KNOWLEDGE_SUMMARY.md'
        lines = ["# 知识摘要", "", f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "## 知识统计", ""]

        for category, items in all_knowledge.items():
            lines.append(f"- **{category}**: {len(items)} 条知识")
            by_type = defaultdict(int)
            for item in items:
                by_type[item['type']] += 1
            for t, c in by_type.items():
                lines.append(f"  - {t}: {c}")

        lines.append("")
        lines.append("## 常见模式")

        all_datasets = []
        for items in all_knowledge.values():
            all_datasets.extend([i['value'] for i in items if i['type'] == 'dataset_mention'])
        if all_datasets:
            top_datasets = Counter(all_datasets).most_common(5)
            lines.append("### 常用数据集")
            for ds, cnt in top_datasets:
                lines.append(f"- {ds}: {cnt}次")

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        logger.info(f"知识摘要已更新: {summary_file}")

    def update_current_state(self, processed: int, total: int, from_posts: int, from_emails: int):
        state_file = self.knowledge_dir / 'memory' / 'CURRENT_STATE.md'
        pct = f"({processed*100//total}%)" if total > 0 else "(0%)"

        lines = [
            "# 当前状态", "",
            f"> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
            "## 知识搜索进度",
            f"- 已处理: {processed}/{total} 条 {pct}",
            f"  - 论坛帖子: {from_posts}",
            f"  - 邮件: {from_emails}",
            f"- 状态: 知识搜索循环运行中", "",
            "## 模式",
            "- 知识搜索模式（不跑回测）",
            "- 持续从论坛帖子和邮件提取知识", "",
            "---",
            "*此文件由knowledge_loop自动更新*"
        ]

        with open(state_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))


class KnowledgeLoop:
    """知识搜索主循环"""

    def __init__(self, config: dict):
        posts_file = config.get('posts_file', 'data/raw/posts_categorized.json')
        emails_file = config.get('emails_file', 'data/raw/emails_raw.json')
        knowledge_dir = config.get('knowledge_dir', 'knowledge_base')

        self.searcher = KnowledgeSearcher(posts_file, emails_file)
        self.updater = KnowledgeBaseUpdater(knowledge_dir)
        self.processed_count = 0
        self.from_posts = 0
        self.from_emails = 0
        self.all_knowledge = defaultdict(list)

    def run_once(self) -> int:
        processed = 0
        unprocessed_posts = self.searcher.get_unprocessed_posts()
        unprocessed_emails = self.searcher.get_unprocessed_emails()

        logger.info(f"待处理: {len(unprocessed_posts)} 篇帖子, {len(unprocessed_emails)} 封邮件")

        # 处理帖子
        for category, post in unprocessed_posts[:20]:
            pid = post.get('id', '')
            items = self.searcher.extract_knowledge(category, post)
            self.all_knowledge[category].extend(items)
            self.searcher.processed_post_ids.add(pid)
            self.processed_count += 1
            self.from_posts += 1
            processed += 1
            if items:
                logger.info(f"  [帖子] {post.get('subject', '')[:40]}... -> {len(items)}条知识")

        # 处理邮件
        for email in unprocessed_emails[:20]:
            uid = email.get('uid', '')
            items = self.searcher.extract_email_knowledge(email)
            category = email.get('category', '其他')
            self.all_knowledge[category].extend(items)
            self.searcher.processed_email_uids.add(uid)
            self.processed_count += 1
            self.from_emails += 1
            processed += 1
            if items:
                logger.info(f"  [邮件] {email.get('subject', '')[:40]}... -> {len(items)}条知识")

        # 更新知识库
        if processed > 0:
            self.updater.update_daily_log('综合', [], processed)

        total_posts = sum(len(v) for v in self.searcher.posts.values())
        total_emails = len(self.searcher.emails)
        total = total_posts + total_emails

        self.updater.update_current_state(self.processed_count, total, self.from_posts, self.from_emails)
        self.updater.update_knowledge_summary(self.all_knowledge)

        logger.info(f"本轮处理: {processed} 条 (帖子:{self.from_posts}, 邮件:{self.from_emails})")
        return processed

    def run_continuous(self, interval: int = 60, max_rounds: int = 100):
        logger.info(f"开始知识搜索循环 (间隔{interval}秒, 最多{max_rounds}轮)")

        for round_num in range(max_rounds):
            logger.info(f"\n{'='*50}")
            logger.info(f"第 {round_num + 1} 轮")
            logger.info(f"{'='*50}")

            processed = self.run_once()
            if processed == 0:
                logger.info("没有待处理数据")
                break

            unprocessed = len(self.searcher.get_unprocessed_posts()) + len(self.searcher.get_unprocessed_emails())
            logger.info(f"剩余 {unprocessed} 条待处理")
            if round_num < max_rounds - 1 and processed > 0:
                time.sleep(interval)

        logger.info(f"\n完成! 共处理: {self.processed_count} 条 (帖子:{self.from_posts}, 邮件:{self.from_emails})")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='知识搜索循环')
    parser.add_argument('--posts', type=str, default='data/raw/posts_categorized.json')
    parser.add_argument('--emails', type=str, default='data/raw/emails_raw.json')
    parser.add_argument('--output', type=str, default='knowledge_base')
    parser.add_argument('--interval', type=int, default=5)
    parser.add_argument('--rounds', type=int, default=100)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()

    config = {
        'posts_file': args.posts,
        'emails_file': args.emails,
        'knowledge_dir': args.output
    }

    loop = KnowledgeLoop(config)
    if args.once:
        loop.run_once()
    else:
        loop.run_continuous(interval=args.interval, max_rounds=args.rounds)


if __name__ == "__main__":
    main()
