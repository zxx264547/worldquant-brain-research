#!/usr/bin/env python3
"""
WebDataRAW Parser - 数据解压与处理
用于解压世坤平台的原始数据文件
"""

import os
import zlib
import pickle
import struct
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebDataRawParser:
    """WebDataRAW解压解析器"""

    def __init__(self, data_dir: str = "./data/raw"):
        self.data_dir = data_dir
        self.cache: Dict[str, Any] = {}

    def decode_binary(self, file_path: str) -> Any:
        """
        解压二进制文件

        文件格式通常是 msgpack + zlib 压缩
        """
        logger.info(f"解压文件: {file_path}")

        with open(file_path, 'rb') as f:
            compressed_data = f.read()

        # zlib解压
        decompressed = zlib.decompress(compressed_data)

        # msgpack反序列化
        import msgpack
        data = msgpack.unpackb(decompressed, raw=False)

        logger.info(f"解压成功，数据类型: {type(data)}")

        if isinstance(data, dict):
            logger.info(f"字典键: {list(data.keys())[:10]}")
        elif isinstance(data, list):
            logger.info(f"列表长度: {len(data)}")

        return data

    def parse_dataframe(self, file_path: str) -> pd.DataFrame:
        """解析为DataFrame"""
        data = self.decode_binary(file_path)

        if isinstance(data, dict):
            # 如果是字典，尝试提取数据
            if 'data' in data:
                data = data['data']

        if isinstance(data, list):
            df = pd.DataFrame(data)
            logger.info(f"转换为DataFrame: {df.shape}")
            return df

        logger.warning("无法转换为DataFrame")
        return pd.DataFrame()

    def merge_datasets(
        self,
        res_df: pd.DataFrame,
        settings_df: pd.DataFrame,
        is_df: pd.DataFrame,
        os_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        合并四个具有相同ID的数据集

        类似SQL JOIN操作
        """
        merged = res_df.merge(settings_df, on='id', how='left', suffixes=('', '_settings'))
        merged = merged.merge(is_df, on='id', how='left', suffixes=('', '_is'))
        merged = merged.merge(os_df, on='id', how='left', suffixes=('', '_os'))

        logger.info(f"合并完成: {merged.shape}")

        return merged

    def extract_fields(self, data: Any, pattern: str = None) -> List[str]:
        """
        提取字段名

        pattern: 正则表达式模式
        """
        fields = []

        if isinstance(data, dict):
            fields = list(data.keys())
        elif isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                fields = list(data[0].keys())

        if pattern:
            import re
            fields = [f for f in fields if re.search(pattern, str(f))]

        logger.info(f"提取到 {len(fields)} 个字段")

        return fields

    def analyze_field_naming(self, fields: List[str]) -> Dict:
        """
        分析字段命名规律

        WorldQuant字段格式:
        [数据集id]_[经济学指标]_[时间周期]_[无含义后缀]

        示例: pv87_2_indicator_freq_matrix_scope_metric_stat
        """
        analysis = {
            "datasets": set(),
            "indicators": set(),
            "frequencies": set(),
            "patterns": []
        }

        import re

        # 常见模式
        dataset_pattern = r'^([a-z]+)\d+_'  # 数据集ID
        freq_pattern = r'_(af|qf|mf|wf|df)_'  # 频率
        stat_pattern = r'_(high|low|mean|median|dts|number|std|cnt|sum|max|min|p10|p25|p50|p75|p90)_$'  # 统计量

        for field in fields:
            # 提取数据集
            ds_match = re.match(dataset_pattern, field)
            if ds_match:
                analysis["datasets"].add(ds_match.group(1))

            # 提取频率
            freq_match = re.search(freq_pattern, field)
            if freq_match:
                analysis["frequencies"].add(freq_match.group(1))

            # 提取统计量
            stat_match = re.search(stat_pattern, field)
            if stat_match:
                analysis["indicators"].add(stat_match.group(1))

        # 转换为可序列化格式
        analysis["datasets"] = list(analysis["datasets"])
        analysis["indicators"] = list(analysis["indicators"])
        analysis["frequencies"] = list(analysis["frequencies"])

        logger.info(f"数据集: {analysis['datasets']}")
        logger.info(f"频率: {analysis['frequencies']}")
        logger.info(f"统计量: {analysis['indicators']}")

        return analysis


def main():
    """测试"""
    parser = WebDataRawParser()

    # 示例：分析字段
    sample_fields = [
        "pv87_2_af_matrix_all_null_high",
        "pv87_2_qf_matrix_p1_chngratio_mean",
        "analyst11_1e_af_score_industry_rank",
    ]

    result = parser.analyze_field_naming(sample_fields)
    print(f"分析结果: {result}")


if __name__ == "__main__":
    main()
