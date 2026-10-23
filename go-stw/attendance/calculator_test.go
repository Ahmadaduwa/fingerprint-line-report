package attendance

import (
	"strings"
	"testing"
	"time"
)

func TestParseHM(t *testing.T) {
	tests := []struct {
		input string
		expH  int
		expM  int
		expOk bool
	}{
		{"07:30", 7, 30, true},
		{"7:30", 7, 30, true},
		{"07.30", 7, 30, true},
		{"09:00", 9, 0, true},
		{"23:59", 23, 59, true},
		{"24:00", 0, 0, false},
		{"invalid", 0, 0, false},
		{"", 0, 0, false},
	}

	for _, tt := range tests {
		h, m, ok := ParseHM(tt.input)
		if ok != tt.expOk || (ok && (h != tt.expH || m != tt.expM)) {
			t.Errorf("ParseHM(%q) = (%d, %d, %v), expected (%d, %d, %v)", tt.input, h, m, ok, tt.expH, tt.expM, tt.expOk)
		}
	}
}

func TestThaiDate(t *testing.T) {
	d := time.Date(2026, 10, 23, 8, 0, 0, 0, time.Local)
	s := ThaiDate(d)
	// 2026 + 543 = 2569
	if !strings.Contains(s, "2569") || !strings.Contains(s, "ตุลาคม") || !strings.Contains(s, "วันศุกร์") {
		t.Errorf("ThaiDate(%v) = %q, missing expected Thai date parts", d, s)
	}
}

func TestComputeAndBuildMessage(t *testing.T) {
	day := time.Date(2026, 10, 23, 0, 0, 0, 0, time.Local)
	now := time.Date(2026, 10, 23, 10, 0, 0, 0, time.Local)

	people := []Person{
		{Enroll: 1, Code: "001", Name: "นายสมชาย", ShiftCode: "01"},
		{Enroll: 2, Code: "002", Name: "นางสาวสมศรี", ShiftCode: "01"},
		{Enroll: 3, Code: "003", Name: "นายมานะ", ShiftCode: "01"},
		{Enroll: 4, Code: "004", Name: "นายชูใจ", ShiftCode: "01"},
	}

	scans := map[int][]time.Time{
		1: {time.Date(2026, 10, 23, 7, 15, 0, 0, time.Local)}, // On-time (before 07:30)
		2: {time.Date(2026, 10, 23, 7, 45, 0, 0, time.Local)}, // Late (after 07:30 by 15 mins)
	}

	shifts := map[string]Shift{
		"01": {Code: "01", Name: "กะปกติ"},
	}

	leaves := map[string]string{
		"003": "ลาป่วย",
	}

	holidays := map[string]string{}
	schoolWorkdays := [7]int{0, 1, 1, 1, 1, 1, 0} // Mon-Fri

	summary := Compute(
		day,
		people,
		scans,
		shifts,
		map[int]string{},
		leaves,
		holidays,
		schoolWorkdays,
		"07:30",
		now,
	)

	if !summary.IsWorkday {
		t.Fatalf("expected Friday to be a workday")
	}

	pList := summary.ByStatus("present")
	if len(pList) != 1 || pList[0].Person.Enroll != 1 {
		t.Errorf("expected 1 present (enroll 1), got %v", pList)
	}

	lList := summary.ByStatus("late")
	if len(lList) != 1 || lList[0].Person.Enroll != 2 || lList[0].LateMinutes != 15 {
		t.Errorf("expected 1 late (enroll 2) with 15 late mins, got %v", lList)
	}

	leaveList := summary.ByStatus("leave")
	if len(leaveList) != 1 || leaveList[0].Person.Enroll != 3 || leaveList[0].LeaveName != "ลาป่วย" {
		t.Errorf("expected 1 leave (enroll 3), got %v", leaveList)
	}

	abList := summary.ByStatus("absent")
	if len(abList) != 1 || abList[0].Person.Enroll != 4 {
		t.Errorf("expected 1 absent (enroll 4), got %v", abList)
	}

	msg := BuildMessage(summary, "STW_TeacherCheck", &now, true)
	if !strings.Contains(msg, "สรุปการมาทำงาน STW_TeacherCheck") {
		t.Errorf("msg header missing, got: %s", msg)
	}
	if !strings.Contains(msg, "⏰ มาสาย (1 คน):") || !strings.Contains(msg, "สาย 15 นาที") {
		t.Errorf("msg late section incorrect, got: %s", msg)
	}
	if !strings.Contains(msg, "📝 ลางาน (1 คน):") || !strings.Contains(msg, "ลาป่วย") {
		t.Errorf("msg leave section incorrect, got: %s", msg)
	}
}
