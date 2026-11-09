#!/usr/bin/env bash
# Khởi động AI Tutor (dùng virtual environment)
cd "$(dirname "$0")"
source venv/bin/activate

# Pre-compile picamera2 bytecode nếu chưa có (chỉ lần đầu)
PICAMERA_CACHE="/usr/lib/python3/dist-packages/picamera2/__pycache__"
if [ ! -d "$PICAMERA_CACHE" ]; then
    echo "Compiling picamera2 bytecode (chỉ lần đầu)..."
    python3 -m compileall /usr/lib/python3/dist-packages/picamera2/ 2>/dev/null
fi

python3 main.py "$@"
