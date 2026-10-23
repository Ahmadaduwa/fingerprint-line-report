@echo off
chcp 65001 >nul
title STW_TeacherCheck (Manual Mode)
color 0B

echo ========================================================
echo   รันระบบ STW_TeacherCheck ในโหมด Manual (ดู Log บนหน้าจอ)

echo ========================================================
echo.
echo กำลังเปิด Web UI ที่ http://localhost:8090 ...
echo กด Ctrl+C เพื่อหยุดการทำงาน
echo.

cd /d "%~dp0..\line-report\app"
python main.py

pause
