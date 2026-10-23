package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

type Settings struct {
	LateTime           string   `json:"late_time"`
	AutoDownloadTime   string   `json:"auto_download_time"`
	SendTimes          []string `json:"send_times"`
	LateGraceMinutes   int      `json:"late_grace_minutes"`
	DBHost             string   `json:"db_host"`
	DBPort             int      `json:"db_port"`
	DBName             string   `json:"db_name"`
	DBUser             string   `json:"db_user"`
	DBPassword         string   `json:"db_password,omitempty"`
	DBAuth             string   `json:"db_auth"` // "windows", "sql", "mock"
	CompanyName        string   `json:"company_name"`
	ShowPresent        bool     `json:"show_present"`
	SendOnDayoff       bool     `json:"send_on_dayoff"`
	MockMode           bool     `json:"mock_mode"`
	WebPort            int      `json:"web_port"`
	WebUsername        string   `json:"web_username"`
	WebPassword        string   `json:"web_password"`
	LineChannelToken   string   `json:"line_channel_access_token,omitempty"`
	LineChannelSecret  string   `json:"line_channel_secret,omitempty"`
	AutoAddRecipients  bool     `json:"auto_add_recipients"`
	WelcomeMessage     string   `json:"welcome_message,omitempty"`
}

var (
	settingsLock sync.RWMutex
	current      *Settings
	dataDir      = "data"
	settingsFile = filepath.Join("data", "settings.json")
)

func DefaultSettings() Settings {
	return Settings{
		LateTime:          "07:30",
		AutoDownloadTime:  "09:00",
		SendTimes:         []string{"09:30"},
		LateGraceMinutes:  0,
		DBHost:            `.\\SQLEXPRESS`,
		DBPort:            1433,
		DBName:            "hiptime",
		DBUser:            "sa",
		DBPassword:        "",
		DBAuth:            "windows",
		CompanyName:       "STW_TeacherCheck",
		ShowPresent:       true,
		SendOnDayoff:      false,
		MockMode:          false,
		WebPort:           8090,
		WebUsername:       "admin",
		WebPassword:       "admin1234",
		AutoAddRecipients: true,
		WelcomeMessage:    "",
	}
}

func LoadSettings() Settings {
	settingsLock.Lock()
	defer settingsLock.Unlock()

	if current != nil {
		return *current
	}

	_ = os.MkdirAll(dataDir, 0755)
	defaults := DefaultSettings()

	bytes, err := os.ReadFile(settingsFile)
	if err != nil {
		current = &defaults
		saveToFile(defaults)
		return defaults
	}

	cfg := defaults
	if err := json.Unmarshal(bytes, &cfg); err != nil {
		current = &defaults
		return defaults
	}

	if len(cfg.SendTimes) == 0 {
		cfg.SendTimes = []string{"09:30"}
	}
	if cfg.LateTime == "" {
		cfg.LateTime = "07:30"
	}
	if cfg.DBName == "" {
		cfg.DBName = "hiptime"
	}
	if cfg.CompanyName == "" {
		cfg.CompanyName = "STW_TeacherCheck"
	}

	current = &cfg
	return *current
}

func SaveSettings(newCfg Settings) (Settings, error) {
	settingsLock.Lock()
	defer settingsLock.Unlock()

	if len(newCfg.SendTimes) == 0 {
		newCfg.SendTimes = []string{"09:30"}
	}
	if newCfg.LateTime == "" {
		newCfg.LateTime = "07:30"
	}
	if newCfg.DBName == "" {
		newCfg.DBName = "hiptime"
	}
	if newCfg.CompanyName == "" {
		newCfg.CompanyName = "STW_TeacherCheck"
	}
	if newCfg.WebPort == 0 {
		newCfg.WebPort = 8090
	}

	current = &newCfg
	err := saveToFile(newCfg)
	return newCfg, err
}

func saveToFile(cfg Settings) error {
	_ = os.MkdirAll(dataDir, 0755)
	bytes, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	tmpFile := settingsFile + ".tmp"
	if err := os.WriteFile(tmpFile, bytes, 0644); err != nil {
		return err
	}
	return os.Rename(tmpFile, settingsFile)
}
