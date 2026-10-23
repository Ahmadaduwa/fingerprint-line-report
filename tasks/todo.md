# Todo List

- [x] Task 1: ตรวจสอบและปรับปรุงโค้ด Python ให้เข้ากันได้กับ Python 3.8.10 (แก้ `| None` ให้ใช้ `Optional` และ `from __future__ import annotations`)
- [x] Task 2: ปรับปรุง `db.py` ให้รองรับ Hybrid Authentication (Windows Auth / SQL Auth) และ Mock Mode พร้อมคำแนะนำภาษาไทยเมื่อเชื่อมต่อไม่ได้
- [x] Task 3: สร้าง SQL Server Schema & Seed Data จำลองฐานข้อมูล `hiptime` ตรงตาม HIP Time 4.0
- [x] Task 4: ปรับปรุง `Dockerfile` ให้ใช้ `python:3.8.10-slim` และอัปเดต `docker-compose.yml`
- [x] Task 5: สร้างชุดสคริปต์ 1-Click สำหรับ Windows 7 (`install.bat`, `run_manual.bat`, `run_background.vbs`, `uninstall.bat`)
- [x] Task 6: อัปเดต `.github/workflows/ci.yml` ให้ทดสอบ Matrix (Python 3.8 & 3.12)
- [x] Task 7: เขียน Unit Test ตรวจสอบ Mock Mode, Windows Auth format, และ Syntax Compatibility (27/27 ผ่าน)
- [x] Task 8: เพิ่มระบบบันทึก Log ข้อผิดพลาด (`log_buffer.py`) พร้อมปุ่ม Copy Log บนหน้าเว็บ เพื่อให้ก๊อปส่งให้นายดูได้สะดวก
- [x] Task 9: เพิ่มการตั้งค่าผ่านหน้าเว็บ (`settings.py`) โดยตั้งค่าเริ่มต้น: ตัดสาย 07:30 น., Auto Download 09:00 น., และส่ง LINE 09:30 น.
