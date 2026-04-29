#!/bin/bash

# Script setup_adb.sh - StreamDesk
# Dùng để map port 8000 từ điện thoại về máy tính qua dây cáp ADB.

echo "--- Đang thiết lập kết nối ADB reverse cho StreamDesk ---"

# Kiểm tra xem adb có được cài đặt hay không
if ! command -v adb &> /dev/null; then
    echo "Lỗi: Chưa cài đặt adb. Vui lòng cài đặt bằng lệnh: sudo apt install android-tools-adb"
    exit 1
fi

# Thực hiện lệnh reverse
adb reverse tcp:8999 tcp:8999

if [ $? -eq 0 ]; then
    echo "Thành công: Đã kết nối cổng 8999. Bạn có thể mở ứng dụng trên điện thoại."
else
    echo "Lỗi: Không thể thiết lập adb reverse. Vui lòng kiểm tra cáp và bật Debugging trên điện thoại."
fi
