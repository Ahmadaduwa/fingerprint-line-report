@echo off
chcp 65001 >nul
title ติดตั้งระบบ STW_TeacherCheck บน Windows 7 (32-bit/64-bit)
color 0A

echo ========================================================
echo   ติดตั้งระบบสรุปเวลาสแกนนิ้วส่ง LINE: STW_TeacherCheck
echo   (สำหรับโปรแกรม HIP TIME 4.0 บน Windows 7 / Python 3.8.10)
echo ========================================================

echo.

:: 1. ตรวจสอบ Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] ไม่พบคำสั่ง Python ในเครื่อง!
    echo กรุณาติดตั้ง Python 3.8.10 (32-bit Windows installer) จาก:
    echo https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe
    echo *สำคัญ: อย่าลืมติ๊กถูก "Add Python 3.8 to PATH" ตอนติดตั้ง
    echo.
    pause
    exit /b 1
)

echo [1/3] ตรวจพบ Python:
python --version
echo.

:: 2. ติดตั้ง Dependencies และเตรียมไฟล์คอนฟิก
echo [2/3] กำลังเตรียมไฟล์คอนฟิกและติดตั้ง Dependencies...
cd /d "%~dp0..\line-report"

if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [OK] สร้างไฟล์ .env จาก .env.example ให้อัตโนมัติแล้ว
    )
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [WARNING] มีแพ็กเกจบางตัวลงไม่สำเร็จ กำลังลองติดตั้งพื้นฐาน...
    python -m pip install pymssql requests sqlalchemy
)
echo.

:: 3. ตั้งค่า Windows Task Scheduler ให้รันอัตโนมัติในเบื้องหลัง (Background)
echo [3/3] กำลังตั้งค่าให้ระบบเริ่มทำงานอัตโนมัติทุกครั้งที่เปิดเครื่อง...
set TASK_NAME=STW_TeacherCheck
set VBS_PATH=%~dp0run_background.vbs

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onlogon /rl highest /f

if %errorlevel% equ 0 (
    echo [SUCCESS] ลงทะเบียน Task Scheduler เรียบร้อยแล้ว!
    echo กำลังเริ่มโปรแกรมในเบื้องหลังทันที...
    schtasks /run /tn "%TASK_NAME%"
) else (
    echo [WARNING] ไม่สามารถตั้ง Task Scheduler ได้ (อาจต้องคลิกขวา Run as administrator)
    echo ท่านสามารถดับเบิลคลิกไฟล์ run_manual.bat เพื่อเริ่มใช้งานได้ทันที
)

echo.
echo ========================================================
echo   การติดตั้งเสร็จสมบูรณ์!
echo.
echo   - โปรแกรมรันอยู่ใน Background แล้ว
echo   - เข้าจัดการตั้งค่าและดู Log ได้ที่:
echo     http://localhost:8090
echo ========================================================
echo.
pause
