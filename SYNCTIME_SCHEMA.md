# Synctime Database — โครงสร้าง DB และ Table

> บันทึกเมื่อ 2026-10-17 · ดึงจาก SQL Server ใน container `hip_sqlserver` (volume `docker_mssql_data`)

## 1. ภาพรวม

| รายการ | ค่า |
|---|---|
| Server | Microsoft SQL Server 2019 (RTM-CU32-GDR) (KB5122772) - 15.0.4490.9 (X64) (Express) |
| Database | `Synctime` (database ของผู้ใช้มีตัวเดียว นอกนั้นเป็น system DB) |
| ซอฟต์แวร์ | HIP Time 4.0 (ค่า `School.systemname`) — โปรแกรมลงเวลาด้วยนิ้ว/บัตร/ใบหน้าของ HIP Global |
| Collation | `SQL_Latin1_General_CP1_CI_AS` (ภาษาไทยเก็บได้เพราะคอลัมน์เป็น nvarchar) |
| Compatibility level | 150 · Recovery model: FULL |
| ไฟล์ | `/var/opt/mssql/data/Synctime.mdf`, `/var/opt/mssql/data/Synctime_log.ldf` (อย่างละ 8 MB) |
| จำนวน table | 28 (schema `dbo` ทั้งหมด) |
| View / Stored procedure / Function / Trigger | ไม่มี |
| Foreign key | **ไม่มีเลย** — ความสัมพันธ์อยู่ในโค้ดของโปรแกรม (ดูหัวข้อ 3) |
| Index | มีแค่ clustered PK ของแต่ละ table ไม่มี index อื่น |

### การเชื่อมต่อ

```
Host: 127.0.0.1,1433   User: sa   Database: Synctime
docker exec -it hip_sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -d Synctime
```

รหัสผ่าน `sa` อยู่ใน [docker-compose.yml](docker-compose.yml) (`SA_PASSWORD`)

## 2. รายชื่อ Table

| กลุ่ม | Table | แถว | คอลัมน์ | หน้าที่ |
|---|---|--:|--:|---|
| คนและเครื่องสแกน | [`Student`](#student) | 0 | 30 | ข้อมูลพนักงาน/นักเรียน หนึ่งแถวต่อหนึ่งคน เป็นศูนย์กลางของระบบ |
| คนและเครื่องสแกน | [`StudentMachine`](#studentmachine) | 0 | 10 | template ลายนิ้วมือ/ใบหน้าของแต่ละคนในแต่ละเครื่อง ใช้ backup/sync ขึ้นลงเครื่อง |
| คนและเครื่องสแกน | [`Machine`](#machine) | 1 | 15 | เครื่องสแกนที่ลงทะเบียนไว้ (IP, port, รุ่น) |
| คนและเครื่องสแกน | [`MachineModel`](#machinemodel) | 39 | 8 | master รุ่นเครื่อง และความสามารถของแต่ละรุ่น (นิ้ว/บัตร/หน้า/ประตู) |
| การลงเวลา | [`Transcantime`](#transcantime) | 0 | 18 | log การสแกนดิบทุกครั้งที่ดึงจากเครื่อง (table สำคัญที่สุดด้านข้อมูลเวลา) |
| การลงเวลา | [`TranscantimeBK`](#transcantimebk) | 0 | 13 | สำเนา/backup ของ Transcantime (คอลัมน์น้อยกว่า ไม่มี pic/mask/tem) |
| การลงเวลา | [`StudentTime`](#studenttime) | 0 | 105 | สรุปเวลาสแกนรายวันแบบแนวนอน 1 แถว = 1 คน x 1 วัน, เวลาแต่ละครั้งอยู่ใน time01..time100 |
| กะงานและช่วงเวลา | [`StudentShift`](#studentshift) | 0 | 5 | กำหนดกะของแต่ละคนเป็นรายวัน (override กะประจำใน Student.shiftcode) |
| กะงานและช่วงเวลา | [`Shift`](#shift) | 2 | 17 | master กะงาน พร้อมช่วงเวลาสแกนเข้า/พัก/ออก/OT |
| กะงานและช่วงเวลา | [`TimeZone`](#timezone) | 0 | 17 | Time zone ของเครื่อง (ช่วงเวลาที่อนุญาตให้สแกน/เปิดประตู) สูงสุด 7 ช่วง |
| กะงานและช่วงเวลา | [`StudentTimeZone`](#studenttimezone) | 0 | 10 | ผูกคนกับ Time zone ในแต่ละวันของสัปดาห์ ต่อเครื่อง |
| การลาและวันหยุด | [`Leave`](#leave) | 0 | 3 | master ประเภทการลา |
| การลาและวันหยุด | [`TranLeave`](#tranleave) | 0 | 7 | รายการลาของแต่ละคน |
| การลาและวันหยุด | [`Holiday`](#holiday) | 0 | 3 | วันหยุดบริษัท/โรงเรียน |
| องค์กร | [`School`](#school) | 1 | 38 | ข้อมูลบริษัท/โรงเรียน และค่าตั้งค่าระบบทั้งหมด (เวลาทำงาน, วันทำงาน, auto download, SMS, LINE, email) |
| องค์กร | [`Branch`](#branch) | 0 | 4 | สาขา |
| องค์กร | [`Level`](#level) | 0 | 7 | แผนก/ระดับชั้น (ใช้แบ่งกลุ่มคน, มี LINE token แยกต่อกลุ่มได้) |
| องค์กร | [`Classes`](#classes) | 0 | 5 | ห้องเรียน/กลุ่มย่อยภายใต้ Level |
| ผู้ใช้โปรแกรม | [`Users`](#users) | 0 | 6 | ผู้ใช้ที่ login เข้าโปรแกรม Synctime |
| ผู้ใช้โปรแกรม | [`useraccesslevel`](#useraccesslevel) | 0 | 3 | สิทธิ์ของผู้ใช้ว่าเห็น Level ไหนได้บ้าง |
| เงินเดือน | [`transpay`](#transpay) | 0 | 42 | ผลการคำนวณเงินเดือนต่อคนต่องวด (รายได้, OT, รายการหัก, ภาษี) |
| ตั้งค่า/ระบบ | [`ExportFormat`](#exportformat) | 1 | 52 | รูปแบบการ export ไฟล์เวลา (text) ไปให้โปรแกรมเงินเดือนอื่น |
| ตั้งค่า/ระบบ | [`SetExportFormat`](#setexportformat) | 0 | 10 | กำหนดคอลัมน์ของไฟล์ export แบบละเอียด |
| ตั้งค่า/ระบบ | [`repport`](#repport) | 0 | 12 | table ชั่วคราวสำหรับทำรายงาน (rep01..rep12 เป็น text ทั้งหมด) |
| ตั้งค่า/ระบบ | [`AutoLoadTime`](#autoloadtime) | 0 | 2 | เวลาที่ตั้งให้ดึงข้อมูลจากเครื่องอัตโนมัติ (HH:MM) |
| ตั้งค่า/ระบบ | [`AutoLoadErr`](#autoloaderr) | 0 | 6 | log error ตอนดึงข้อมูลจากเครื่องอัตโนมัติ |
| ตั้งค่า/ระบบ | [`ckelocation`](#ckelocation) | 1 | 1 | path ที่โปรแกรมใช้ (ค่าปัจจุบัน c:\) |
| ตั้งค่า/ระบบ | [`ckenamepc`](#ckenamepc) | 0 | 2 | ชื่อเครื่อง PC ที่ติดตั้งโปรแกรม และสถานะ (น่าจะใช้ตรวจ license) |

ณ วันที่บันทึก มีข้อมูลแค่ `School`, `Machine`, `MachineModel`, `Shift`, `ExportFormat`, `ckelocation` ส่วน table อื่นว่างทั้งหมด (ยังไม่มีพนักงานและยังไม่มี log สแกน)

## 3. ความสัมพันธ์ระหว่าง Table

DB ไม่มี FK จริง ความสัมพันธ์ข้างล่างนี้อนุมานจากชื่อคอลัมน์ join ด้วยรหัสแบบ text/ตัวเลข ไม่ได้ใช้ `id`

```
                         School (schoolcode)
                              │
 Branch (branchcode) ──┐      │      ┌── Level (levelcode) ── Classes
                       │      │      │        │
 Shift (shiftcode) ────┼── Student ──┘        └── useraccesslevel ── Users
       │               │   (studentcode, enrollnumber)
       └─ StudentShift ┤      │
                       │      ├── studentcode ──► TranLeave ──► Leave
                       │      └── studentcode ──► transpay
                       │
            enrollnumber (กุญแจหลักฝั่งเครื่องสแกน)
       ┌───────────┬───────┴───────┬────────────────┐
  Transcantime  StudentTime  StudentMachine  StudentTimeZone
       │                           │                │
       └──────── machineno ────────┴──── Machine ───┴── TimeZone
                                          │
                                     MachineModel (modelcode)
```

| จาก | ไปยัง | หมายเหตุ |
|---|---|---|
| `Student.enrollnumber` | `Transcantime.enrollnumber` | 1 คน : หลาย log สแกน |
| `Student.enrollnumber` | `TranscantimeBK.enrollnumber` |  |
| `Student.enrollnumber` | `StudentTime.enrollnumber` | 1 คน : 1 แถวต่อวัน |
| `Student.enrollnumber` | `StudentMachine.enrollnumber` | template นิ้ว/หน้า |
| `Student.enrollnumber` | `StudentShift.enrollnumber` | กะรายวัน |
| `Student.enrollnumber` | `StudentTimeZone.enrollnumber` |  |
| `Student.studentcode` | `TranLeave.studentcode` | การลาใช้ studentcode ไม่ใช่ enrollnumber |
| `Student.studentcode` | `transpay.empcode` | คาดว่า |
| `Student.schoolcode` | `School.schoolcode` |  |
| `Student.levelcode / levelcode2 / levelcode3` | `Level.levelcode` |  |
| `Student.shiftcode` | `Shift.shiftcode` | กะประจำ |
| `StudentShift.shiftcode` | `Shift.shiftcode` |  |
| `Student.branchcode` | `Branch.branchcode` |  |
| `Classes.levelcode` | `Level.levelcode` |  |
| `TranLeave.leavecode` | `Leave.leavecode` |  |
| `useraccesslevel.usercode` | `Users.usercode` |  |
| `useraccesslevel.levelcode` | `Level.levelcode` |  |
| `Machine.modelcode` | `MachineModel.modelcode` |  |
| `Transcantime / StudentMachine / TimeZone / StudentTimeZone / AutoLoadErr .machineno` | `Machine.machineno` |  |
| `StudentTimeZone.*timezoneno` | `TimeZone.timezoneno` |  |

**flow ข้อมูลเวลา:** เครื่องสแกน → (โปรแกรมดึงทุก `School.intervalmachine` นาที) → `Transcantime` → ประมวลผลแล้วตั้ง `recordtostudent = 1` → สรุปลง `StudentTime` (time01, time02, …) → คำนวณกับ `Shift` / `StudentShift` / `TranLeave` / `Holiday` → รายงานหรือ export ไฟล์ตาม `ExportFormat`

## 4. รายละเอียดแต่ละ Table

สัญลักษณ์: **PK** = primary key, **ID** = identity (auto increment), Null = Y คือว่างได้

### กลุ่ม: คนและเครื่องสแกน

#### Student

ข้อมูลพนักงาน/นักเรียน หนึ่งแถวต่อหนึ่งคน เป็นศูนย์กลางของระบบ  
แถวปัจจุบัน: **0** · PK constraint: `PK_Student`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `studentcode` | nvarchar(50) | Y |  | รหัสพนักงาน/นักเรียน (รหัสที่คนใช้อ้างอิง) |
| 3 | `studentname` | nvarchar(250) | Y |  | ชื่อ-สกุล (ไทย) |
| 4 | `studentnamee` | nvarchar(250) | Y |  | ชื่อ-สกุล (อังกฤษ) |
| 5 | `schoolcode` | nvarchar(50) | Y |  | → School.schoolcode |
| 6 | `levelcode` | nvarchar(50) | Y |  | → Level.levelcode (แผนก/ระดับหลัก) |
| 7 | `enrollnumber` | bigint | Y | `((0))` | รหัสที่ลงทะเบียนในเครื่องสแกน ใช้ join กับ Transcantime / StudentMachine / StudentTime |
| 8 | `mobilerecvmsg` | nvarchar(250) | Y |  | เบอร์ที่รับ SMS แจ้งเตือนการสแกน (เช่นผู้ปกครอง) |
| 9 | `cardno` | nvarchar(50) | Y |  | เลขบัตร RFID |
| 10 | `studentdate` | nvarchar(50) | Y |  | วันที่เริ่มงาน/เข้าเรียน (text) |
| 11 | `birthdate` | nvarchar(50) | Y |  | วันเกิด (text) |
| 12 | `address1` | nvarchar(250) | Y |  |  |
| 13 | `address2` | nvarchar(250) | Y |  |  |
| 14 | `province` | nvarchar(150) | Y |  |  |
| 15 | `salary` | decimal(12,2) | Y |  | เงินเดือน |
| 16 | `mobile` | nvarchar(100) | Y |  |  |
| 17 | `idcard` | nvarchar(100) | Y |  | เลขบัตรประชาชน |
| 18 | `issueby` | nvarchar(100) | Y |  | ออกบัตรโดย |
| 19 | `passport` | nvarchar(100) | Y |  |  |
| 20 | `carlicence` | nvarchar(100) | Y |  |  |
| 21 | `motorlicence` | nvarchar(100) | Y |  |  |
| 22 | `shiftflg` | int | Y | `((0))` | 0 = ใช้กะประจำ, อื่น ๆ = ใช้กะรายวันจาก StudentShift (คาดว่า) |
| 23 | `shiftcode` | nvarchar(50) | Y |  | → Shift.shiftcode กะประจำ |
| 24 | `branchcode` | nvarchar(50) | Y |  | → Branch.branchcode |
| 25 | `webusercode` | nvarchar(250) | Y |  | รหัสผู้ใช้ฝั่งเว็บ |
| 26 | `active` | bit | Y | `((1))` | 1 = ยังทำงานอยู่ |
| 27 | `retiredate` | nvarchar(50) | Y |  | วันที่ลาออก (text) |
| 28 | `pic` | nvarchar(max) | Y |  | รูปภาพ (path หรือ base64) |
| 29 | `levelcode2` | nvarchar(50) | Y |  | Level รอง |
| 30 | `levelcode3` | nvarchar(50) | Y |  | Level รอง |

#### StudentMachine

template ลายนิ้วมือ/ใบหน้าของแต่ละคนในแต่ละเครื่อง ใช้ backup/sync ขึ้นลงเครื่อง  
แถวปัจจุบัน: **0** · PK constraint: `PK_StudentMachine`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `enrollnumber` | bigint | Y | `((0))` | → Student.enrollnumber |
| 3 | `machineno` | int | Y | `((0))` | → Machine.machineno |
| 4 | `fingerno` | int | Y | `((0))` | ลำดับนิ้ว (0–9) |
| 5 | `privilege` | int | Y | `((0))` | สิทธิ์ในเครื่อง (0 = ผู้ใช้ทั่วไป, สูงกว่า = admin) |
| 6 | `password` | int | Y | `((0))` | รหัสผ่านในเครื่อง (ตัวเลข) |
| 7 | `fpdata` | varbinary(max) | Y |  | template ลายนิ้วมือ (binary) |
| 8 | `face` | varbinary(max) | Y |  | template ใบหน้า (binary) |
| 9 | `series` | nvarchar(max) | Y |  | series ของเครื่องที่ template มาจาก |
| 10 | `DataH` | nvarchar(max) | Y |  | ข้อมูล template แบบ text/hex (สำหรับเครื่องบาง series) |

#### Machine

เครื่องสแกนที่ลงทะเบียนไว้ (IP, port, รุ่น)  
แถวปัจจุบัน: **1** · PK constraint: `PK_Machine`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `machineno` | int | Y | `((0))` | เลขเครื่อง ใช้อ้างอิงจาก table อื่น |
| 3 | `machinename` | nvarchar(100) | Y |  | ชื่อเครื่อง |
| 4 | `ip` | nvarchar(50) | Y |  | IP ของเครื่อง |
| 5 | `port` | nvarchar(50) | Y |  | port เชื่อมต่อ |
| 6 | `password` | nvarchar(250) | Y | `((0))` | comm key ของเครื่อง |
| 7 | `modelcode` | nvarchar(50) | Y |  | → MachineModel.modelcode |
| 8 | `autodownloadtype` | int | Y | `((1))` | รูปแบบการดึงอัตโนมัติ |
| 9 | `snno` | nvarchar(150) | Y |  | serial number |
| 10 | `series` | nvarchar(50) | Y |  | series ของเครื่อง (ตรงกับ MachineModel.series) |
| 11 | `dnsflg` | int | Y | `((0))` | 1 = ใช้ชื่อโดเมนแทน IP |
| 12 | `inout` | nvarchar(10) | Y |  | เครื่องสำหรับเข้า/ออก |
| 13 | `uname` | nvarchar(250) | Y |  | username (เครื่องรุ่นที่มี web/API) |
| 14 | `pwd` | nvarchar(250) | Y |  | password (เครื่องรุ่นที่มี web/API) |
| 15 | `result` | nvarchar(10) | Y |  | ผลการเชื่อมต่อล่าสุด |

#### MachineModel

master รุ่นเครื่อง และความสามารถของแต่ละรุ่น (นิ้ว/บัตร/หน้า/ประตู)  
แถวปัจจุบัน: **39** · PK constraint: `PK_MqachineModel`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `modelcode` | nvarchar(50) | Y |  | ชื่อรุ่น |
| 3 | `fingerflg` | int | Y | `((0))` | 1 = รองรับลายนิ้วมือ |
| 4 | `cardflg` | int | Y | `((0))` | 1 = รองรับบัตร |
| 5 | `faceflg` | int | Y | `((0))` | 1 = รองรับใบหน้า |
| 6 | `doorflg` | int | Y |  | 1 = ควบคุมประตูได้ |
| 7 | `qtyrecord` | int | Y | `((160000))` | ความจุ log ในเครื่อง |
| 8 | `series` | nvarchar(50) | Y |  | กลุ่มของรุ่น (ใช้เลือก SDK/protocol) |

### กลุ่ม: การลงเวลา

#### Transcantime

log การสแกนดิบทุกครั้งที่ดึงจากเครื่อง (table สำคัญที่สุดด้านข้อมูลเวลา)  
แถวปัจจุบัน: **0** · PK constraint: `PK_transcantime`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `enrollnumber` | bigint | Y | `((0))` | → Student.enrollnumber |
| 3 | `machineno` | int | Y | `((0))` | → Machine.machineno |
| 4 | `verifymode` | int | Y | `((0))` | วิธียืนยันตัวตน (รหัสตัวเลขจากเครื่อง) |
| 5 | `verifymodestr` | nvarchar(50) | Y |  | วิธียืนยันตัวตนแบบข้อความ (FP/Card/Face/...) |
| 6 | `datetimescan` | nvarchar(50) | Y |  | วันเวลาที่สแกน (text) |
| 7 | `adddate` | datetime | N | `(getdate())` | เวลาที่บันทึกลง DB |
| 8 | `sendsmsflg` | int | Y | `((0))` | 1 = ส่ง SMS แล้ว |
| 9 | `sentsmsdate` | datetime | Y |  | เวลาที่ส่ง SMS |
| 10 | `sentremark` | nvarchar(250) | Y |  | ผลการส่ง SMS |
| 11 | `recordtostudent` | int | Y | `((0))` | 1 = ประมวลผลลง StudentTime แล้ว |
| 12 | `timetype` | nvarchar(5) | Y | `(N'IN')` | IN / OUT |
| 13 | `webflg` | int | Y | `((0))` | 1 = ส่งขึ้นเว็บแล้ว |
| 14 | `pic` | nvarchar(max) | Y |  | รูปที่ถ่ายตอนสแกน |
| 15 | `flgEditTime` | int | Y | `((0))` | 1 = เวลาที่แก้ไข/เพิ่มด้วยมือ |
| 16 | `result` | nvarchar(10) | Y |  | ผลการตรวจ (เครื่องรุ่นวัดอุณหภูมิ/หน้ากาก) |
| 17 | `mask` | nvarchar(10) | Y |  | ใส่หน้ากากหรือไม่ |
| 18 | `tem` | nvarchar(10) | Y |  | อุณหภูมิร่างกาย |

#### TranscantimeBK

สำเนา/backup ของ Transcantime (คอลัมน์น้อยกว่า ไม่มี pic/mask/tem)  
แถวปัจจุบัน: **0** · PK constraint: `PK_TranscantimeBK`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `int` | int | N |  | **PK** **ID** PK (ตั้งชื่อคอลัมน์ว่า int) |
| 2 | `enrollnumber` | bigint | Y |  |  |
| 3 | `machineno` | int | Y |  |  |
| 4 | `verifymode` | int | Y |  |  |
| 5 | `verifymodestr` | nvarchar(50) | Y |  |  |
| 6 | `datetimescan` | nvarchar(50) | Y |  |  |
| 7 | `adddate` | datetime | Y |  |  |
| 8 | `sendsmsflg` | int | Y |  |  |
| 9 | `sentsmsdate` | datetime | Y |  |  |
| 10 | `sentremark` | nvarchar(250) | Y |  |  |
| 11 | `recordtostudent` | int | Y | `((0))` |  |
| 12 | `timetype` | nvarchar(5) | Y | `(N'IN')` |  |
| 13 | `webflg` | int | Y | `((0))` |  |

#### StudentTime

สรุปเวลาสแกนรายวันแบบแนวนอน 1 แถว = 1 คน x 1 วัน, เวลาแต่ละครั้งอยู่ใน time01..time100  
แถวปัจจุบัน: **0** · PK constraint: `PK_StudentTime`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `enrollnumber` | bigint | Y | `((0))` | → Student.enrollnumber |
| 3 | `tdate` | nvarchar(20) | Y |  | วันที่ (text) |
| 4 | `time01` | nvarchar(50) | Y |  | เวลาสแกนครั้งที่ 1 ของวัน (time02..time100 = ครั้งถัดไป) |
| 5–43 | `time02` … `time40` | nvarchar(50) | Y | | (คอลัมน์ซ้ำรูปแบบเดียวกัน 39 คอลัมน์) |
| 44 | `smstimes` | int | Y | `((0))` | จำนวนครั้งที่ส่ง SMS ของวันนั้น |
| 45 | `editreason` | nvarchar(250) | Y |  | เหตุผลที่แก้ไขเวลา |
| 46 | `time41` | nvarchar(10) | Y |  | ตั้งแต่ time41 ขนาดลดเหลือ nvarchar(10) |
| 47–105 | `time42` … `time100` | nvarchar(10) | Y | | (คอลัมน์ซ้ำรูปแบบเดียวกัน 59 คอลัมน์) |

### กลุ่ม: กะงานและช่วงเวลา

#### StudentShift

กำหนดกะของแต่ละคนเป็นรายวัน (override กะประจำใน Student.shiftcode)  
แถวปัจจุบัน: **0** · PK constraint: `PK_StudentShift`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `enrollnumber` | bigint | Y | `((0))` | → Student.enrollnumber |
| 3 | `tdate` | nvarchar(20) | Y |  | วันที่ (text) |
| 4 | `shiftcode` | nvarchar(50) | Y |  | → Shift.shiftcode |
| 5 | `adddate` | datetime | Y | `(getdate())` | เวลาที่บันทึก |

#### Shift

master กะงาน พร้อมช่วงเวลาสแกนเข้า/พัก/ออก/OT  
แถวปัจจุบัน: **2** · PK constraint: `PK_Shift`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `shiftcode` | nvarchar(50) | Y |  | รหัสกะ |
| 3 | `shiftname` | nvarchar(150) | Y |  | ชื่อกะ |
| 4 | `starttime` | nvarchar(50) | Y |  | เวลาเข้างาน |
| 5 | `endtime` | nvarchar(50) | Y |  | เวลาเลิกงาน |
| 6 | `bst` | nvarchar(50) | Y |  | ช่วงสแกนเข้างาน: เริ่ม |
| 7 | `bet` | nvarchar(50) | Y |  | ช่วงสแกนเข้างาน: สิ้นสุด |
| 8 | `lst` | nvarchar(50) | Y |  | ช่วงสแกนออกพัก: เริ่ม |
| 9 | `let` | nvarchar(50) | Y |  | ช่วงสแกนออกพัก: สิ้นสุด |
| 10 | `est` | nvarchar(50) | Y |  | ช่วงสแกนเข้าหลังพัก: เริ่ม |
| 11 | `eet` | nvarchar(50) | Y |  | ช่วงสแกนเข้าหลังพัก: สิ้นสุด |
| 12 | `botst` | nvarchar(50) | Y |  | ช่วงสแกนเลิกงาน: เริ่ม |
| 13 | `botet` | nvarchar(50) | Y |  | ช่วงสแกนเลิกงาน: สิ้นสุด |
| 14 | `otst` | nvarchar(50) | Y |  | ช่วง OT: เริ่ม |
| 15 | `otet` | nvarchar(50) | Y |  | ช่วง OT: สิ้นสุด |
| 16 | `flgShift` | int | Y | `((0))` | ประเภทกะ (เช่น ข้ามวัน) |
| 17 | `breaktime` | nvarchar(10) | Y | `((0))` | เวลาพัก (นาที) |

#### TimeZone

Time zone ของเครื่อง (ช่วงเวลาที่อนุญาตให้สแกน/เปิดประตู) สูงสุด 7 ช่วง  
แถวปัจจุบัน: **0** · PK constraint: `PK_TimeZone`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `timezoneno` | nvarchar(50) | Y |  | เลข time zone |
| 3 | `machineno` | int | Y |  | → Machine.machineno |
| 4 | `starttime1` | nvarchar(50) | Y |  | ช่วงที่ 1 เริ่ม (ไปจนถึง starttime7/endtime7) |
| 5–17 | `endtime1` … `endtime7` | nvarchar(50) | Y | | (คอลัมน์ซ้ำรูปแบบเดียวกัน 13 คอลัมน์) |

#### StudentTimeZone

ผูกคนกับ Time zone ในแต่ละวันของสัปดาห์ ต่อเครื่อง  
แถวปัจจุบัน: **0** · PK constraint: `PK_StudentTimeZone`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `enrollnumber` | bigint | Y |  | → Student.enrollnumber |
| 3 | `machineno` | int | Y |  | → Machine.machineno |
| 4 | `suntimezoneno` | nvarchar(50) | Y |  | time zone วันอาทิตย์ (→ TimeZone.timezoneno), วันอื่นเหมือนกัน |
| 5 | `montimezoneno` | nvarchar(50) | Y |  |  |
| 6 | `tuetimezoneno` | nvarchar(50) | Y |  |  |
| 7 | `wedtimezoneno` | nvarchar(50) | Y |  |  |
| 8 | `thutimezoneno` | nvarchar(50) | Y |  |  |
| 9 | `fritimezoneno` | nvarchar(50) | Y |  |  |
| 10 | `sattimezoneno` | nvarchar(50) | Y |  |  |

### กลุ่ม: การลาและวันหยุด

#### Leave

master ประเภทการลา  
แถวปัจจุบัน: **0** · PK constraint: `PK_Leave`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `leavecode` | nvarchar(50) | Y |  | รหัสประเภทลา |
| 3 | `leavename` | nvarchar(200) | Y |  | ชื่อประเภทลา |

#### TranLeave

รายการลาของแต่ละคน  
แถวปัจจุบัน: **0** · PK constraint: `PK_TranLeave`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `studentcode` | nvarchar(50) | Y |  | → Student.studentcode (ไม่ใช่ enrollnumber) |
| 3 | `leavedate` | nvarchar(20) | Y |  | วันที่ลา (text) |
| 4 | `leavecode` | nvarchar(50) | Y |  | → Leave.leavecode |
| 5 | `starttime` | nvarchar(50) | Y |  | ลาตั้งแต่ |
| 6 | `endtime` | nvarchar(50) | Y |  | ลาถึง |
| 7 | `reason` | nvarchar(250) | Y |  | เหตุผล |

#### Holiday

วันหยุดบริษัท/โรงเรียน  
แถวปัจจุบัน: **0** · PK constraint: `PK_Holiday`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `holdate` | datetime | Y | `(getdate())` | วันหยุด |
| 3 | `holreason` | nvarchar(max) | Y |  | ชื่อ/เหตุผลวันหยุด |

### กลุ่ม: องค์กร

#### School

ข้อมูลบริษัท/โรงเรียน และค่าตั้งค่าระบบทั้งหมด (เวลาทำงาน, วันทำงาน, auto download, SMS, LINE, email)  
แถวปัจจุบัน: **1** · PK constraint: `PK_School`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `systemname` | nvarchar(150) | Y |  | ชื่อระบบ |
| 3 | `schoolcode` | nvarchar(50) | Y |  | รหัสบริษัท/โรงเรียน |
| 4 | `schoolname` | nvarchar(250) | Y |  | ชื่อบริษัท/โรงเรียน |
| 5 | `address1` | nvarchar(250) | Y |  |  |
| 6 | `address2` | nvarchar(250) | Y |  |  |
| 7 | `province` | nvarchar(250) | Y |  |  |
| 8 | `zipcode` | nvarchar(50) | Y |  |  |
| 9 | `starttime` | nvarchar(50) | Y |  | เวลาเข้างานมาตรฐาน |
| 10 | `endtime` | nvarchar(50) | Y |  | เวลาเลิกงานมาตรฐาน |
| 11 | `satwork` | int | Y | `((0))` | 1 = ทำงานวันเสาร์ |
| 12 | `sunwork` | int | Y | `((0))` | 1 = ทำงานวันอาทิตย์ |
| 13 | `autodownload` | int | Y | `((0))` | 1 = เปิดดึงข้อมูลอัตโนมัติ |
| 14 | `autosendsms` | int | Y | `((0))` | 1 = ส่ง SMS อัตโนมัติ |
| 15 | `sendpicflg` | int | Y | `((0))` | 1 = ส่งรูปไปด้วย |
| 16 | `intervalmachine` | int | Y | `((10))` | รอบดึงข้อมูลจากเครื่อง (นาที) |
| 17 | `smslimittime` | int | Y | `((2))` | จำกัดจำนวน SMS ต่อวัน |
| 18 | `smsprefix` | nvarchar(250) | Y |  | ข้อความนำหน้า SMS |
| 19 | `sendaslevel` | int | Y | `((0))` | 1 = ส่งแจ้งเตือนตาม Level |
| 20 | `linetokenaccess` | nvarchar(250) | Y |  | LINE Notify token |
| 21 | `intervaltime` | int | Y | `((10))` | รอบเวลาทำงานของ service (นาที) |
| 22 | `active` | bit | Y | `((1))` |  |
| 23 | `usephotosendsms` | int | Y |  | 1 = ส่งรูปใน SMS/LINE |
| 24 | `emppictpath` | nvarchar(250) | Y |  | โฟลเดอร์เก็บรูปพนักงาน |
| 25 | `webunique` | nvarchar(max) | Y |  | key ฝั่งเว็บ |
| 26 | `smsonlyfirstlastlfg` | int | Y |  | 1 = ส่ง SMS เฉพาะสแกนครั้งแรก/สุดท้าย |
| 27 | `cutminute` | int | Y | `((0))` | ตัดเศษนาที |
| 28 | `sendemail` | nvarchar(250) | Y | `(N'')` | email ผู้ส่ง |
| 29 | `sendemailpassword` | nvarchar(250) | Y | `(N'')` | รหัสผ่าน email ผู้ส่ง |
| 30 | `recvemail` | nvarchar(250) | Y | `(N'')` | email ผู้รับ |
| 31 | `lastsendmail` | nvarchar(25) | Y | `(N'')` | ส่ง email ล่าสุดเมื่อไร |
| 32 | `smtpserver` | nvarchar(250) | Y | `(N'')` | SMTP server |
| 33 | `monwork` | int | Y | `((1))` | 1 = ทำงานวันจันทร์ (tue..fri เหมือนกัน) |
| 34 | `tuework` | int | Y | `((1))` |  |
| 35 | `wedwork` | int | Y | `((1))` |  |
| 36 | `thuwork` | int | Y | `((1))` |  |
| 37 | `friwork` | int | Y | `((1))` |  |
| 38 | `chkrestart` | int | Y | `((0))` | flag restart service |

#### Branch

สาขา  
แถวปัจจุบัน: **0** · PK constraint: `PK_Branch`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `branchid` | int | N |  | **PK** **ID** |
| 2 | `branchcode` | nvarchar(50) | Y |  | รหัสสาขา |
| 3 | `branchname` | nvarchar(250) | Y |  | ชื่อสาขา |
| 4 | `active` | bit | Y |  |  |

#### Level

แผนก/ระดับชั้น (ใช้แบ่งกลุ่มคน, มี LINE token แยกต่อกลุ่มได้)  
แถวปัจจุบัน: **0** · PK constraint: `PK_level`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `levelid` | int | N |  | **PK** **ID** |
| 2 | `levelcode` | nvarchar(50) | Y |  | รหัสแผนก/ระดับ |
| 3 | `levelname` | nvarchar(250) | Y |  | ชื่อ |
| 4 | `linetokenaccess` | nvarchar(250) | Y |  | LINE token ของกลุ่มนี้ |
| 5 | `fullqty` | int | Y | `((0))` | จำนวนคนทั้งหมด |
| 6 | `comeqty` | int | Y | `((0))` | จำนวนคนที่มาแล้ว |
| 7 | `active` | bit | Y | `((1))` |  |

#### Classes

ห้องเรียน/กลุ่มย่อยภายใต้ Level  
แถวปัจจุบัน: **0** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **ID** |
| 2 | `classcode` | nvarchar(50) | Y |  |  |
| 3 | `classname` | nvarchar(250) | Y |  |  |
| 4 | `levelcode` | nvarchar(50) | Y |  | → Level.levelcode |
| 5 | `active` | bit | Y | `((1))` |  |

### กลุ่ม: ผู้ใช้โปรแกรม

#### Users

ผู้ใช้ที่ login เข้าโปรแกรม Synctime  
แถวปัจจุบัน: **0** · PK constraint: `PK_Users`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `usercode` | nvarchar(50) | Y |  | รหัสผู้ใช้ (ใช้ login) |
| 3 | `username` | nvarchar(250) | Y |  | ชื่อผู้ใช้ |
| 4 | `usertype` | nvarchar(50) | Y | `((0))` | ประเภทผู้ใช้ |
| 5 | `userusertype` | nvarchar(50) | Y |  |  |
| 6 | `password` | nvarchar(250) | Y |  | รหัสผ่าน (nvarchar — น่าจะเก็บ plain text) |

#### useraccesslevel

สิทธิ์ของผู้ใช้ว่าเห็น Level ไหนได้บ้าง  
แถวปัจจุบัน: **0** · PK constraint: `PK_useraccesslevel`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `usercode` | nvarchar(50) | Y |  | → Users.usercode |
| 3 | `levelcode` | nvarchar(50) | Y |  | → Level.levelcode |

### กลุ่ม: เงินเดือน

#### transpay

ผลการคำนวณเงินเดือนต่อคนต่องวด (รายได้, OT, รายการหัก, ภาษี)  
แถวปัจจุบัน: **0** · PK constraint: `PK_transpay`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `caldatecode` | nvarchar(50) | Y |  | รหัสงวดเงินเดือน |
| 3 | `empcode` | nvarchar(50) | Y |  | → Student.studentcode (คาดว่า) |
| 4 | `running` | nvarchar(50) | Y |  | เลขลำดับ |
| 5 | `salwage` | nvarchar(max) | Y | `((0))` | เงินเดือน/ค่าแรง |
| 6 | `workday` | decimal(12,2) | Y | `((0))` | จำนวนวันทำงาน |
| 7 | `bonus` | decimal(12,2) | Y | `((0))` |  |
| 8 | `hourot1` | nvarchar(50) | Y | `(N'')` | ชั่วโมง OT 1 เท่า |
| 9 | `hourot15` | nvarchar(50) | Y | `(N'')` | ชั่วโมง OT 1.5 เท่า |
| 10 | `hourot2` | nvarchar(50) | Y | `(N'')` | ชั่วโมง OT 2 เท่า |
| 11 | `hourot3` | nvarchar(50) | Y | `(N'')` | ชั่วโมง OT 3 เท่า |
| 12 | `ot1amt` | decimal(12,2) | Y | `((0))` | เงิน OT 1 เท่า |
| 13 | `ot15amt` | decimal(12,2) | Y | `((0))` |  |
| 14 | `ot2amt` | decimal(12,2) | Y | `((0))` |  |
| 15 | `ot3amt` | decimal(12,2) | Y | `((0))` |  |
| 16 | `diligence` | decimal(12,2) | Y |  | เบี้ยขยัน |
| 17 | `commission` | decimal(12,2) | Y | `((0))` |  |
| 18 | `posivalue` | decimal(12,2) | Y | `((0))` | ค่าตำแหน่ง |
| 19 | `professionalfee` | decimal(12,2) | Y | `((0))` | ค่าวิชาชีพ |
| 20 | `allowance` | decimal(12,2) | Y | `((0))` |  |
| 21 | `food` | decimal(12,2) | Y | `((0))` |  |
| 22 | `fuel` | decimal(12,2) | Y | `((0))` |  |
| 23 | `otherincome` | decimal(12,2) | Y | `((0))` |  |
| 24 | `otherincomedesc` | nvarchar(150) | Y |  |  |
| 25 | `othercompincome` | decimal(12,2) | Y | `((0))` |  |
| 26 | `minuslate` | decimal(12,2) | Y | `((0))` | หักมาสาย |
| 27 | `minusleave` | decimal(12,2) | Y | `((0))` | หักลา |
| 28 | `minusinsure` | decimal(12,2) | Y | `((0))` | หักประกันสังคม |
| 29 | `minustax` | decimal(12,2) | Y | `((0))` | หักภาษี |
| 30 | `minusother` | decimal(12,2) | Y | `((0))` |  |
| 31 | `minusborrow` | decimal(12,2) | Y | `((0))` | หักเงินยืม |
| 32 | `minusotherdesc` | nvarchar(150) | Y |  |  |
| 33 | `caldate` | datetime | Y | `(getdate())` | วันที่คำนวณ |
| 34 | `caltaxflg` | bit | Y | `((0))` | 1 = คำนวณภาษี |
| 35 | `salcal` | nvarchar(max) | Y |  |  |
| 36 | `totincome` | nvarchar(max) | Y |  | รายได้รวม |
| 37 | `deduceincome` | decimal(12,2) | Y | `((0))` | ค่าลดหย่อน |
| 38 | `deducewifeincome` | decimal(12,2) | Y | `((0))` |  |
| 39 | `deducesonqty` | int | Y | `((0))` | จำนวนบุตร |
| 40 | `deducesonexpense` | decimal(12,2) | Y | `((0))` |  |
| 41 | `socialinsurepc` | decimal(12,2) | Y | `((0))` | % ประกันสังคม |
| 42 | `active` | bit | Y |  |  |

### กลุ่ม: ตั้งค่า/ระบบ

#### ExportFormat

รูปแบบการ export ไฟล์เวลา (text) ไปให้โปรแกรมเงินเดือนอื่น  
แถวปัจจุบัน: **1** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `filetype` | nvarchar(50) | Y |  | ชนิดไฟล์ |
| 2 | `symbol` | nvarchar(50) | Y |  | ตัวคั่น |
| 3 | `qty` | int | Y |  | จำนวน |
| 4 | `usesymbolflg` | int | Y |  |  |
| 5 | `saveflg` | int | Y |  | 1 = บันทึกไฟล์อัตโนมัติ |
| 6 | `savelocation` | nvarchar(250) | Y |  | โฟลเดอร์ปลายทาง |
| 7 | `dateformat` | nvarchar(50) | Y |  | รูปแบบวันที่ |
| 8 | `openflg` | int | Y |  |  |
| 9 | `rpt1field` | nvarchar(250) | Y |  | ฟิลด์ลำดับที่ 1 ในไฟล์ (ถึง rpt15field) |
| 10 | `rpt2field` | nvarchar(250) | Y |  |  |
| 11 | `rpt3field` | nvarchar(250) | Y |  |  |
| 12 | `rpt4field` | nvarchar(250) | Y |  |  |
| 13 | `rpt5field` | nvarchar(250) | Y |  |  |
| 14 | `rpt6field` | nvarchar(250) | Y |  |  |
| 15 | `rpt7field` | nvarchar(250) | Y |  |  |
| 16 | `rpt8field` | nvarchar(250) | Y |  |  |
| 17 | `rpt9field` | nvarchar(250) | Y |  |  |
| 18 | `rpt10field` | nvarchar(250) | Y |  |  |
| 19 | `rpt11field` | nvarchar(250) | Y |  |  |
| 20 | `rpt12field` | nvarchar(250) | Y |  |  |
| 21 | `rpt13field` | nvarchar(250) | Y |  |  |
| 22 | `rpt14field` | nvarchar(250) | Y |  |  |
| 23 | `rpt15field` | nvarchar(250) | Y |  |  |
| 24 | `eachfieldlenflg` | int | Y |  | 1 = กำหนดความยาวแต่ละฟิลด์ |
| 25 | `rptfield1len` | nvarchar(250) | Y |  | ความยาวฟิลด์ที่ 1 (ถึง rptfield15len) |
| 26 | `rptfield2len` | nvarchar(250) | Y |  |  |
| 27 | `rptfield3len` | nvarchar(250) | Y |  |  |
| 28 | `rptfield4len` | nvarchar(250) | Y |  |  |
| 29 | `rptfield5len` | nvarchar(250) | Y |  |  |
| 30 | `rptfield6len` | nvarchar(250) | Y |  |  |
| 31 | `rptfield7len` | nvarchar(250) | Y |  |  |
| 32 | `rptfield8len` | nvarchar(250) | Y |  |  |
| 33 | `rptfield9len` | nvarchar(250) | Y |  |  |
| 34 | `rptfield10len` | nvarchar(250) | Y |  |  |
| 35 | `rptfield11len` | nvarchar(250) | Y |  |  |
| 36 | `rptfield12len` | nvarchar(250) | Y |  |  |
| 37 | `rptfield13len` | nvarchar(250) | Y |  |  |
| 38 | `rptfield14len` | nvarchar(250) | Y |  |  |
| 39 | `rptfield15len` | nvarchar(250) | Y |  |  |
| 40 | `frontspace` | int | Y |  |  |
| 41 | `showsecond` | int | Y |  | 1 = แสดงวินาที |
| 42 | `leftside` | int | Y |  |  |
| 43 | `timeformat` | nvarchar(50) | Y |  | รูปแบบเวลา |
| 44 | `ScantimeType` | int | Y | `((0))` |  |
| 45 | `symbol1` | nvarchar(50) | Y |  |  |
| 46 | `usesymbolflg1` | int | Y | `((0))` |  |
| 47 | `fixcol_oneflg` | int | Y | `((0))` |  |
| 48 | `tem` | nvarchar(max) | Y |  |  |
| 49 | `mask` | nvarchar(10) | Y |  |  |
| 50 | `temin` | nvarchar(10) | Y |  |  |
| 51 | `vol` | nvarchar(10) | Y |  |  |
| 52 | `lag` | nvarchar(10) | Y |  |  |

#### SetExportFormat

กำหนดคอลัมน์ของไฟล์ export แบบละเอียด  
แถวปัจจุบัน: **0** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `Id` | int | N |  | **ID** |
| 2 | `idcol` | nvarchar(50) | Y |  |  |
| 3 | `colname` | nvarchar(50) | Y |  |  |
| 4 | `colwidth` | int | Y |  |  |
| 5 | `colformat` | nvarchar(50) | Y |  |  |
| 6 | `colchkflg` | int | Y |  |  |
| 7 | `colrdflg` | int | Y |  |  |
| 8 | `coltxtsysbol` | nvarchar(50) | Y |  |  |
| 9 | `colqty` | int | Y |  |  |
| 10 | `coltypeflg` | int | Y |  |  |

#### repport

table ชั่วคราวสำหรับทำรายงาน (rep01..rep12 เป็น text ทั้งหมด)  
แถวปัจจุบัน: **0** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1–12 | `rep01` … `rep12` | nvarchar(150) | Y | | (คอลัมน์ซ้ำรูปแบบเดียวกัน 12 คอลัมน์) |

#### AutoLoadTime

เวลาที่ตั้งให้ดึงข้อมูลจากเครื่องอัตโนมัติ (HH:MM)  
แถวปัจจุบัน: **0** · PK constraint: `PK_AutoLoadTime`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `loadtime` | nvarchar(10) | Y | `(CONVERT([varchar](5),getdate(),(108)))` | เวลาดึงข้อมูล HH:MM |

#### AutoLoadErr

log error ตอนดึงข้อมูลจากเครื่องอัตโนมัติ  
แถวปัจจุบัน: **0** · PK constraint: `PK_AutoDownLoadErr`

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `id` | int | N |  | **PK** **ID** |
| 2 | `machineno` | int | Y |  | → Machine.machineno |
| 3 | `errmsg` | nvarchar(max) | Y |  | ข้อความ error |
| 4 | `errdate` | datetime | Y | `(getdate())` | เวลาที่เกิด |
| 5 | `machinename` | nvarchar(max) | Y |  |  |
| 6 | `errcode` | nvarchar(50) | Y |  | รหัส error |

#### ckelocation

path ที่โปรแกรมใช้ (ค่าปัจจุบัน c:\)  
แถวปัจจุบัน: **1** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `location` | nvarchar(50) | Y |  |  |

#### ckenamepc

ชื่อเครื่อง PC ที่ติดตั้งโปรแกรม และสถานะ (น่าจะใช้ตรวจ license)  
แถวปัจจุบัน: **0** · **ไม่มี Primary Key**

| # | คอลัมน์ | ชนิด | Null | Default | คำอธิบาย |
|--:|---|---|:-:|---|---|
| 1 | `namepc` | nvarchar(150) | Y |  |  |
| 2 | `status` | int | Y |  |  |

## 5. ข้อมูลที่มีอยู่ตอนนี้

### School

| คอลัมน์ | ค่า |
|---|---|
| `systemname` | HIP Time 4.0 |
| `schoolcode` | HIP |
| `schoolname` | HIP Global Co., Ltd. |
| `starttime` | 08:00 |
| `endtime` | 17:30 |
| `satwork` | 0 |
| `sunwork` | 0 |
| `monwork` | 1 |
| `tuework` | 1 |
| `wedwork` | 1 |
| `thuwork` | 1 |
| `friwork` | 1 |
| `autodownload` | 0 |
| `intervalmachine` | 10 |
| `intervaltime` | 10 |
| `cutminute` | 0 |
| `emppictpath` | C:\HIP_IMAGE |

ทำงานจันทร์–ศุกร์ 08:00–17:30 ไม่ทำงานเสาร์-อาทิตย์ ยังไม่ได้เปิด auto download (ค่าที่เกี่ยวกับ email/LINE/SMS ไม่ได้ใส่ไว้ในไฟล์นี้)

### Machine

| machineno | machinename | ip | port | modelcode | autodownloadtype | snno | series | dnsflg | inout |
|---|---|---|---|---|---|---|---|---|---|
| 1 | fk_device | 192.168.0.106 | 7005 | CiF77S | 1 | 77S2601039 | S | 0 | 0 |

รหัส comm key / username / password ของเครื่องไม่ได้ใส่ไว้ในไฟล์นี้

### Shift

| id | shiftcode | shiftname | start | end | bst | bet | lst | let | est | eet | botst | botet | otst | otet | flgShift | breaktime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 01 | กะงานปกติ | 08:00 | 17:00 | 06:00 | 08:00 | 12:01 | 12:30 | 12:02 | 13:00 | 17:30 | 18:00 | 18:00 | 22:00 | 0 | 0 |
| 2 | 99 | กะวันหยุด | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 00:00 | 0 | 0 |

อ่านกะ `01`: เข้างาน 08:00 (สแกนเข้าได้ 06:00–08:00), ออกพัก 12:01–12:30, เข้าหลังพัก 12:02–13:00, เลิกงาน 17:00 (สแกนออกได้ 17:30–18:00), OT 18:00–22:00

### ExportFormat

| คอลัมน์ | ค่า |
|---|---|
| `filetype` | T |
| `symbol` | , |
| `qty` | 1 |
| `usesymbolflg` | 1 |
| `saveflg` | 1 |
| `savelocation` | D:\ExportTime |
| `dateformat` | dd-MM-yyyy |
| `timeformat` | NULL |
| `openflg` | 1 |
| `rpt1field` | NULL |
| `rpt2field` | NULL |
| `rpt3field` | NULL |
| `rpt4field` | NULL |
| `rpt5field` | NULL |
| `frontspace` | NULL |
| `showsecond` | NULL |
| `leftside` | NULL |
| `ScantimeType` | 0 |

### ckelocation

`location` = `c:\`

### MachineModel (39 รุ่น)

| modelcode | นิ้ว | บัตร | หน้า | ประตู | ความจุ log | series |
|---|:-:|:-:|:-:|:-:|--:|---|
| Ci100S |  | ✓ |  | ✓ | 160,000 | S |
| Ci690S | ✓ | ✓ |  | ✓ | 160,000 | S |
| Ci680S | ✓ | ✓ |  | ✓ | 160,000 | S |
| Ci691S | ✓ | ✓ |  | ✓ | 160,000 | S |
| Ci691TS | ✓ | ✓ |  | ✓ | 160,000 | S |
| CiF69S | ✓ | ✓ | ✓ | ✓ | 160,000 | S |
| CiF69TS | ✓ | ✓ | ✓ | ✓ | 200,000 | S |
| CMi681S | ✓ | ✓ |  |  | 160,000 | S |
| CMi682S | ✓ | ✓ |  |  | 160,000 | S |
| CMi683S | ✓ | ✓ |  |  | 160,000 | S |
| CMiF63S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CMiF65S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CMiF66S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CMiF68S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CMiF68S PLUS | ✓ | ✓ | ✓ | ✓ | 160,000 | S |
| CMi671S | ✓ | ✓ |  |  | 200,000 | S |
| CMi58S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CMiF75S | ✓ | ✓ | ✓ |  | 200,000 | S |
| CiF76S | ✓ | ✓ | ✓ | ✓ | 200,000 | S |
| CiF77S | ✓ | ✓ | ✓ | ✓ | 200,000 | S |
| CiF91S-VL | ✓ | ✓ | ✓ | ✓ | 200,000 | S-VL |
| CiF93S-VL | ✓ | ✓ | ✓ | ✓ | 200,000 | S-VL |
| CMiF95S-VL | ✓ | ✓ | ✓ |  | 200,000 | S-VL |
| CiF263 | ✓ | ✓ | ✓ | ✓ | 150,000 | 2-VL |
| CiF265-VL | ✓ | ✓ | ✓ | ✓ | 150,000 | 2-VL |
| CiF273-VL | ✓ | ✓ | ✓ | ✓ | 300,000 | 2-VL |
| CMi511C | ✓ | ✓ |  | ✓ | 200,000 | Synctime |
| CMiF54C | ✓ | ✓ | ✓ | ✓ | 200,000 | Synctime |
| CiF55C | ✓ | ✓ | ✓ | ✓ | 200,000 | Synctime |
| CMTV923 |  |  | ✓ |  | 200,000 | Camera |
| CMTV924 |  |  | ✓ |  | 200,000 | Camera |
| facetab |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF301 |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF503 |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF410 |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF730 |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF730-C |  | ✓ | ✓ |  | 200,000 | facetab |
| CiF510-FP | ✓ | ✓ | ✓ |  | 200,000 | facetab |
| CIF718 |  |  | ✓ |  | 50,000 | CIF718 |

## 6. ข้อสังเกตและจุดที่ต้องระวัง

- **ไม่มี Foreign Key** ลบหรือเปลี่ยนรหัสใน master (`Level`, `Shift`, `Student`) แล้ว DB จะไม่กันให้ ข้อมูลอาจกำพร้าได้
- **วันที่/เวลาเก็บเป็น text** (`Transcantime.datetimescan`, `StudentTime.tdate`, `Shift.*time`, `Student.birthdate` ฯลฯ) ต้อง `CONVERT`/`TRY_CONVERT` ก่อนเทียบหรือเรียง และรูปแบบอาจไม่เหมือนกันทุกแถว (ยังไม่มีข้อมูลให้ตรวจ)
- **กุญแจ join มีสองแบบ**: ฝั่งเครื่องสแกนใช้ `enrollnumber` (bigint) แต่ `TranLeave`/`transpay` ใช้ `studentcode`/`empcode` (text)
- **ไม่มี index นอกจาก PK** — ถ้า `Transcantime` มีหลายแสนแถว query ตาม `enrollnumber`/`datetimescan` จะ scan ทั้ง table ควรเพิ่ม index เช่น `(enrollnumber, datetimescan)` ถ้าจะใช้งานจริง
- **`StudentTime` เป็นแบบแนวนอน** (time01..time100) ถ้าจะวิเคราะห์ควรใช้ `Transcantime` หรือ `UNPIVOT`
- `time01`–`time40` เป็น nvarchar(50) แต่ `time41`–`time100` เป็น nvarchar(10) ขนาดไม่เท่ากัน
- `TranscantimeBK` ตั้งชื่อคอลัมน์ PK ว่า `int` · table ที่ไม่มี PK: `Classes`, `ExportFormat`, `SetExportFormat`, `ckelocation`, `ckenamepc`, `repport` (`Classes`/`SetExportFormat` มี `id` identity แต่ไม่ได้ตั้งเป็น PK)
- **ข้อมูลอ่อนไหว**: `Users.password`, `Machine.password/pwd`, `School.sendemailpassword`, `School.linetokenaccess` เป็น nvarchar ธรรมดา น่าจะเก็บ plain text · `Student.idcard`, `salary`, `StudentMachine.fpdata/face` เป็นข้อมูลส่วนบุคคล/ชีวมิติ (PDPA)
- ชื่อ table/คอลัมน์สะกดไม่สม่ำเสมอ เช่น `repport`, `smsonlyfirstlastlfg`, `coltxtsysbol`, PK ชื่อ `PK_MqachineModel`

## 7. Query ที่ใช้บ่อย

```sql
-- log สแกนพร้อมชื่อคน
SELECT s.studentcode, s.studentname, t.datetimescan, t.timetype, t.verifymodestr, m.machinename
FROM Transcantime t
LEFT JOIN Student s ON s.enrollnumber = t.enrollnumber
LEFT JOIN Machine m ON m.machineno = t.machineno
ORDER BY t.id DESC;

-- สแกนครั้งแรก/สุดท้ายของแต่ละคนต่อวัน (สมมติ datetimescan เป็นรูปแบบที่ CONVERT ได้)
SELECT enrollnumber,
       CAST(TRY_CONVERT(datetime, datetimescan) AS date) AS d,
       MIN(TRY_CONVERT(datetime, datetimescan)) AS first_in,
       MAX(TRY_CONVERT(datetime, datetimescan)) AS last_out
FROM Transcantime
GROUP BY enrollnumber, CAST(TRY_CONVERT(datetime, datetimescan) AS date);

-- กะที่ใช้จริงของคนในวันหนึ่ง (กะรายวันก่อน ถ้าไม่มีใช้กะประจำ)
SELECT s.enrollnumber, s.studentname, COALESCE(ss.shiftcode, s.shiftcode) AS shiftcode
FROM Student s
LEFT JOIN StudentShift ss ON ss.enrollnumber = s.enrollnumber AND ss.tdate = '2026-10-17';

-- ดึงโครงสร้าง table ใหม่ (ถ้า schema เปลี่ยน)
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_NAME, ORDINAL_POSITION;
```
