# 自动化配置

## TARE + OCR无人值守

### 问题
TARE Token限制导致无法无人值守运行

### 解决方案
使用MCP + OCR 实现自动化填写

### 所需工具
1. **Tesseract OCR**
   - 下载：https://github.com/tesseract-ocr/tesseract/releases
   - Windows安装后路径：`C:\Program Files\Tesseract-OCR\tesseract.exe`

2. **中文语言包**
   - 下载：https://github.com/tesseract-ocr/tessdata_fast
   - 文件：`chi_sim.traineddata`
   - 放入 tessdata 文件夹

### 配置步骤
1. 安装 Tesseract
2. 下载中文语言包放入 tessdata 文件夹
3. 将 TARE 输入框截图保存为 `input_box.png`
4. 运行监控脚本

### Python依赖
```python
import pyautogui    # 屏幕控制
import pytesseract  # OCR识别
import pyperclip    # 剪贴板
import logging
import time
```

### 脚本核心逻辑
```python
# 配置 tesseract 路径
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 监控循环
while True:
    # 截图输入框
    # OCR识别状态
    # 如果需要填写，自动填写
    # 记录日志
    time.sleep(interval)
```

## 自动提交调度

### 策略
- 根据OS排名自动调整提交
- OS > 0.5 时交Theme
- 其他时间交普通Alpha

### 注意事项
- 设置合理的检查间隔
- 处理异常中断情况
- 保存运行日志

---

*整理时间：2026年4月*
