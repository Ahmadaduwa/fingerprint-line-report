@echo off
chcp 65001 >nul
title ตั้งค่าเริ่มทำงานอัตโนมัติ (STW_TeacherCheck)
color 0A

echo ========================================================
echo   ตั้งค่าให้ STW_TeacherCheck เริ่มทำงานอัตโนมัติ
echo ========================================================
echo.

set TASK_NAME=STW_TeacherCheck
set EXE_PATH=%~dp0STW_TeacherCheck_Silent.exe

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks /create /tn "%TASK_NAME%" /tr "\"%EXE_PATH%\"" /sc onlogon /rl highest /f

if %errorlevel% equ 0 (
    echo [SUCCESS] ลงทะเบียนเริ่มต้นอัตโนมัติเรียบร้อยแล้ว!
    echo กำลังเริ่มโปรแกรมในเบื้องหลังทันที...
    start "" "%EXE_PATH%"
    echo.
    echo เปิดหน้าเว็บจัดการได้ที่: http://localhost:8090
) else (
    echo [ERROR] ไม่สามารถตั้ง Task ได้ กรุณาคลิกขวาที่ไฟล์นี้แล้วเลือก "Run as administrator"
)

echo.
pause
