@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title 网课挂机启动器

set "ENV_NAME=lite_env"
set "PYTHON_EXEC=%~dp0%ENV_NAME%\Scripts\python.exe"

:: 1. 检查环境，如果没有则安装 (这部分保持同步阻塞，确保环境就绪)
if not exist "%PYTHON_EXEC%" (
    echo [信息] 正在初始化环境...
    python -m venv %ENV_NAME%
    "%PYTHON_EXEC%" -m pip install --upgrade pip >nul 2>&1
    if exist "requirements.txt" (
        "%PYTHON_EXEC%" -m pip install -r requirements.txt
    ) else (
        "%PYTHON_EXEC%" -m pip install DrissionPage
    )
    echo [完成] 环境准备就绪。
)

:: 2. 【核心修改】启动 Python 并立即退出 Batch
:: "start" 命令会开启一个新进程
:: "" 是窗口标题
:: 后面的参数是启动 Python
echo [启动] 正在唤起脚本窗口...

start "优课自动挂机" "%PYTHON_EXEC%" "main.py"

:: 3. 启动器立刻自我关闭，不再在该窗口停留
exit