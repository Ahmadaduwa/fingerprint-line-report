"""
ระบบบันทึกและจัดการ Log (Memory Ring Buffer + File Log)
เก็บ Log ล่าสุดเพื่อให้ผู้ใช้กดดูและ Copy Log ส่งให้นาย/ทีมงานตรวจสอบได้ง่ายจากหน้าเว็บ
"""
from __future__ import annotations
import collections
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional

MAX_LOGS = 500

class RingBufferHandler(logging.Handler):
    """เก็บ Log ใน Memory แบบ FIFO สูงสุด MAX_LOGS รายการ"""
    def __init__(self, capacity: int = MAX_LOGS):
        super().__init__()
        self.buffer = collections.deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            err_details = None
            if record.exc_info:
                err_details = "".join(traceback.format_exception(*record.exc_info))
            self.buffer.append({
                "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "formatted": msg,
                "error_details": err_details,
            })
        except Exception:
            self.handleError(record)

    def get_logs(self, limit: int = 200, level: Optional[str] = None) -> List[Dict]:
        items = list(self.buffer)
        if level:
            level_upper = level.upper()
            items = [x for x in items if x["level"] == level_upper]
        return items[-limit:]

    def clear(self):
        self.buffer.clear()


_ring_handler: Optional[RingBufferHandler] = None


def setup_logging(data_dir: str = "data", level: int = logging.INFO) -> RingBufferHandler:
    """ตั้งค่า Logging ทั้งลง Console, File (`data/app.log`), และ RingBuffer"""
    global _ring_handler
    if _ring_handler is not None:
        return _ring_handler

    os.makedirs(data_dir, exist_ok=True)
    log_file = os.path.join(data_dir, "app.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 1. Console Handler
    console_h = logging.StreamHandler(sys.stdout)
    console_h.setFormatter(formatter)
    console_h.setLevel(level)
    root_logger.addHandler(console_h)

    # 2. File Handler (UTF-8)
    try:
        file_h = logging.FileHandler(log_file, encoding="utf-8")
        file_h.setFormatter(formatter)
        file_h.setLevel(level)
        root_logger.addHandler(file_h)
    except Exception as e:
        print(f"Warning: Cannot write to log file {log_file}: {e}", file=sys.stderr)

    # 3. RingBuffer Handler
    _ring_handler = RingBufferHandler(MAX_LOGS)
    _ring_handler.setFormatter(formatter)
    _ring_handler.setLevel(level)
    root_logger.addHandler(_ring_handler)

    return _ring_handler


def get_log_buffer() -> RingBufferHandler:
    global _ring_handler
    if _ring_handler is None:
        _ring_handler = setup_logging()
    return _ring_handler
