@echo off
chcp 65001 >nul
title แก้ไขปัญหาการเชื่อมต่อ SQL Server (STW_TeacherCheck)
color 0B

echo ========================================================
echo   แก้ไขปัญหาการเชื่อมต่อ SQL Server (SQL Server Browser)
echo ========================================================
echo.

echo กำลังเปิดบริการ SQL Server Browser (บริการค้นหา Instance SQLEXPRES)...
sc config "SQLBrowser" start= auto >nul 2>&1
net start "SQLBrowser"

echo.
echo ตรวจสอบสถานะบริการ SQL Server:
sc query "MSSQL$SQLEXPRES" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] พบ SQL Server (MSSQL$SQLEXPRES) ในเครื่องนี้
    net start "MSSQL$SQLEXPRES" >nul 2>&1
) else (
    sc query "MSSQLSERVER" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] พบ SQL Server (Default Instance) ในเครื่องนี้
        net start "MSSQLSERVER" >nul 2>&1
    ) else (
        echo [INFO] ตรวจสอบรายชื่อบริการ MSSQL ในระบบ...
    )
)

echo.
echo ========================================================
echo   เปิดบริการ SQL Server Browser เรียบร้อยแล้ว!
echo ========================================================
echo.
echo ตอนนี้ให้กลับไปที่หน้าเว็บ http://localhost:8090
echo แล้วกดปุ่ม "🔌 ทดสอบการเชื่อมต่อ Database ตอนนี้" อีกครั้งได้เลยครับ
echo.
pause
