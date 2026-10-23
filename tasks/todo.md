# Todo List: Real DB & LINE Auto-Webhook Fix

- [x] Task 1: อัปเดต `.env` และ `go-stw/config/settings.go` (ใส่ LINE Token จริง, รองรับอ่านค่าจาก `.env`, เอาโค้ดบังคับทับค่า DB ออก)
- [x] Task 2: แก้ไข `go-stw/db/database.go` (เพิ่ม `encrypt=disable` + TLS 1.0 CipherSuites, แก้ `?` เป็น `@p1`, เพิ่ม `Ping()` และระบบ Auto-Fallback เชื่อมต่อทั้ง `Synctime` และ `hiptime`)
- [x] Task 3: อัปเกรด `go-stw/line/client.go` (เพิ่ม `SetWebhookEndpoint`, `GetWebhookEndpoint`, และ `BroadcastText`)
- [x] Task 4: สร้าง `go-stw/tunnel/tunnel.go` สำหรับรัน `cloudflared --no-autoupdate` อัตโนมัติและซิงก์ Webhook URL เข้า LINE API ทันทีที่เปิดโปรแกรม
- [x] Task 5: อัปเดต `go-stw/main.go`, `go-stw/web/server.go`, และ `go-stw/web/index.html` (ให้บันทึกตั้งค่าแล้ว Reconnect DB ทันที, แสดงสถานะ DB และ Webhook URL จริง)
- [x] Task 6: ดาวน์โหลด `cloudflared.exe` รุ่นรองรับ Windows 7 32-bit (Go 1.20) ใส่ใน `release-windows7/cloudflared.exe` และอัปเดตสคริปต์ `.bat`
- [x] Task 7: รัน Unit Tests, ทดสอบเชื่อม `hip_sqlserver` (DB `Synctime`) + ทดสอบเชื่อม LINE API จริง + คอมไพล์ `.exe` สำหรับ Windows 7 32-bit
