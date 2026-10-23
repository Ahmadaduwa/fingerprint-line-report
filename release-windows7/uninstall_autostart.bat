@echo off
chcp 65001 >nul
title ถอนการติดตั้ง STW_TeacherCheck Autostart
color 0C

echo ========================================================
echo   ถอนการติดตั้ง STW_TeacherCheck จาก Autostart
echo ========================================================
echo.

set TASK_NAME=STW_TeacherCheck
schtasks /delete /tn "%TASK_NAME%" /f

echo ปิดโปรแกรม STW_TeacherCheck ที่กำลังทำงานอยู่...
taskkill /f /im STW_TeacherCheck_Silent.exe >nul 2>&1
taskkill /f /im STW_TeacherCheck.exe >nul 2>&1

echo.
echo [OK] ถอนการติดตั้งเรียบร้อยแล้ว
pause
