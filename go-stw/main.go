package main

import (
	"flag"
	"fmt"
	"strings"
	"sync"
	"time"


	"stw_teacher_check/attendance"
	"stw_teacher_check/config"
	"stw_teacher_check/db"
	"stw_teacher_check/line"
	"stw_teacher_check/logger"
	"stw_teacher_check/storage"
	"stw_teacher_check/web"
)

var (
	currentDB   db.Database
	dbMu        sync.RWMutex
	webInstance *web.WebServer
)

func getDB() db.Database {
	dbMu.RLock()
	defer dbMu.RUnlock()
	return currentDB
}

func initDB(mock bool) error {
	dbMu.Lock()
	defer dbMu.Unlock()

	cfg := config.LoadSettings()
	if mock {
		cfg.MockMode = true
	}

	if currentDB != nil {
		_ = currentDB.Close()
	}

	d, err := db.Connect(cfg)
	if err != nil {
		logger.Error("MAIN", err, "เชื่อมต่อฐานข้อมูลไม่สำเร็จ กำลังสลับเป็น Mock DB ชั่วคราว...")
		currentDB = db.NewMockDB(cfg.CompanyName)
		return err
	}
	currentDB = d
	return nil
}

func makeReport(d db.Database, day time.Time, now time.Time) (attendance.Summary, string, error) {
	cfg := config.LoadSettings()

	people, err := d.GetPeople()
	if err != nil {
		return attendance.Summary{}, "", err
	}
	scans, _ := d.GetScans(day)
	shifts, _ := d.GetShifts()
	dailyShift, _ := d.GetDailyShift(day)
	leaves, _ := d.GetLeaves(day)
	holidays, _ := d.GetHolidays()
	schoolName, workdays, _ := d.GetSchool()
	if schoolName != "" {
		cfg.CompanyName = schoolName
	}

	summary := attendance.Compute(
		day, people, scans, shifts, dailyShift, leaves, holidays, workdays,
		cfg.LateTime, now,
	)

	if summary.IsWorkday && summary.TotalScans == 0 && len(summary.ByStatus("absent")) > 0 {
		msg := fmt.Sprintf("⚠️ สรุปการมาทำงาน %s\n%s\n\nยังไม่มีข้อมูลการสแกนของวันนี้ในระบบเลย\nตรวจสอบว่าโปรแกรม HIP TIME ดึงข้อมูลจากเครื่องสแกนแล้วหรือยัง (รอบ %s น.)", cfg.CompanyName, attendance.ThaiDate(day), cfg.AutoDownloadTime)
		return summary, msg, nil
	}

	msg := attendance.BuildMessage(summary, cfg.CompanyName, &now, cfg.ShowPresent)
	return summary, msg, nil
}

func runOnce(day time.Time, dryRun bool) error {
	now := time.Now()
	d := getDB()
	if d == nil {
		return fmt.Errorf("ฐานข้อมูลยังไม่พร้อมใช้งาน")
	}

	summary, text, err := makeReport(d, day, now)
	if err != nil {
		logger.Error("REPORT", err, "สร้างรายงานสรุปไม่สำเร็จ")
		return err
	}

	cfg := config.LoadSettings()
	if !summary.IsWorkday && !cfg.SendOnDayoff && len(summary.ByStatus("present")) == 0 {
		logger.Info("REPORT", "%s เป็นวันหยุด ไม่ส่งรายงาน", day.Format("2006-01-02"))
		return nil
	}

	if dryRun {
		fmt.Println("--- DRY RUN PREVIEW ---")
		fmt.Println(text)
		return nil
	}

	targets := storage.GetActiveTargetIDs()
	if len(targets) == 0 {
		logger.Warning("REPORT", "ไม่มีรายชื่อผู้รับรายงานที่เปิดใช้งาน (ข้ามการส่ง)")
		return fmt.Errorf("ไม่มีรายชื่อผู้รับรายงาน")
	}

	lineClient := line.NewClient(cfg.LineChannelToken)
	err = lineClient.SendText(targets, text)
	if err != nil {
		logger.Error("REPORT", err, "ส่งรายงานเข้า LINE ไม่สำเร็จ")
		if webInstance != nil {
			webInstance.SetLastRun(now.Format("2006-01-02 15:04:05"), fmt.Sprintf("ส่งไม่สำเร็จ: %s", err))
		}
		return err
	}

	logger.Info("REPORT", "ส่งรายงานประจำวันไปยัง %d ผู้รับ สำเร็จเรียบร้อย", len(targets))
	if webInstance != nil {
		webInstance.SetLastRun(now.Format("2006-01-02 15:04:05"), "ส่งสำเร็จตามรอบเวลา")
	}
	return nil
}

func nextRunTime(times []string, now time.Time) time.Time {
	var candidates []time.Time
	for _, tStr := range times {
		h, m, ok := attendance.ParseHM(tStr)
		if !ok {
			continue
		}
		// วันนี้
		tToday := time.Date(now.Year(), now.Month(), now.Day(), h, m, 0, 0, now.Location())
		if tToday.After(now) {
			candidates = append(candidates, tToday)
		}
		// พรุ่งนี้
		tTomorrow := tToday.AddDate(0, 0, 1)
		candidates = append(candidates, tTomorrow)
	}

	if len(candidates) == 0 {
		// Default 09:30 พรุ่งนี้
		return time.Date(now.Year(), now.Month(), now.Day()+1, 9, 30, 0, 0, now.Location())
	}

	minT := candidates[0]
	for _, c := range candidates[1:] {
		if c.Before(minT) {
			minT = c
		}
	}
	return minT
}

func startScheduler() {
	for {
		cfg := config.LoadSettings()
		now := time.Now()
		nextT := nextRunTime(cfg.SendTimes, now)

		logger.Info("SCHEDULER", "รอบส่งรายงานถัดไป: %s (ส่งเวลา: %s)", nextT.Format("2006-01-02 15:04:05"), strings.Join(cfg.SendTimes, ", "))

		sleepDuration := time.Until(nextT)
		for sleepDuration > 0 {
			step := 20 * time.Second
			if sleepDuration < step {
				step = sleepDuration
			}
			time.Sleep(step)
			sleepDuration = time.Until(nextT)
		}

		logger.Info("SCHEDULER", "⏰ ถึงเวลาส่งรายงานประจำวันแล้ว (%s)", time.Now().Format("15:04:05"))
		_ = runOnce(time.Now(), false)
		time.Sleep(2 * time.Second)
	}
}

func main() {
	logger.InitLogger()
	logger.Info("MAIN", "==================================================")
	logger.Info("MAIN", "   เริ่มต้นระบบ STW_TeacherCheck (Go Edition)     ")
	logger.Info("MAIN", "==================================================")

	nowFlag := flag.Bool("now", false, "ส่งสรุปของวันนี้ทันที")
	mockFlag := flag.Bool("mock", false, "รันด้วยฐานข้อมูลจำลอง (เสมือนจริง)")
	dryRunFlag := flag.Bool("dry-run", false, "แสดงข้อความตัวอย่าง ไม่ส่ง LINE")
	dateFlag := flag.String("date", "", "ระบุวันที่สรุป (YYYY-MM-DD)")
	checkFlag := flag.Bool("check", false, "ทดสอบเชื่อมต่อฐานข้อมูล")
	flag.Parse()

	_ = initDB(*mockFlag)

	if *checkFlag {
		d := getDB()
		res := d.TestConnection()
		fmt.Printf("ผลการตรวจสอบฐานข้อมูล:\n%+v\n", res)
		return
	}

	if *nowFlag || *dryRunFlag || *dateFlag != "" {
		targetDay := time.Now()
		if *dateFlag != "" {
			parsed, err := time.Parse("2006-01-02", *dateFlag)
			if err == nil {
				targetDay = parsed
			}
		}
		_ = runOnce(targetDay, *dryRunFlag)
		return
	}

	// สร้าง Web Server
	webInstance = web.NewWebServer(getDB, func() error {
		return runOnce(time.Now(), false)
	})

	cfg := config.LoadSettings()
	port := cfg.WebPort
	if port == 0 {
		port = 8090
	}

	// เริ่ม Background Scheduler
	go startScheduler()

	// เริ่ม Web Server (Blocking)
	webInstance.Start(port)
}
