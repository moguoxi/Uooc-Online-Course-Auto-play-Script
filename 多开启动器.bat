@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title 优课多开管理器

echo =================================================
echo           优课在线 - 批量多开启动器
echo =================================================

:: 1. 设置 Python 环境路径 (复用原启动器逻辑)
set "ENV_NAME=lite_env"
set "PYTHON_EXEC=%~dp0%ENV_NAME%\Scripts\python.exe"

:: 简单检查环境是否存在
if not exist "%PYTHON_EXEC%" (
    echo ❌ 未检测到虚拟环境，请先运行一次【启动器.bat】来初始化环境！
    pause
    exit
)

:: 2. 获取用户输入
echo.
set /p INSTANCE_NUM="👉 请输入要开启的窗口数量 (例如 3): "

:: 校验输入
if "%INSTANCE_NUM%"=="" set INSTANCE_NUM=1
if %INSTANCE_NUM% LEQ 0 set INSTANCE_NUM=1

:: 3. 寻找 Chrome 路径
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else (
    echo ❌ 未找到 Chrome 安装路径，请编辑本脚本手动设置 CHROME_PATH。
    pause
    exit
)

echo.
echo [正在启动] 准备开启 %INSTANCE_NUM% 个挂机实例...
echo -------------------------------------------------

:: 4. 循环启动
:: 从 0 开始循环到 N-1
set /a MAX_LOOP=%INSTANCE_NUM%-1

for /L %%i in (0, 1, !MAX_LOOP!) do (
    :: 计算当前端口 (9222 + i)
    set /a CURRENT_PORT=9222+%%i
    
    :: 设置独立的数据目录
    set "USER_DATA=%~dp0chrome_data_!CURRENT_PORT!"
    
    echo [实例 %%i] 启动端口 !CURRENT_PORT! ...
    
    :: A. 启动 Chrome (不等待，独立窗口)
    start "" "!CHROME_PATH!" --remote-debugging-port=!CURRENT_PORT! --user-data-dir="!USER_DATA!"
    
    :: 等待 2 秒让 Chrome 飞一会
    timeout /t 2 /nobreak >nul
    
    :: B. 启动 Python 脚本 (传入端口号作为参数)
    :: 标题会显示端口号，方便区分
    start "挂机助手 - 端口 !CURRENT_PORT!" "%PYTHON_EXEC%" "main.py" !CURRENT_PORT!
)

echo.
echo ✅ 所有实例启动完毕！
echo.
pause