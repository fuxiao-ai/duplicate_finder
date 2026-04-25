@echo off
chcp 65001 >nul
echo ==============================================
echo 重复文件检测工具 EXE打包脚本
echo ==============================================

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python环境，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)

:: 检查PyInstaller是否安装
echo 🔍 检查打包工具PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 未安装PyInstaller，正在自动安装...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ❌ PyInstaller安装失败，请手动执行：pip install pyinstaller
        pause
        exit /b 1
    )
)

echo ✅ 打包环境准备完成
echo 🔨 正在打包EXE文件...
pyinstaller --onefile --windowed --name "重复文件检测工具" --icon=NONE duplicate_finder_ctk.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ 打包完成！
    echo 📦 输出文件路径：dist\重复文件检测工具.exe
) else (
    echo ❌ 打包失败，请检查错误信息
)

pause
