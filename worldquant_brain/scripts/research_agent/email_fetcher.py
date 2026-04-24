#!/usr/bin/env python3
"""
QQ邮箱邮件抓取器 - 通过IMAP协议抓取邮件并存入JSON
"""

import imaplib
import email
from email.header import decode_header
import json
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('email_fetcher')


class EmailFetcher:
    """QQ邮箱IMAP邮件抓取器"""

    def __init__(self, email_address: str, password: str, output_file: str = "emails_raw.json"):
        self.email_address = email_address
        self.password = password
        self.output_file = Path(output_file)
        self.mail = None
        self.processed_uids = set()
        self.all_emails = []
        self.load_processed()

    def connect(self) -> bool:
        """连接QQ邮箱IMAP"""
        try:
            logger.info(f"连接 {self.email_address}...")
            self.mail = imaplib.IMAP4_SSL(host='imap.qq.com', port=993)
            self.mail.login(self.email_address, self.password)
            logger.info("连接成功!")
            return True
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.mail:
            try:
                self.mail.logout()
            except:
                self.mail.close()
            logger.info("已断开连接")

    def load_processed(self):
        """加载已处理的邮件UID"""
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.all_emails = data.get('emails', [])
                    self.processed_uids = set(e.get('uid', '') for e in self.all_emails)
                    logger.info(f"已加载 {len(self.processed_uids)} 封已处理邮件")
            except Exception as e:
                logger.warning(f"加载失败: {e}")
                self.all_emails = []

    def save_emails(self):
        """保存邮件到文件"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_count': len(self.all_emails),
            'emails': self.all_emails
        }
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(self.all_emails)} 封邮件到 {self.output_file}")

    def decode_email_header(self, header_str: str) -> str:
        """解码邮件头"""
        if not header_str:
            return ""
        decoded_parts = []
        try:
            parts = decode_header(header_str)
            for content, charset in parts:
                if isinstance(content, bytes):
                    charset = charset or 'utf-8'
                    try:
                        decoded_parts.append(content.decode(charset, errors='replace'))
                    except:
                        decoded_parts.append(content.decode('utf-8', errors='replace'))
                else:
                    decoded_parts.append(content)
        except:
            return header_str
        return ''.join(decoded_parts)

    def parse_email_body(self, msg) -> str:
        """解析邮件正文"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = payload.decode(charset, errors='replace')
                        break
                    except:
                        pass
        else:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            try:
                body = payload.decode(charset, errors='replace')
            except:
                pass
        return body

    def extract_email_info(self, uid: str, msg) -> Dict:
        """提取邮件信息"""
        subject = self.decode_email_header(msg.get('Subject', ''))
        sender = self.decode_email_header(msg.get('From', ''))
        date = msg.get('Date', '')
        body = self.parse_email_body(msg)

        # 提取纯文本
        text = re.sub(r'<[^>]+>', '', body)  # 去掉HTML标签
        text = re.sub(r'\s+', ' ', text).strip()

        return {
            'uid': uid,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body[:5000],  # 限制长度
            'text': text[:3000],
            'category': self.categorize(subject, text)
        }

    def categorize(self, subject: str, text: str) -> str:
        """分类邮件"""
        content = (subject + ' ' + text).lower()

        if any(k in content for k in ['alpha', '回测', '模拟']):
            return 'Alpha挖掘'
        elif any(k in content for k in ['vf', 'valuefactor', '加成', '赛季']):
            return 'ValueFactor(VF)'
        elif any(k in content for k in ['combine', '组合']):
            return 'Combine'
        elif any(k in content for k in ['os', 'margi', '续航']):
            return 'OS/OSM'
        elif any(k in content for k in ['ppa', 'ppc', 'sharpe']):
            return 'PPA因子'
        elif any(k in content for k in ['筛选', '去重', '相关性']):
            return 'Alpha筛选'
        elif any(k in content for k in ['数据', 'field', '数据集']):
            return '数据处理'
        elif any(k in content for k in ['经验', '心得', '建议']):
            return '经验心得'
        else:
            return '其他'

    def search_and_fetch(self, search_query: str = 'ALL', batch_size: int = 50) -> int:
        """搜索并抓取邮件"""
        if not self.mail:
            if not self.connect():
                return 0

        try:
            # 选择收件箱
            self.mail.select('INBOX')

            # 搜索邮件
            logger.info(f"搜索邮件: {search_query}")
            status, message_ids = self.mail.search(None, search_query)

            if status != 'OK':
                logger.error(f"搜索失败: {status}")
                return 0

            all_ids = message_ids[0].split()
            logger.info(f"邮箱中共 {len(all_ids)} 封邮件")

            # 过滤未处理的
            new_ids = [mid for mid in all_ids if mid.decode() not in self.processed_uids]
            logger.info(f"新增邮件: {len(new_ids)} 封")

            if not new_ids:
                return 0

            # 逐个抓取
            fetched_count = 0
            for i, mid in enumerate(new_ids):
                try:
                    status, msg_data = self.mail.fetch(mid, '(RFC822)')
                    if status == 'OK' and msg_data and msg_data[0]:
                        uid = mid.decode()
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        email_info = self.extract_email_info(uid, msg)
                        self.all_emails.append(email_info)
                        self.processed_uids.add(uid)
                        fetched_count += 1

                        if (i + 1) % 20 == 0:
                            logger.info(f"  进度: {i+1}/{len(new_ids)}")
                            self.save_emails()  # 定期保存

                except Exception as e:
                    logger.warning(f"抓取邮件失败: {mid} - {e}")

            return fetched_count

        except Exception as e:
            logger.error(f"搜索抓取失败: {e}")
            return 0

    def fetch_all(self, batch_size: int = 50) -> int:
        """抓取所有邮件（分批）"""
        if not self.connect():
            return 0

        try:
            self.mail.select('INBOX')
            status, message_ids = self.mail.search(None, 'ALL')

            if status != 'OK':
                logger.error(f"搜索失败: {status}")
                return 0

            all_ids = message_ids[0].split()
            total = len(all_ids)
            logger.info(f"邮箱中共 {total} 封邮件")

            new_ids = [mid for mid in all_ids if mid.decode() not in self.processed_uids]
            logger.info(f"新增邮件: {len(new_ids)} 封")

            if not new_ids:
                logger.info("没有新邮件")
                return 0

            # 分批处理
            for batch_start in range(0, len(new_ids), batch_size):
                batch = new_ids[batch_start:batch_start + batch_size]
                logger.info(f"处理批次 {batch_start//batch_size + 1}: {len(batch)} 封")

                for mid in batch:
                    try:
                        status, msg_data = self.mail.fetch(mid, '(RFC822)')
                        if status == 'OK' and msg_data and msg_data[0]:
                            uid = mid.decode()
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)

                            email_info = self.extract_email_info(uid, msg)
                            self.all_emails.append(email_info)
                            self.processed_uids.add(uid)

                    except Exception as e:
                        logger.warning(f"抓取失败: {mid} - {e}")

                self.save_emails()
                time.sleep(0.5)  # 避免过快

            return len(new_ids)

        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return 0
        finally:
            self.disconnect()

    def fetch_since(self, date_str: str = None) -> int:
        """抓取指定日期之后的邮件"""
        if not date_str:
            # 默认获取近30天
            from datetime import timedelta
            date_str = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")

        query = f'SINCE {date_str}'
        return self.search_and_fetch(query)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='QQ邮箱抓取器')
    parser.add_argument('--email', type=str, default='2645471525@qq.com',
                       help='邮箱地址')
    parser.add_argument('--password', type=str, default='nurqhdbkqbdveafh',
                       help='授权码')
    parser.add_argument('--output', type=str, default='data/raw/emails_raw.json',
                       help='输出文件')
    parser.add_argument('--since', type=str, default=None,
                       help='抓取指定日期后的邮件 (格式: DD-Mon-YYYY, 如 01-Jan-2026)')
    parser.add_argument('--all', action='store_true',
                       help='抓取所有邮件')
    parser.add_argument('--continuous', action='store_true',
                       help='持续运行模式')
    parser.add_argument('--interval', type=int, default=300,
                       help='检查间隔(秒), 默认300秒')

    args = parser.parse_args()

    fetcher = EmailFetcher(
        email_address=args.email,
        password=args.password,
        output_file=args.output
    )

    if args.all:
        count = fetcher.fetch_all()
        logger.info(f"抓取完成: {count} 封新邮件")
    elif args.since:
        count = fetcher.fetch_since(args.since)
        logger.info(f"抓取完成: {count} 封新邮件")
    elif args.continuous:
        logger.info(f"持续运行模式 (间隔 {args.interval} 秒)")
        while True:
            count = fetcher.fetch_all()
            if count == 0:
                logger.info(f"等待 {args.interval} 秒后再次检查...")
                time.sleep(args.interval)
            else:
                logger.info(f"抓取到 {count} 封新邮件，等待 {args.interval} 秒...")
                time.sleep(args.interval)
    else:
        count = fetcher.fetch_all()
        logger.info(f"抓取完成: {count} 封新邮件")


if __name__ == "__main__":
    main()
