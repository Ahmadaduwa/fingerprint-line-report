# แผนงาน: ระบบสรุปการมาทำงานส่ง LINE

> อัปเดตล่าสุด 2026-10-17

## เป้าหมาย

ส่งสรุป **มา / สาย / ขาด / ลา** ของพนักงานเข้า LINE ทุกเช้า 09:00
ใช้ **LINE Messaging API** แทน LINE Notify (ปิดบริการแล้ว) โดยอ่านข้อมูลจาก DB ของโปรแกรม HIP TIME 4.0

## ระบบทำงานยังไง

```
เครื่องสแกน CiF77S ──► โปรแกรม HIP TIME 4.0 ──► SQL Server (DB: Synctime)
  (คนสแกนนิ้ว/หน้า)     (บนโน้ตบุ๊ก LAPTOP-P7L0GKCJ,      │  docker: hip_sqlserver
                          ดึง log เข้า DB ตามเวลาที่ตั้ง)    │
                                                           ▼  อ่านอย่างเดียว
                                                 line-report (โค้ดที่เราเขียน)
                                                           │  docker: hip_line_report
                                                           ▼  ทุกวัน 09:00
                                                   LINE Messaging API ► ผู้รับ
```

| ส่วน | ใครรับผิดชอบ | หมายเหตุ |
|---|---|---|
| บันทึกเวลาในเครื่องสแกน | เครื่องสแกน | |
| ดึง log จากเครื่องสแกนเข้าตาราง `Transcantime` | **โปรแกรม HIP** | ต้องเปิด auto download และต้องเปิดโปรแกรมค้างไว้ |
| อ่าน DB → สรุป → ส่ง LINE | **line-report** (เรา) | อ่านอย่างเดียว ไม่เขียนลง DB |

## สถานะ

### ✅ ทำแล้ว
- [x] เปิด SQL Server ด้วย volume เดิม `docker_mssql_data` (DB `Synctime` 28 table)
- [x] แก้ [docker-compose.yml](docker-compose.yml) ให้ใช้ volume เดิมแบบ `external` และลบ `version` ออก
- [x] บันทึกโครงสร้าง DB ทั้งหมดไว้ที่ [SYNCTIME_SCHEMA.md](SYNCTIME_SCHEMA.md)
- [x] อ่านคู่มือ HIP TIME 4.0 (วิธีย้ายข้อมูลเครื่องสแกน, เชื่อม DB, backup/restore)
- [x] เขียน service [line-report/](line-report/) — สรุปมา/สาย/ขาด/ลา แล้วส่งเข้า LINE
- [x] ตั้งเวลาส่ง 09:00 ทุกวัน (ข้ามเสาร์-อาทิตย์และวันหยุดใน `Holiday`)
- [x] unit test ผ่าน 8/8, ทดสอบอ่าน DB จริงแบบ dry-run ผ่าน

### ⏳ ต้องทำต่อ (ก่อนใช้งานจริง)
- [ ] **ตั้ง HIP ให้ดึง log อัตโนมัติก่อน 09:00** (เมนู "ตั้งเวลาดึงข้อมูลจากเครื่องบันทึกเวลา") — ตอนนี้ `School.autodownload = 0` และ `Transcantime` ยังว่าง
- [ ] ลองสแกนจริง แล้วรัน `--check` เพื่อดูรูปแบบ `datetimescan` จริง ว่าระบบอ่านถูก
- [ ] สร้าง LINE Messaging API channel ที่ https://developers.line.biz → เอา **Channel access token (long-lived)** ใส่ใน `line-report/.env`
- [ ] ตัดสินใจผู้รับ: broadcast (เว้น `LINE_TO` ว่าง) หรือส่งเข้า user/กลุ่ม (ใส่ ID ใน `LINE_TO`)
- [ ] ทดสอบส่งจริง (`--now` หรือ `--date <วันทำงาน>`)
- [ ] `docker compose up -d` ให้รันถาวร
- [ ] เพิ่มข้อมูลพนักงานใน HIP: ชื่อจริง, แผนก (Level), กะ — ตอนนี้มี 3 คน (aku, aduwa, 99) ยังไม่มีแผนก/กะ

### 💡 ไอเดียพัฒนาต่อ (ยังไม่ทำ)
- ส่งเข้ากลุ่ม LINE → ต้องทำ webhook เพื่อหา groupId
- ส่งแยกตามแผนก (Level) ไปคนละกลุ่ม/คนละคน
- แจ้งทันทีเมื่อมีคนสแกน (real-time)
- สรุปรอบเย็น / สรุปรายสัปดาห์ / รายเดือน
- ข้อความแบบ Flex Message (สวยกว่า text)
- ดึง log จากเครื่องสแกนเองโดยไม่พึ่งโน้ตบุ๊ก HIP (ต้องรู้ protocol ของเครื่อง / ดูว่าเครื่องมีเมนู Cloud Server/ADMS ไหม)
- ตั้ง `TZ=Asia/Bangkok` ให้ SQL Server (ตอนนี้เป็น UTC ทำให้ `adddate` ช้ากว่าไทย 7 ชม.)

## กติกาการนับ (ตอนนี้)

| สถานะ | เงื่อนไข |
|---|---|
| 📝 ลา | มีรายการใน `TranLeave` วันนั้น (ลาก่อนเสมอ แม้จะสแกน) |
| ✅ มาตรงเวลา | สแกนครั้งแรก ≤ เวลาเข้ากะ + `LATE_GRACE_MINUTES` |
| ⏰ สาย | สแกนครั้งแรก > เวลาเข้ากะ + `LATE_GRACE_MINUTES` |
| ❌ ขาด | วันทำงาน แต่ไม่มีการสแกน |
| 🕐 ยังไม่ถึงเวลา | กะยังไม่เริ่ม (เช่น กะบ่าย) |
| ข้าม | เสาร์-อาทิตย์ (ตาม `School.*work`), วันใน `Holiday`, กะวันหยุด (00:00–00:00) |

- กะที่ใช้: `StudentShift` ของวันนั้น → ถ้าไม่มีใช้ `Student.shiftcode` → ถ้าไม่มีใช้ `DEFAULT_SHIFT` (01 = 08:00–17:00)
- ถ้าวันทำงานแต่**ไม่มีใครสแกนเลย** → ส่งข้อความเตือน "ยังไม่มีข้อมูลการสแกน" แทน (กันกรณี HIP ยังไม่ดึงข้อมูล)

### ข้อจำกัดที่รู้แล้ว
- ยังไม่รองรับกะข้ามวัน (เช่น 22:00–06:00)
- ลาครึ่งวันนับเป็นลาทั้งวัน
- ถ้า HIP ดึงข้อมูลหลัง 09:00 คนที่สแกนแล้วจะถูกนับเป็นขาดในรอบนั้น

## ไฟล์ในโปรเจกต์

| ไฟล์ | ใช้ทำอะไร |
|---|---|
| [docker-compose.yml](docker-compose.yml) | `sqlserver` + `line-report` |
| [SYNCTIME_SCHEMA.md](SYNCTIME_SCHEMA.md) | โครงสร้าง DB Synctime ละเอียดทุก table |
| [line-report/.env](line-report/.env) | ค่าตั้ง (LINE token, เวลาส่ง, รหัส DB) — **มีรหัสผ่าน ห้ามแชร์** |
| [line-report/.env.example](line-report/.env.example) | ตัวอย่างค่าตั้งพร้อมคำอธิบาย |
| [line-report/app/attendance.py](line-report/app/attendance.py) | logic คำนวณ มา/สาย/ขาด/ลา |
| [line-report/app/db.py](line-report/app/db.py) | อ่าน DB |
| [line-report/app/report.py](line-report/app/report.py) | สร้างข้อความภาษาไทย |
| [line-report/app/line_api.py](line-report/app/line_api.py) | ส่ง LINE (push / broadcast) |
| [line-report/app/main.py](line-report/app/main.py) | CLI + ตั้งเวลา |
| [line-report/tests/](line-report/tests/) | unit test |

## คำสั่งที่ใช้บ่อย

```bash
cd ~/projects/fingerprint

docker compose up -d                       # เปิดทั้งหมด
docker compose up -d sqlserver             # เปิดเฉพาะ DB (ถ้ายังไม่มี LINE token)
docker compose up -d --build line-report   # หลังแก้โค้ด
docker logs -f hip_line_report             # ดู log การส่ง

# ทดสอบ (ไม่ต้องเปิด service)
docker compose run --rm line-report python main.py --dry-run --date 2026-10-16   # ดูข้อความ ไม่ส่ง
docker compose run --rm line-report python main.py --now                         # ส่งของวันนี้ทันที
docker compose run --rm line-report python main.py --check                       # ดูรูปแบบวันที่ในข้อมูลจริง
docker compose run --rm line-report python -m unittest discover -s /tests        # รัน test

# เข้า DB
docker exec -it hip_sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -d Synctime
```

## ข้อมูลสำคัญที่ต้องจำ

- **DB:** SQL Server 2019 Express ใน docker `hip_sqlserver`, port 1433, DB `Synctime`, user `sa` (รหัสใน compose)
- **Volume:** `docker_mssql_data` (สร้างจาก compose เก่าชื่อโปรเจกต์ `docker`) — อย่าลบ
- **พอร์ต 1433 ต้องเปิด `0.0.0.0`** เพราะโน้ตบุ๊ก HIP (`LAPTOP-P7L0GKCJ`, 192.168.0.108) ต่อเข้ามาทาง LAN
- **เครื่องสแกน:** `fk_device` รุ่น CiF77S (Series S), ตั้งใน HIP ไว้ที่ 192.168.0.106:7005 — ตอนทดสอบจาก server ต่อไม่ติด (IP อาจเปลี่ยน ยังไม่ได้ยืนยัน)
- **คู่มือ HIP TIME 4.0:** https://hip-servicecenter.com/newpro/download/HIP%20TIME4.0.pdf — หน้า 11–17 เครื่องสแกน/ย้ายข้อมูล, 25–26 เชื่อม DB, 38 ตั้งเวลาดึงอัตโนมัติ, 43–44 backup/restore
- HIP รองรับเฉพาะเครื่อง **Series S**
- รหัสยืนยันการลบข้อมูลในเครื่องสแกน (ค่าเริ่มต้น) `1234` — ลบแล้วย้อนไม่ได้
