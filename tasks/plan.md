# Implementation Plan: Python 3.8.10 (Windows 7 32-bit) & Target Server Simulation

## Overview
ปรับปรุงระบบ `line-report` ให้รองรับ Python 3.8.10 (32-bit x86) สำหรับติดตั้งและใช้งานบน Windows 7 พร้อมสร้างชุดสคริปต์ 1-Click ติดตั้งเป็น Windows Task Scheduler และสร้างระบบจำลองสภาพแวดล้อม (Simulation Environment) ให้เหมือนเครื่อง Windows 7 + SQL Server 2012 `hiptime` จริงมากที่สุด ทั้งในแบบ Docker Compose และ Offline Mock Mode

## Key Decisions & Architecture
1. **Python 3.8.10 Compatibility**:
   - ปรับ Type Annotations ทั้งหมดให้รองรับ Python 3.8 (ใช้ `typing.Optional`, `typing.List`, `typing.Dict` หรือ `from __future__ import annotations`)
   - อัปเดต `line-report/Dockerfile` เป็น `python:3.8.10-slim`
2. **Hybrid Authentication**:
   - รองรับ Windows Authentication (เมื่อรันบน Windows 7 ผ่าน `pyodbc` โดยไม่ต้องรู้รหัส `sa`)
   - รองรับ SQL Server Authentication (`sa` + password ผ่าน `pymssql`)
   - ฐานข้อมูลค่าเริ่มต้น: `hiptime` (ตรงตามโปรแกรม HIP Time 4.0)
3. **Realistic Simulation**:
   - **Docker Simulation**: อัปเดต `docker-compose.yml` และ init script สร้างฐานข้อมูล `hiptime` พร้อม Table และข้อมูลพนักงานตามหน้าจอจริง (ID 1, 2, 3, 10, 99, 159, 1111)
   - **Offline Mock Mode**: รันด้วย `--mock` หรือ `DB_MOCK=true` เพื่อทดสอบระบบได้ทันทีโดยไม่ต้องรัน SQL Server
4. **Windows 7 1-Click Installer**:
   - `install.bat`: ตรวจสอบ/สร้าง venv, ลง `requirements.txt`, และลงทะเบียน Task Scheduler
   - `run_manual.bat`: รันทดสอบแบบเห็น Log ทันที
   - `uninstall.bat`: ถอนการติดตั้ง Service/Task
5. **CI/CD Quality Gates**:
   - อัปเดต GitHub Actions Matrix ให้ทดสอบทั้ง Python 3.8 และ 3.12
