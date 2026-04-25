@echo off
setlocal enabledelayedexpansion
:: 切换到GBK编码，避免中文乱码
chcp 936 >nul
echo ==============================================
echo 重复文件检测工具 快捷启动器
echo ==============================================

:: 保持窗口不自动关闭，出现错误会停留
if not defined in_subprocess (
    set in_subprocess=1
    cmd /k "%~f0"
    exit /b
)

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python环境，请先安装 Python 3.8 或更高版本
    echo 📥 官方下载地址：https://www.python.org/downloads/
    echo 💡 安装时请勾选 "Add Python to PATH" 选项
    echo.
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

echo ✅ Python环境检测正常：
python --version

:: 检查当前目录是否正确
if not exist "duplicate_finder_ctk.py" (
    echo ❌ 错误：找不到主程序文件 duplicate_finder_ctk.py
    echo 💡 请确保此bat文件放在和主程序同一个目录下
    echo.
    echo 当前目录：%cd%
    dir /b
    echo.
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

:: 检查依赖包是否安装
echo.
echo 🔍 检查运行依赖...
pip show customtkinter send2trash >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 缺少必要依赖包，正在自动安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败，请手动执行命令：pip install -r requirements.txt
        echo.
        echo 按任意键退出...
        pause >nul
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 所有依赖已正常安装
)

:: 启动程序
echo.
echo 🚀 正在启动重复文件检测工具...
:: 先尝试用普通python运行测试是否有错误，再用pythonw后台启动
python -c "import customtkinter, send2trash, hashlib, os, json, threading, concurrent.futures" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 依赖导入失败，请尝试手动运行命令：pip install customtkinter send2trash
    echo.
    echo 按任意键退出...
    pause >nul
    exit /b 1
)

:: 正常启动
start pythonw duplicate_finder_ctk.py

echo ✅ 程序启动成功，你可以关闭此窗口
echo.
echo 按任意键退出...
pause >nul
exit /b 0
