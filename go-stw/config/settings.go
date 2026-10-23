package config

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

// Hash ของ Token ทดสอบตัวเก่า (@143smwig) เพื่อล้างค่าออกจาก settings.json อัตโนมัติโดยไม่เก็บ Token ในโค้ด
const oldTestTokenSHA256 = "e69b7598d735e81a52931531bc8295c48a34656046b68190b0b97e29a853c1bc"

type Settings struct {
	LateTime          string   `json:"late_time"`
	AutoDownloadTime  string   `json:"auto_download_time"`
	SendTimes         []string `json:"send_times"`
	LateGraceMinutes  int      `json:"late_grace_minutes"`
	DBHost            string   `json:"db_host"`
	DBPort            int      `json:"db_port"`
	DBName            string   `json:"db_name"`
	DBUser            string   `json:"db_user"`
	DBPassword        string   `json:"db_password,omitempty"`
	DBAuth            string   `json:"db_auth"` // "windows", "sql", "mock"
	CompanyName       string   `json:"company_name"`
	ShowPresent       bool     `json:"show_present"`
	SendOnDayoff      bool     `json:"send_on_dayoff"`
	MockMode          bool     `json:"mock_mode"`
	WebPort           int      `json:"web_port"`
	WebUsername       string   `json:"web_username"`
	WebPassword       string   `json:"web_password"`
	LineChannelToken  string   `json:"line_channel_access_token,omitempty"`
	LineChannelSecret string   `json:"line_channel_secret,omitempty"`
	AutoAddRecipients bool     `json:"auto_add_recipients"`
	WelcomeMessage    string   `json:"welcome_message,omitempty"`
	EnableTunnel      bool     `json:"enable_tunnel"`
}

var (
	settingsLock sync.RWMutex
	current      *Settings
	dataDir      = "data"
	settingsFile = filepath.Join("data", "settings.json")
)

func isOldTestToken(tok string) bool {
	if tok == "" {
		return false
	}
	h := sha256.Sum256([]byte(strings.TrimSpace(tok)))
	return hex.EncodeToString(h[:]) == oldTestTokenSHA256
}

func DefaultSettings() Settings {
	return Settings{
		LateTime:          "07:30",
		AutoDownloadTime:  "09:00",
		SendTimes:         []string{"09:30"},
		LateGraceMinutes:  0,
		DBHost:            "127.0.0.1",
		DBPort:            1433,
		DBName:            "Synctime",
		DBUser:            "sa",
		DBPassword:        "",
		DBAuth:            "windows",
		CompanyName:       "โรงเรียนแสงธรรมวิทยา",
		ShowPresent:       true,
		SendOnDayoff:      false,
		MockMode:          false,
		WebPort:           8090,
		WebUsername:       "admin",
		WebPassword:       "admin1234",
		LineChannelToken:  "",
		AutoAddRecipients: true,
		WelcomeMessage:    "",
		EnableTunnel:      true,
	}
}

func loadEnvMap() map[string]string {
	envMap := make(map[string]string)
	candidates := []string{".env", filepath.Join("..", ".env")}
	if exePath, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exePath)
		candidates = append(candidates,
			filepath.Join(exeDir, ".env"),
			filepath.Join(exeDir, "..", ".env"),
		)
	}
	for _, p := range candidates {
		f, err := os.Open(p)
		if err != nil {
			continue
		}
		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			parts := strings.SplitN(line, "=", 2)
			if len(parts) == 2 {
				k := strings.TrimSpace(parts[0])
				v := strings.TrimSpace(parts[1])
				if _, exists := envMap[k]; !exists && v != "" {
					envMap[k] = v
				}
			}
		}
		_ = f.Close()
	}
	return envMap
}

func applyEnvFallbacks(cfg *Settings) {
	if isOldTestToken(cfg.LineChannelToken) {
		cfg.LineChannelToken = ""
	}
	env := loadEnvMap()
	if cfg.LineChannelToken == "" {
		if tok := env["LINE_CHANNEL_ACCESS_TOKEN"]; tok != "" && !isOldTestToken(tok) {
			cfg.LineChannelToken = tok
		}
	}
	if cfg.LineChannelSecret == "" {
		if sec := env["LINE_CHANNEL_SECRET"]; sec != "" {
			cfg.LineChannelSecret = sec
		}
	}
	if cfg.DBPassword == "" {
		if pw := env["DB_PASSWORD"]; pw != "" {
			cfg.DBPassword = pw
			if cfg.DBAuth == "" || cfg.DBAuth == "windows" {
				cfg.DBAuth = "sql"
			}
		}
	}
	if v := env["DB_HOST"]; v != "" && cfg.DBHost == "" {
		cfg.DBHost = v
	}
	if v := env["DB_NAME"]; v != "" && cfg.DBName == "" {
		cfg.DBName = v
	}
	if v := env["WEB_PORT"]; v != "" && cfg.WebPort == 0 {
		if p, err := strconv.Atoi(v); err == nil && p > 0 {
			cfg.WebPort = p
		}
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
	applyEnvFallbacks(&defaults)

	bytes, err := os.ReadFile(settingsFile)
	if err != nil {
		current = &defaults
		_ = saveToFile(defaults)
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
		cfg.DBName = "Synctime"
	}
	if cfg.CompanyName == "" {
		cfg.CompanyName = "โรงเรียนแสงธรรมวิทยา"
	}
	if cfg.DBHost == "" {
		cfg.DBHost = "127.0.0.1"
	}
	if cfg.DBAuth == "" {
		if cfg.DBPassword != "" {
			cfg.DBAuth = "sql"
		} else {
			cfg.DBAuth = "windows"
		}
	}
	if cfg.WebPort == 0 {
		cfg.WebPort = 8090
	}
	if cfg.WebUsername == "" {
		cfg.WebUsername = "admin"
	}
	if cfg.WebPassword == "" || cfg.WebPassword == "change_this_password" {
		cfg.WebPassword = "admin1234"
	}
	applyEnvFallbacks(&cfg)
	_ = saveToFile(cfg)

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
		newCfg.DBName = "Synctime"
	}
	if newCfg.CompanyName == "" {
		newCfg.CompanyName = "โรงเรียนแสงธรรมวิทยา"
	}
	if newCfg.WebPort == 0 {
		newCfg.WebPort = 8090
	}
	if newCfg.WebUsername == "" {
		newCfg.WebUsername = "admin"
	}
	if newCfg.WebPassword == "" {
		newCfg.WebPassword = "admin1234"
	}
	applyEnvFallbacks(&newCfg)

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
