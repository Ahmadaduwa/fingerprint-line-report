package attendance

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Person struct {
	Enroll    int    `json:"enroll"`
	Code      string `json:"code"`
	Name      string `json:"name"`
	Level     string `json:"level"`
	ShiftCode string `json:"shift_code"`
}

type Shift struct {
	Code      string     `json:"code"`
	Name      string     `json:"name"`
	Start     *time.Time `json:"start"`
	End       *time.Time `json:"end"`
	IsDayOff  bool       `json:"is_dayoff"`
}

type Result struct {
	Person      Person     `json:"person"`
	Status      string     `json:"status"` // present, late, absent, leave, dayoff, pending
	FirstScan   *time.Time `json:"first_scan,omitempty"`
	LastScan    *time.Time `json:"last_scan,omitempty"`
	LateMinutes int        `json:"late_minutes"`
	Shift       *Shift     `json:"shift,omitempty"`
	LeaveName   string     `json:"leave_name,omitempty"`
}

type Summary struct {
	Day        time.Time `json:"day"`
	IsWorkday  bool      `json:"is_workday"`
	Holiday    string    `json:"holiday,omitempty"`
	Results    []Result  `json:"results"`
	TotalScans int       `json:"total_scans"`
}

func (s *Summary) ByStatus(status string) []Result {
	var res []Result
	for _, r := range s.Results {
		if r.Status == status {
			res = append(res, r)
		}
	}
	return res
}

func ParseHM(s string) (int, int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, 0, false
	}
	re := regexp.MustCompile(`^(\d{1,2})[:.](\d{2})`)
	m := re.FindStringSubmatch(s)
	if len(m) < 3 {
		return 0, 0, false
	}
	h, _ := strconv.Atoi(m[1])
	mi, _ := strconv.Atoi(m[2])
	if h >= 0 && h < 24 && mi >= 0 && mi < 60 {
		return h, mi, true
	}
	return 0, 0, false
}

func Compute(
	day time.Time,
	people []Person,
	scans map[int][]time.Time,
	shifts map[string]Shift,
	dailyShift map[int]string,
	leaves map[string]string,
	holidays map[string]string,
	schoolWorkdays [7]int,
	lateCutoffStr string,
	now time.Time,
) Summary {
	dateStr := day.Format("2006-01-02")
	holidayReason := holidays[dateStr]

	// Weekday index: Sunday=0 ... Saturday=6
	weekdayIdx := int(day.Weekday())
	weekdayOn := schoolWorkdays[weekdayIdx] == 1
	isWorkday := weekdayOn && holidayReason == ""

	// Late Cutoff Time (Default 07:30)
	lateH, lateM, ok := ParseHM(lateCutoffStr)
	if !ok {
		lateH, lateM = 7, 30
	}
	lateCutoff := time.Date(day.Year(), day.Month(), day.Day(), lateH, lateM, 0, 0, day.Location())

	totalScans := 0
	for _, times := range scans {
		totalScans += len(times)
	}

	summary := Summary{
		Day:        day,
		IsWorkday:  isWorkday,
		Holiday:    holidayReason,
		Results:    make([]Result, 0, len(people)),
		TotalScans: totalScans,
	}

	for _, p := range people {
		times := scans[p.Enroll]
		sort.Slice(times, func(i, j int) bool { return times[i].Before(times[j]) })

		shiftCode := dailyShift[p.Enroll]
		if shiftCode == "" {
			shiftCode = p.ShiftCode
		}
		sh, hasShift := shifts[shiftCode]
		if !hasShift {
			sh = Shift{Code: "01", Name: "กะปกติ"}
		}

		r := Result{
			Person: p,
			Shift:  &sh,
		}
		if len(times) > 0 {
			r.FirstScan = &times[0]
			if len(times) > 1 {
				r.LastScan = &times[len(times)-1]
			}
		}

		if leaveName, hasLeave := leaves[p.Code]; hasLeave {
			r.Status = "leave"
			r.LeaveName = leaveName
		} else if !isWorkday || sh.IsDayOff {
			if len(times) > 0 {
				r.Status = "present"
			} else {
				r.Status = "dayoff"
			}
		} else if len(times) > 0 {
			r.Status = "present"
			// ตรวจสอบว่าสายหรือไม่ (หลัง lateCutoff เช่น 07:30)
			if r.FirstScan.After(lateCutoff) {
				r.Status = "late"
				diff := r.FirstScan.Sub(lateCutoff)
				r.LateMinutes = int(diff.Minutes())
			}
		} else if day.Format("2006-01-02") == now.Format("2006-01-02") && now.Before(lateCutoff) {
			r.Status = "pending"
		} else {
			r.Status = "absent"
		}

		summary.Results = append(summary.Results, r)
	}

	return summary
}

// ================== THAI FORMATTING ==================

var thaiDays = []string{"วันอาทิตย์", "วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์"}
var thaiMonths = []string{"", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"}

func ThaiDate(d time.Time) string {
	dayName := thaiDays[d.Weekday()]
	monthName := thaiMonths[d.Month()]
	yearThai := d.Year() + 543
	return fmt.Sprintf("%sที่ %d %s %d", dayName, d.Day(), monthName, yearThai)
}

func BuildMessage(summary Summary, company string, now *time.Time, showPresent bool) string {
	presentList := summary.ByStatus("present")
	lateList := summary.ByStatus("late")
	absentList := summary.ByStatus("absent")
	leaveList := summary.ByStatus("leave")
	pendingList := summary.ByStatus("pending")

	dateHeader := ThaiDate(summary.Day)
	if now != nil {
		dateHeader += fmt.Sprintf(" (ข้อมูล ณ %s)", now.Format("15:04 น."))
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("📊 สรุปการมาทำงาน %s\n%s\n\n", company, dateHeader))

	if !summary.IsWorkday {
		reason := summary.Holiday
		if reason == "" {
			reason = "วันหยุดประจำสัปดาห์"
		}
		sb.WriteString(fmt.Sprintf("🎉 วันนี้เป็นวันหยุด: %s\n", reason))
		if len(presentList) > 0 {
			sb.WriteString(fmt.Sprintf("มีผู้มาทำงาน %d คน:\n", len(presentList)))
			for _, r := range presentList {
				timeStr := ""
				if r.FirstScan != nil {
					timeStr = r.FirstScan.Format(" (15:04)")
				}
				sb.WriteString(fmt.Sprintf(" • %s%s\n", r.Person.Name, timeStr))
			}
		}
		return strings.TrimSpace(sb.String())
	}

	total := len(summary.Results)
	checkedIn := len(presentList) + len(lateList)
	sb.WriteString(fmt.Sprintf("👥 ทั้งหมด: %d คน | เข้างานแล้ว: %d คน\n", total, checkedIn))
	sb.WriteString(fmt.Sprintf("✅ ปกติ: %d  |  ⏰ สาย: %d\n", len(presentList), len(lateList)))
	sb.WriteString(fmt.Sprintf("❌ ขาด: %d   |  📝 ลา: %d\n", len(absentList), len(leaveList)))
	if len(pendingList) > 0 {
		sb.WriteString(fmt.Sprintf("⏳ ยังไม่ถึงเวลา: %d คน\n", len(pendingList)))
	}
	sb.WriteString("------------------------------\n")

	// สาย
	if len(lateList) > 0 {
		sb.WriteString(fmt.Sprintf("\n⏰ มาสาย (%d คน):\n", len(lateList)))
		for _, r := range lateList {
			timeStr := ""
			if r.FirstScan != nil {
				timeStr = fmt.Sprintf(" [เข้า %s, สาย %d นาที]", r.FirstScan.Format("15:04"), r.LateMinutes)
			}
			sb.WriteString(fmt.Sprintf(" • %s%s\n", r.Person.Name, timeStr))
		}
	}

	// ลา
	if len(leaveList) > 0 {
		sb.WriteString(fmt.Sprintf("\n📝 ลางาน (%d คน):\n", len(leaveList)))
		for _, r := range leaveList {
			sb.WriteString(fmt.Sprintf(" • %s (%s)\n", r.Person.Name, r.LeaveName))
		}
	}

	// ขาด
	if len(absentList) > 0 {
		sb.WriteString(fmt.Sprintf("\n❌ ยังไม่พบการสแกน/ขาด (%d คน):\n", len(absentList)))
		for _, r := range absentList {
			sb.WriteString(fmt.Sprintf(" • %s\n", r.Person.Name))
		}
	}

	// ปกติ (ถ้าเปิด showPresent)
	if showPresent && len(presentList) > 0 {
		sb.WriteString(fmt.Sprintf("\n✅ มาตรงเวลา (%d คน):\n", len(presentList)))
		for _, r := range presentList {
			timeStr := ""
			if r.FirstScan != nil {
				timeStr = fmt.Sprintf(" (%s)", r.FirstScan.Format("15:04"))
			}
			sb.WriteString(fmt.Sprintf(" • %s%s\n", r.Person.Name, timeStr))
		}
	}

	return strings.TrimSpace(sb.String())
}
