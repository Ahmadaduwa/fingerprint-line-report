# Statement of Intent: STW_TeacherCheck — Real DB & LINE Integration Fix

> Confirmed: 2026-10-23

## Intent Summary

- **Outcome:** แก้ไข `go-stw` และชุดไฟล์ใน `release-windows7` ให้เชื่อมทั้ง **SQL Server** และ **LINE (`@143smwig` STW_FaceCheck)** ได้จริงแบบอัตโนมัติ พร้อมทดสอบกับ `hip_sqlserver` และ LINE API จริงจนผ่านครบทุกจุด
- **User:** ผู้ดูแลระบบ/โรงเรียนแสงธรรมวิทยา ที่รัน `STW_TeacherCheck.exe` บนเครื่อง Windows 7 (32-bit) ที่มี SQL Server + HIP Time 4.0 (และทดสอบบน Linux `hip_sqlserver` ได้ด้วย)
- **Why now:**
  1. **ฝั่ง DB พังเพราะ:**
     - SQL Server 2012 บน Windows 7 ใช้ TLS 1.0 (`protocol version 301`) แต่ `buildConnString` ใน `go-stw/db/database.go` ไม่ได้ใส่ `encrypt=disable` ทำให้ติด `TLS Handshake failed: tls: server selected unsupported protocol version 301`
     - คำสั่ง `GetScans` ใช้ `?` แทน `@p1` (ซึ่ง driver `sqlserver` ของ `go-mssqldb` บังคับใช้ `@p1`)
     - ตอนกดบันทึกตั้งค่าหน้าเว็บ (`POST /api/settings`) ระบบไม่ได้สั่ง Reconnect DB จริง และ `GET /api/status` ไม่ได้ตรวจสอบ error จาก DB ก่อนตอบว่า `db_connected: true`
     - `config/settings.go` มีโค้ดบังคับเปลี่ยนค่า `DBHost` และ `DBAuth` ทับค่าที่ผู้ใช้ตั้ง
  2. **ฝั่ง LINE & Webhook พังเพราะ:**
     - `cloudflared` เวอร์ชันล่าสุดรันบน Windows 7 32-bit ไม่ได้ (เพราะคอมไพล์ด้วย Go 1.21+ ที่ตัดการรองรับ Windows 7)
     - ผู้ใช้ต้องคอยนำ URL ของ Cloudflare Tunnel ไปวางใน LINE Developers Console เองทุกครั้งที่เปิดเครื่อง
     - ระบบเดิมบังคับว่าต้องมี `recipients` เท่านั้นถึงจะส่งได้ ไม่มีระบบสำรองส่งแบบ Broadcast
- **Success:**
  1. เชื่อมต่อ DB สำเร็จทั้งบน Windows 7 (TLS 1.0 / `hiptime` หรือ `Synctime`) และทดสอบกับ Docker `hip_sqlserver` (`Synctime`) ผ่านจริง
  2. ฝัง `LINE_CHANNEL_ACCESS_TOKEN` ของบอท `STW_FaceCheck` (`@143smwig`) พร้อมใช้งานทันที และโหลดค่าจาก `.env` ได้ด้วย
  3. ใช้ `cloudflared.exe` รุ่นที่รองรับ **Windows 7 32-bit** (Go 1.20) โดยให้ตัวโปรแกรม `STW_TeacherCheck.exe` สั่งเปิด Tunnel เองในเบื้องหลัง แล้ว **ยิง API ไปอัปเดต Webhook URL (`PUT /v2/bot/channel/webhook/endpoint`) เข้า LINE Developers ให้เองอัตโนมัติทุกครั้งที่เปิดโปรแกรม** เพื่อดึง User ID คนที่ทัก/แอดเข้ามา + มีโหมดสำรองส่ง Broadcast ได้ถ้ายังไม่ได้เลือกผู้รับ
- **Constraint:** ต้องทำงานได้บน **Windows 7 32-bit** แบบดับเบิลคลิกไฟล์เดียวจบ ไม่ต้องลงโปรแกรมเสริม และใช้โครงสร้างตารางตาม `SYNCTIME_SCHEMA.md`
- **Out of scope:** ไม่แก้ไขฐานข้อมูลฝั่งโปรแกรม HIP Time 4.0 (อ่านอย่างเดียว) และไม่ทำระบบกะข้ามวัน
