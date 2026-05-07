#!/usr/bin/env python3
"""转换QQ邮件到论坛格式"""

import json
import re
from pathlib import Path

def clean_html(text):
    """简单清理HTML标签"""
    if not text:
        return ""
    # 移除常见HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def convert_emails(input_path: str, output_path: str, min_length: int = 50):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    emails = data.get('emails', [])

    # 按category分组
    by_category = {}
    for email in emails:
        category = email.get('category', '其他')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(email)

    # 转换为社区格式
    by_community = {}

    for category, email_list in by_category.items():
        topics = {}
        for email in email_list:
            uid = email.get('uid', '')
            subject = email.get('subject', '')
            text = email.get('text', '') or email.get('body', '')

            # 跳过太短的内容
            if len(text) < min_length:
                continue

            # 清理内容
            text = clean_html(text)

            topics[uid] = {
                "id": uid,
                "title": subject,
                "postContent": text[:5000],  # 限制长度
                "url": f"email://{uid}",
                "datetime": email.get('date', ''),
                "author": email.get('sender', ''),
                "voteNum": 0,
                "commentNum": 0,
                "comments": {}
            }

        if topics:
            by_community[category] = {
                "title": category,
                "topics": topics
            }

    result = {"byCommunity": by_community}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"转换完成: {input_path} -> {output_path}")
    print(f"社区数量: {len(by_community)}")
    total_topics = sum(len(c.get('topics', {})) for c in by_community.values())
    print(f"邮件数量: {total_topics}")

    # 打印统计
    for cat, comm in sorted(by_community.items(), key=lambda x: len(x[1].get('topics', {})), reverse=True):
        print(f"  {cat}: {len(comm.get('topics', {}))}封")

if __name__ == "__main__":
    import sys
    convert_emails(
        sys.argv[1] if len(sys.argv) > 1 else '/home/zxx/worldQuant/worldquant_brain/data/raw/emails_raw.json',
        sys.argv[2] if len(sys.argv) > 2 else '/home/zxx/worldQuant/worldquant_brain/data/raw/emails_export.json'
    )
