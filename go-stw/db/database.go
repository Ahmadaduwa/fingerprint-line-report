package db

import (
	"database/sql"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	_ "github.com/denisenkom/go-mssqldb"

	"stw_teacher_check/attendance"
	"stw_teacher_check/config"
	"stw_teacher_check/logger"
)

type Database interface {
	TestConnection() map[string]interface{}
	GetSchool() (string, [7]int, error)
	GetPeople() ([]attendance.Person, error)
	GetShifts() (map[string]attendance.Shift, error)
	GetDailyShift(day time.Time) (map[int]string, error)
	GetLeaves(day time.Time) (map[string]string, error)
	GetHolidays() (map[string]string, error)
	GetScans(day time.Time) (map[int][]time.Time, error)
	Close() error
}

type SQLServerDB struct {
	db       *sql.DB
	host     string
	database string
}

func Connect(cfg config.Settings) (Database, error) {
	if cfg.MockMode || strings.EqualFold(cfg.DBAuth, "mock") || strings.EqualFold(cfg.DBHost, "mock") {
		logger.Info("DB", "ใช้ฐานข้อมูลจำลอง (Mock DB)")
		return NewMockDB(cfg.CompanyName), nil
	}

	connStr := buildConnString(cfg)
	db, err := sql.Open("sqlserver", connStr)
	if err != nil {
		logger.Error("DB", err, "เปิดการเชื่อมต่อ SQL Server ไม่สำเร็จ: %s", cfg.DBHost)
		return nil, err
	}

	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(3)
	db.SetConnMaxLifetime(time.Hour)

	return &SQLServerDB{
		db:       db,
		host:     cfg.DBHost,
		database: cfg.DBName,
	}, nil
}

func buildConnString(cfg config.Settings) string {
	server := strings.TrimSpace(cfg.DBHost)
	if server == "" {
		server = `.\SQLEXPRESS`
	}
	// ปรับ backslash ให้ถูกต้อง ไม่ให้ซ้ำซ้อน
	server = regexp.MustCompile(`\\+`).ReplaceAllString(server, `\`)

	dbName := strings.TrimSpace(cfg.DBName)
	if dbName == "" {
		dbName = "hiptime"
	}

	var parts []string
	parts = append(parts, fmt.Sprintf("server=%s", server))

	// ถ้าไม่มี instance และระบุ port พิเศษ
	if cfg.DBPort > 0 && cfg.DBPort != 1433 && !strings.Contains(server, `\`) {
		parts = append(parts, fmt.Sprintf("port=%d", cfg.DBPort))
	}
	parts = append(parts, fmt.Sprintf("database=%s", dbName))
	parts = append(parts, "connection timeout=10")
	parts = append(parts, "dial timeout=10")

	// Authentication mode
	if strings.EqualFold(cfg.DBAuth, "windows") || cfg.DBPassword == "" {
		parts = append(parts, "trusted_connection=yes")
	} else {
		user := strings.TrimSpace(cfg.DBUser)
		if user == "" {
			user = "sa"
		}
		parts = append(parts, fmt.Sprintf("user id=%s", user))
		parts = append(parts, fmt.Sprintf("password=%s", cfg.DBPassword))
	}

	return strings.Join(parts, ";") + ";"
}

func (s *SQLServerDB) Close() error {
	if s.db != nil {
		return s.db.Close()
	}
	return nil
}

func (s *SQLServerDB) TestConnection() map[string]interface{} {
	if err := s.db.Ping(); err != nil {
		errStr := err.Error()
		advice := "ตรวจสอบชื่อ Server/Instance และเปิดพอร์ต 1433 ใน SQL Server Configuration Manager"
		if strings.Contains(errStr, "Sql Server Browser") {
			advice = "บริการ 'SQL Server Browser' ปิดอยู่ กรุณาคลิกขวาที่ไฟล์ fix_sql_connection.bat แล้วเลือก 'Run as administrator' หรือเปิด services.msc สั่ง Start บริการ SQL Server Browser"
		} else if strings.Contains(errStr, "Login failed") {
			advice = "รหัสผ่าน SQL Server ('sa') ไม่ถูกต้อง หรือ Windows User ไม่มีสิทธิ์ sysadmin"
		} else if strings.Contains(errStr, "Cannot open database") {
			advice = fmt.Sprintf("ไม่พบฐานข้อมูล '%s' (ตรวจสอบว่าชื่อ hiptime ตรงกับในเครื่องหรือไม่)", s.database)
		}

		logger.Error("DB", err, "ทดสอบเชื่อมต่อล้มเหลว: %s", advice)
		return map[string]interface{}{
			"ok":       false,
			"error":    errStr,
			"advice":   advice,
			"host":     s.host,
			"database": s.database,
		}
	}

	var ver string
	var dbName string
	_ = s.db.QueryRow("SELECT @@VERSION, DB_NAME()").Scan(&ver, &dbName)
	if lines := strings.Split(ver, "\n"); len(lines) > 0 {
		ver = lines[0]
	}

	people, _ := s.GetPeople()
	schoolName, _, _ := s.GetSchool()

	return map[string]interface{}{
		"ok":             true,
		"message":        "เชื่อมต่อฐานข้อมูล SQL Server สำเร็จเรียบร้อย",
		"server_version": ver,
		"database":       dbName,
		"school_name":    schoolName,
		"employee_count": len(people),
	}
}

func (s *SQLServerDB) GetSchool() (string, [7]int, error) {
	var name sql.NullString
	var mon, tue, wed, thu, fri, sat, sun sql.NullInt64

	row := s.db.QueryRow(`
		SELECT TOP 1 schoolname, monwork, tuework, wedwork, thuwork, friwork, satwork, sunwork 
		FROM School 
		WHERE active = 1 OR active IS NULL 
		ORDER BY id
	`)
	err := row.Scan(&name, &mon, &tue, &wed, &thu, &fri, &sat, &sun)
	if err != nil && err != sql.ErrNoRows {
		return "", [7]int{0, 1, 1, 1, 1, 1, 0}, err
	}

	// Index 0: Sunday, 1: Monday, ... 6: Saturday
	workdays := [7]int{
		int(sun.Int64), int(mon.Int64), int(tue.Int64),
		int(wed.Int64), int(thu.Int64), int(fri.Int64), int(sat.Int64),
	}
	if !mon.Valid {
		workdays = [7]int{0, 1, 1, 1, 1, 1, 0}
	}

	return strings.TrimSpace(name.String), workdays, nil
}

func (s *SQLServerDB) GetPeople() ([]attendance.Person, error) {
	rows, err := s.db.Query(`
		SELECT enrollnumber, studentcode, studentname, levelcode, shiftcode 
		FROM Student 
		WHERE (active = 1 OR active IS NULL) AND enrollnumber IS NOT NULL AND enrollnumber > 0
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var people []attendance.Person
	for rows.Next() {
		var enroll int
		var code, name, level, shift sql.NullString
		if err := rows.Scan(&enroll, &code, &name, &level, &shift); err != nil {
			continue
		}
		pName := strings.TrimSpace(name.String)
		if pName == "" {
			pName = strconv.Itoa(enroll)
		}
		people = append(people, attendance.Person{
			Enroll:    enroll,
			Code:      strings.TrimSpace(code.String),
			Name:      pName,
			Level:     strings.TrimSpace(level.String),
			ShiftCode: strings.TrimSpace(shift.String),
		})
	}
	return people, nil
}

func (s *SQLServerDB) GetShifts() (map[string]attendance.Shift, error) {
	rows, err := s.db.Query(`SELECT shiftcode, shiftname, starttime, endtime FROM Shift`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	shifts := make(map[string]attendance.Shift)
	for rows.Next() {
		var code, name, start, end sql.NullString
		if err := rows.Scan(&code, &name, &start, &end); err != nil {
			continue
		}
		c := strings.TrimSpace(code.String)
		sh := attendance.Shift{
			Code: c,
			Name: strings.TrimSpace(name.String),
		}
		if sh.Name == "" {
			sh.Name = c
		}
		if start.Valid && end.Valid {
			if start.String == "00:00" && end.String == "00:00" {
				sh.IsDayOff = true
			}
		}
		shifts[c] = sh
	}
	return shifts, nil
}

func (s *SQLServerDB) GetDailyShift(day time.Time) (map[int]string, error) {
	dateStr := day.Format("2006-01-02")
	rows, err := s.db.Query(`SELECT enrollnumber, tdate, shiftcode FROM StudentShift`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	m := make(map[int]string)
	for rows.Next() {
		var enroll int
		var tdate, shift sql.NullString
		if err := rows.Scan(&enroll, &tdate, &shift); err != nil {
			continue
		}
		if enroll > 0 && strings.HasPrefix(strings.TrimSpace(tdate.String), dateStr) {
			m[enroll] = strings.TrimSpace(shift.String)
		}
	}
	return m, nil
}

func (s *SQLServerDB) GetLeaves(day time.Time) (map[string]string, error) {
	dateStr := day.Format("2006-01-02")
	rows, err := s.db.Query(`
		SELECT tl.studentcode, l.leavename, tl.leavedate 
		FROM TranLeave tl 
		LEFT JOIN Leave l ON tl.leavecode = l.leavecode
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	m := make(map[string]string)
	for rows.Next() {
		var code, name, ldate sql.NullString
		if err := rows.Scan(&code, &name, &ldate); err != nil {
			continue
		}
		if strings.HasPrefix(strings.TrimSpace(ldate.String), dateStr) {
			lName := strings.TrimSpace(name.String)
			if lName == "" {
				lName = "ลา"
			}
			m[strings.TrimSpace(code.String)] = lName
		}
	}
	return m, nil
}

func (s *SQLServerDB) GetHolidays() (map[string]string, error) {
	rows, err := s.db.Query(`SELECT holdate, holreason FROM Holiday`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	m := make(map[string]string)
	for rows.Next() {
		var hdate, reason sql.NullString
		if err := rows.Scan(&hdate, &reason); err != nil {
			continue
		}
		dStr := parseDateStr(hdate.String)
		if dStr != "" {
			r := strings.TrimSpace(reason.String)
			if r == "" {
				r = "วันหยุด"
			}
			m[dStr] = r
		}
	}
	return m, nil
}

func (s *SQLServerDB) GetScans(day time.Time) (map[int][]time.Time, error) {
	cutoff := day.AddDate(0, 0, -1).Format("2006-01-02")
	rows, err := s.db.Query(`
		SELECT enrollnumber, datetimescan 
		FROM Transcantime 
		WHERE adddate >= ? OR adddate IS NULL
	`, cutoff)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	dayStr := day.Format("2006-01-02")
	m := make(map[int][]time.Time)

	for rows.Next() {
		var enroll int
		var scanStr sql.NullString
		if err := rows.Scan(&enroll, &scanStr); err != nil {
			continue
		}
		if enroll <= 0 || !scanStr.Valid {
			continue
		}
		t := parseDateTime(scanStr.String)
		if !t.IsZero() && t.Format("2006-01-02") == dayStr {
			m[enroll] = append(m[enroll], t)
		}
	}
	return m, nil
}

// ================== DATE/TIME PARSING ==================

var dtFormats = []string{
	"2006-01-02 15:04:05", "2006-01-02 15:04", "2006-01-02T15:04:05",
	"2006/01/02 15:04:05", "2006/01/02 15:04",
	"02/01/2006 15:04:05", "02/01/2006 15:04",
	"02-01-2006 15:04:05", "02-01-2006 15:04",
	"2006-01-02", "2006/01/02", "02/01/2006", "02-01-2006",
}

func parseDateTime(s string) time.Time {
	s = strings.TrimSpace(s)
	// ตัด ms
	re := regexp.MustCompile(`\.\d+$`)
	s = re.ReplaceAllString(s, "")

	for _, fmtStr := range dtFormats {
		t, err := time.ParseInLocation(fmtStr, s, time.Local)
		if err == nil {
			if t.Year() > 2400 { // พ.ศ.
				t = t.AddDate(-543, 0, 0)
			}
			return t
		}
	}
	return time.Time{}
}

func parseDateStr(s string) string {
	t := parseDateTime(s)
	if t.IsZero() {
		return ""
	}
	return t.Format("2006-01-02")
}
