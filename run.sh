#!/bin/bash
# 快速启动脚本（macOS/Linux）

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "LP Mode Visualizer - Quick Start"
echo "=================================="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate
echo "✓ Virtual environment activated"

# 安装依赖
echo "Installing dependencies..."
pip install -q -r requirements.txt

# 运行测试
echo "Running tests..."
python test.py

# 启动应用
echo ""
echo "Starting application..."
python main.py
