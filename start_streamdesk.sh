#!/bin/bash

# Thư mục chứa project
PROJECT_DIR="/home/gmo044/Desktop/Android Studio Source/StreamDesk"

# 1. Chạy setup_adb.sh để mở cổng cho máy ảo/điện thoại
echo "Setting up ADB reverse..."
bash "$PROJECT_DIR/setup_adb.sh"

# 2. Chạy Server Python ẩn 
echo "Starting StreamDesk Server (Hidden)..."
cd "$PROJECT_DIR/ServerPython"
# Chạy python3 trong nền, chuyển hướng log vào server.log
nohup python3 main.py > "$PROJECT_DIR/ServerPython/server.log" 2>&1 &

echo "Done! StreamDesk is running in background. Check server.log for details."
