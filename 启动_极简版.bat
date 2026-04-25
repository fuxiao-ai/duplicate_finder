@echo off
:: 极简版启动脚本，无复杂检测，避免编码和兼容性问题
python duplicate_finder_ctk.py
:: 如果上面命令失败，尝试用py命令
if %errorlevel% neq 0 (
    py duplicate_finder_ctk.py
)
:: 都失败就停留窗口看错误
pause
