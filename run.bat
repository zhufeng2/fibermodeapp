@echo off
REM 快速启动脚本（Windows）

setlocal enabledelayedexpansion

echo LP Mode Visualizer - Quick Start
echo ==================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python found: %PYTHON_VERSION%

REM 创建虚拟环境
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat
echo ✓ Virtual environment activated

REM 安装依赖
echo Installing dependencies...
pip install -q -r requirements.txt

REM 运行测试
echo Running tests...
python test.py

REM 启动应用
echo.
echo Starting application...
python main.py

pause
