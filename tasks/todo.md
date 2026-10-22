# Tasks: LINE Web Report & CI/CD Private Repo

- [x] Task 1: สร้าง `recipients.py` จัดการผู้รับรายงานใน `data/recipients.json`
- [x] Task 2: สร้าง Web Server (`web.py`) และหน้า UI (`web/index.html`)
- [ ] Task 3: ปรับปรุง `main.py` ให้รัน Web Server ควบคู่กับ Scheduler และดึงผู้รับจาก `recipients.py`
- [ ] Task 4: อัปเดต `docker-compose.yml` เปิดพอร์ต 8090 และ mount persistent volume
- [ ] Checkpoint 1: Rebuild Docker และทดสอบระบบ
- [ ] Task 5: สร้าง `.gitignore` ป้องกัน `.env` และ credentials
- [ ] Task 6: สร้าง GitHub Actions CI Workflow (`.github/workflows/ci.yml`)
- [ ] Task 7: Git init และสร้าง initial commit
- [ ] Task 8: สร้าง Private Repo บน GitHub (`gh repo create`) และ push `main`
- [ ] Checkpoint 2: ตรวจสอบ CI บน GitHub ว่าผ่าน 100%
