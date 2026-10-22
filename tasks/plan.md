# Implementation Plan: Web Management, Multi-Schedule & CI/CD Private Repo

## Overview
พัฒนาระบบ Web UI จัดการผู้รับรายงาน LINE สำหรับระบบสแกนนิ้ว HIP TIME 4.0 ส่งตามเวลา 09:00 และ 18:00 น. พร้อมตั้งค่า CI/CD Quality Gate (GitHub Actions) และ Commit/Push ขึ้น GitHub Private Repository อย่างปลอดภัย โดยไม่ให้ Secrets หลุด

## Architecture Decisions
- **Unified Container**: รันทั้ง Background Scheduler และ Web Server (พอร์ต 8090) ภายใน container เดียวกันด้วย threading
- **Security First**: ตรวจสอบ `.gitignore` อย่างเข้มงวด ป้องกัน `.env` และ credentials ทั้งหมดไม่ให้เข้า Git
- **CI/CD Quality Gates**:
  1. Python syntax & lint check
  2. Automated Unit Tests (11/11 tests pass)
  3. Docker image build verification
- **Version Control**: สร้าง GitHub Private Repository ภายใต้บัญชี `@Ahmadaduwa` ผ่าน `gh repo create --private`

## Task List

### Phase 1: Complete Web Server & Scheduler Integration
- [x] Task 1: สร้าง `recipients.py` สำหรับ CRUD ผู้รับรายงานใน `data/recipients.json`
- [x] Task 2: สร้าง Web Server (`web.py`) และ Web UI (`web/index.html`)
- [ ] Task 3: เชื่อมโยง `main.py` ให้รัน Web Server ควบคู่กับ Scheduler และใช้ผู้รับจาก `recipients.py`
- [ ] Task 4: อัปเดต `docker-compose.yml` เปิดพอร์ต 8090 และ mount data volume

### Checkpoint: Local Docker Verification
- [ ] Rebuild container และทดสอบเปิดหน้าเว็บ `http://localhost:8090` และรัน test suite

### Phase 2: Security, CI/CD & Private Repository
- [ ] Task 5: สร้าง `.gitignore` ที่รัดกุม (ละเว้น `.env`, credentials, data volumes, cache)
- [ ] Task 6: สร้าง GitHub Actions CI Workflow (`.github/workflows/ci.yml`) ทดสอบ test suite และ build
- [ ] Task 7: Git init, commit โค้ดทั้งหมด
- [ ] Task 8: สร้าง GitHub Private Repository และ push ขึ้น remote branch `main`

### Checkpoint: Complete
- [ ] CI pipeline runs and passes on GitHub
- [ ] Repository is private and safe from secret leaks
