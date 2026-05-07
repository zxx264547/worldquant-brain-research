#!/usr/bin/env python3
"""转换posts_categorized.json到wq-forum-rag兼容格式"""

import json
from pathlib import Path

def convert_format(input_path: str, output_path: str):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 转换: {"社区名": [posts...]} -> {"byCommunity": {"社区名": {"title": "...", "topics": {...}}}}
    by_community = {}

    for community_name, posts in data.items():
        if not isinstance(posts, list):
            continue

        topics = {}
        for post in posts:
            topic_id = post.get('id', '')
            if not topic_id:
                continue

            topics[topic_id] = {
                "id": topic_id,
                "title": post.get('subject', ''),
                "postContent": post.get('content', ''),
                "url": f"https://support.worldquantbrain.com/hc/en-us/community/topics/{topic_id}",
                "datetime": post.get('date', ''),
                "author": post.get('author', ''),
                "voteNum": 0,
                "commentNum": 0,
                "comments": {}
            }

        by_community[community_name] = {
            "title": community_name,
            "topics": topics
        }

    result = {"byCommunity": by_community}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Converted {input_path} -> {output_path}")
    print(f"Communities: {len(by_community)}")

if __name__ == "__main__":
    import sys
    convert_format(
        sys.argv[1] if len(sys.argv) > 1 else '/home/zxx/worldQuant/worldquant_brain/data/raw/posts_categorized.json',
        sys.argv[2] if len(sys.argv) > 2 else '/home/zxx/worldQuant/worldquant_brain/data/raw/forum_export.json'
    )