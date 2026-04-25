@echo off
chcp 65001 >nul
echo ==============================================
echo 重复文件检测工具 快捷启动器
echo ==============================================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python环境，请先安装 Python 3.8 或更高版本
    echo 📥 官方下载地址：https://www.python.org/downloads/
    echo 💡 安装时请勾选 "Add Python to PATH" 选项
    pause
    exit /b 1
)

echo ✅ Python环境检测正常：
python --version

:: 检查依赖包是否安装
echo.
echo 🔍 检查运行依赖...
pip show customtkinter send2trash >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 缺少必要依赖包，正在自动安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败，请手动执行命令：pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 所有依赖已正常安装
)

:: 启动程序
echo.
echo 🚀 正在启动重复文件检测工具...
start pythonw duplicate_finder_ctk.py

echo ✅ 程序启动成功，你可以关闭此窗口
pause >nul
