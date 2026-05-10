#!/bin/bash
cd "$(dirname "$0")" || exit 1

# 加载环境变量 (后面我们会填 API Key)
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    . venv/bin/activate
fi

# 创建日志目录并运行主程序
mkdir -p logs
LOG_FILE="logs/daily_$(date +%Y%m%d).log"
export JSON_OUTPUT_DIR="${JSON_OUTPUT_DIR:-site/data}"

echo "开始运行外汇日报分析系统..."
python3 main.py --mode daily >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "运行完成，最近 20 行日志如下："
tail -20 "$LOG_FILE"
exit $EXIT_CODE 
