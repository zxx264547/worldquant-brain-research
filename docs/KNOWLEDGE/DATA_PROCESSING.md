# 数据处理技巧

## WebDataRAW解压

### 内存要求
- 极高，请清空电脑全部其他打开的应用
- 运行内存10G+

### Python库
```python
import pandas as pd
import msgpack
import zlib
import pickle
```

### 解压函数
```python
def decode_from_bin(file_path):
    with open(file_path, 'rb') as f:
        compressed_data = f.read()
    decompressed_data = zlib.decompress(compressed_data)
    import msgpack
    data = msgpack.unpackb(decompressed_data, raw=False)
    return data
```

## 字段命名规律

### 格式
```
[数据集id]_[经济学指标]_[时间周期]_[无含义后缀]
```

### 示例：pv87
```
pv87_2_[indicator]_[freq]_matrix_[scope]_[metric]_[stat]
```

### 财务指标
- affops, bps, capex, cfps, dps 等

### 频率标识
- af (Annual)
- qf (Quarterly)

### 统计量
- high, low, mean, median, dts, number, std 等

## 正则压缩

将整个数据集字段归纳为特定模式：
1. 每组正则表达式必须**互斥**
2. 相同规律合并输出（优化通用性）
3. 精确表达，避免过度匹配
4. 不可以使用通配符代表有经济含义指标

---

*来源：WorldQuant BRAIN论坛帖子*
