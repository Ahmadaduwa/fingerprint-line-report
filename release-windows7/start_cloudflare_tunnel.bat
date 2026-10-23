@echo off
chcp 65001 >nul
title Cloudflare Tunnel for LINE Webhook - STW_TeacherCheck
color 0b

echo ======================================================================
echo    STW_TeacherCheck - เริ่มต้น Cloudflare Tunnel เพื่อรับ LINE Webhook
echo ======================================================================
echo.
echo [หมายเหตุ] ปกติโปรแกรม STW_TeacherCheck.exe จะเปิด Cloudflare Tunnel
echo และอัปเดต Webhook URL เข้า LINE Developers ให้อัตโนมัติอยู่แล้วในเบื้องหลัง!
echo สคริปต์นี้ใช้กรณีต้องการเปิดดูหน้าจอ Tunnel แยกต่างหากเท่านั้นครับ
echo.

if not exist "%~dp0cloudflared.exe" (
    echo [!] ไม่พบไฟล์ cloudflared.exe ในโฟลเดอร์นี้
    echo [*] กำลังดาวน์โหลด cloudflared รุ่นรองรับ Windows 7 32-bit (v2023.8.2)...
    echo.
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/cloudflare/cloudflared/releases/download/2023.8.2/cloudflared-windows-386.exe', '%~dp0cloudflared.exe')"
)

echo [*] กำลังสร้าง Public HTTPS Tunnel ไปยัง Web UI (http://127.0.0.1:8090)...
echo.
"%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8090 --no-autoupdate --protocol http2
pause
