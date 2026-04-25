# 重复文件检测工具 (Duplicate File Finder)

基于哈希值的智能重复文件检测工具，支持预览、删除和报告生成。

## 功能特性

- 🔍 多级检测策略：先按文件大小，再按 MD5 哈希值
- 📁 目录选择：支持选择任意文件夹扫描
- 👁️ 文件预览：图片、文本、PDF 快速预览
- 🗑️ 安全删除：删除到回收站，可恢复
- ✨ 批量操作：批量删除 / 一键保留一个
- 📊 检测报告：导出详细 JSON 扫描报告
- 🌓 深色/浅色主题：实时切换，无需重启
- ⚡ 高性能优化：分页 + 增量渲染，支持上千个重复文件组

## 技术栈

- Python 3.8+
- CustomTkinter - 现代 GUI
- Pillow - 图片预览
- send2trash - 删除到回收站
- hashlib - 文件哈希计算

## 使用方法

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行
```bash
python duplicate_finder_ctk.py
```

### 打包为 EXE
```bash
build.bat
```
或手动：
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name dup-finder duplicate_finder_ctk.py
```
