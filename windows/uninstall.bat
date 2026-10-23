@echo off
chcp 65001 >nul
title ถอนการติดตั้งระบบ LINE Report Background Task
color 0C

echo ========================================================
echo   ถอนการติดตั้ง HIP Line Report จาก Task Scheduler
echo ========================================================
echo.

set TASK_NAME=STW_TeacherCheck
schtasks /delete /tn "%TASK_NAME%" /f

echo หยุดโปรเซส Python ที่รัน main.py...
taskkill /f /im python.exe /fi "WINDOWTITLE eq STW_TeacherCheck*" >nul 2>&1


echo.
echo [OK] ถอนการติดตั้ง Service เรียบร้อยแล้ว
pause
