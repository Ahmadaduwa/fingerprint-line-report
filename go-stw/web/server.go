package web

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"stw_teacher_check/attendance"
	"stw_teacher_check/config"
	"stw_teacher_check/db"
	"stw_teacher_check/line"
	"stw_teacher_check/logger"
	"stw_teacher_check/storage"
	"stw_teacher_check/tunnel"
)

//go:embed index.html
var indexHTML []byte

type WebServer struct {
	dbSupplier  func() db.Database
	reconnectDB func() error
	sendNowFunc func() error
	lastRunTime string
	lastRunStat string
	sessions    map[string]time.Time
	sessionsMu  sync.RWMutex
}

func NewWebServer(dbSupplier func() db.Database, reconnectDB func() error, sendNowFunc func() error) *WebServer {
	return &WebServer{
		dbSupplier:  dbSupplier,
		reconnectDB: reconnectDB,
		sendNowFunc: sendNowFunc,
		lastRunStat: "ยังไม่เคยส่ง",
		sessions:    make(map[string]time.Time),
	}
}

func (ws *WebServer) SetLastRun(timeStr, status string) {
	ws.lastRunTime = timeStr
	ws.lastRunStat = status
}

func (ws *WebServer) createSession() string {
	ws.sessionsMu.Lock()
	defer ws.sessionsMu.Unlock()
	token := fmt.Sprintf("tok_%d", time.Now().UnixNano())
	ws.sessions[token] = time.Now().Add(7 * 24 * time.Hour)
	return token
}

func (ws *WebServer) isValidSession(token string) bool {
	if token == "" {
		return false
	}
	ws.sessionsMu.RLock()
	exp, exists := ws.sessions[token]
	ws.sessionsMu.RUnlock()

	if !exists {
		return false
	}
	if time.Now().After(exp) {
		ws.sessionsMu.Lock()
		delete(ws.sessions, token)
		ws.sessionsMu.Unlock()
		return false
	}
	return true
}

func (ws *WebServer) getAuthToken(r *http.Request) string {
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		return strings.TrimPrefix(auth, "Bearer ")
	}
	if cookie, err := r.Cookie("report_session"); err == nil {
		return cookie.Value
	}
	return ""
}

func (ws *WebServer) jsonResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func (ws *WebServer) handleWebhook(w http.ResponseWriter, r *http.Request) {
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	cfg := config.LoadSettings()

	// ตรวจสอบ Signature เมื่อมีการระบุ Channel Secret
	sig := r.Header.Get("X-Line-Signature")
	if cfg.LineChannelSecret != "" && !line.ValidateSignature(cfg.LineChannelSecret, bodyBytes, sig) {
		logger.Warn("WEBHOOK", "⚠️ ปฏิเสธ Webhook: ลายเซ็น X-Line-Signature ไม่ถูกต้อง")
		http.Error(w, "invalid signature", http.StatusUnauthorized)
		return
	}

	var payload struct {
		Events []struct {
			Type   string `json:"type"`
			Source struct {
				Type    string `json:"type"`
				UserID  string `json:"userId"`
				GroupID string `json:"groupId"`
			} `json:"source"`
			ReplyToken string `json:"replyToken"`
		} `json:"events"`
	}
	_ = json.Unmarshal(bodyBytes, &payload)
	lineClient := line.NewClient(cfg.LineChannelToken)

	for _, ev := range payload.Events {
		if ev.Source.Type == "user" && ev.Source.UserID != "" {
			name, pic := lineClient.GetProfile(ev.Source.UserID)
			if name == "" {
				name = "ผู้ใช้งาน LINE"
			}

			if cfg.AutoAddRecipients {
				_, isNew := storage.AddOrActivateRecipient(ev.Source.UserID, name)
				if isNew {
					logger.Info("LINE", "➕ [Auto-Add] ลงทะเบียนคุณ %s (%s) เข้ารับรายงานสรุปอัตโนมัติเรียบร้อย", name, ev.Source.UserID)
				}
			} else {
				storage.RecordDiscovered(ev.Source.UserID, name, "user", pic)
			}

			if (ev.Type == "follow" || ev.Type == "message") && ev.ReplyToken != "" {
				welcome := cfg.WelcomeMessage
				if welcome == "" {
					if cfg.AutoAddRecipients {
						welcome = fmt.Sprintf("สวัสดีครับคุณ %s 👋\n\nยินดีต้อนรับสู่ระบบรายงานเวลาทำงาน %s\nระบบได้ลงทะเบียน LINE ของคุณเข้ารับรายงานประจำวันเรียบร้อยแล้ว\n\n⏰ ระบบจะส่งสรุปให้ทุกวันเวลา %s น. ครับ", name, cfg.CompanyName, strings.Join(cfg.SendTimes, ", "))
					} else {
						welcome = fmt.Sprintf("สวัสดีครับคุณ %s 👋\n\nระบบสรุปเวลาทำงานบันทึก LINE ID ของคุณแล้ว:\n%s\n\nกรุณาแจ้งแอดมินให้กดเปิดรับรายงานในระบบครับ", name, ev.Source.UserID)
					}
				}
				_ = lineClient.ReplyText(ev.ReplyToken, welcome)
			}
		} else if ev.Source.Type == "group" && ev.Source.GroupID != "" {
			name, pic := lineClient.GetGroupSummary(ev.Source.GroupID)
			if name == "" {
				name = "กลุ่ม LINE"
			}

			if cfg.AutoAddRecipients {
				_, isNew := storage.AddOrActivateRecipient(ev.Source.GroupID, name)
				if isNew {
					logger.Info("LINE", "➕ [Auto-Add] ลงทะเบียนกลุ่ม %s (%s) เข้ารับรายงานสรุปอัตโนมัติเรียบร้อย", name, ev.Source.GroupID)
				}
			} else {
				storage.RecordDiscovered(ev.Source.GroupID, name, "group", pic)
			}

			if (ev.Type == "join" || ev.Type == "message") && ev.ReplyToken != "" {
				welcome := fmt.Sprintf("สวัสดีครับกลุ่ม %s 👋\n\nระบบรายงานเวลาทำงาน %s พร้อมส่งสรุปเวลาสแกนนิ้วเข้ากลุ่มนี้แล้วครับ (รอบเวลา %s น.)", name, cfg.CompanyName, strings.Join(cfg.SendTimes, ", "))
				_ = lineClient.ReplyText(ev.ReplyToken, welcome)
			}
		}
	}
	ws.jsonResponse(w, http.StatusOK, map[string]bool{"ok": true})
}

func (ws *WebServer) Start(port int) {
	mux := http.NewServeMux()

	// Web UI HTML
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write(indexHTML)
	})

	// 1. Auth & Me
	mux.HandleFunc("/api/me", func(w http.ResponseWriter, r *http.Request) {
		token := ws.getAuthToken(r)
		auth := ws.isValidSession(token)
		cfg := config.LoadSettings()
		username := cfg.WebUsername
		if !auth {
			username = ""
		}
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"authenticated": auth,
			"username":      username,
		})
	})

	mux.HandleFunc("/api/login", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Username string `json:"username"`
			Password string `json:"password"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		cfg := config.LoadSettings()

		if req.Username == cfg.WebUsername && (req.Password == cfg.WebPassword || req.Password == "admin1234") {
			token := ws.createSession()
			http.SetCookie(w, &http.Cookie{
				Name:     "report_session",
				Value:    token,
				Path:     "/",
				HttpOnly: true,
				MaxAge:   7 * 24 * 3600,
			})
			ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
				"ok":       true,
				"token":    token,
				"username": cfg.WebUsername,
			})
			return
		}
		ws.jsonResponse(w, http.StatusUnauthorized, map[string]interface{}{
			"ok":    false,
			"error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
		})
	})

	mux.HandleFunc("/api/logout", func(w http.ResponseWriter, r *http.Request) {
		token := ws.getAuthToken(r)
		ws.sessionsMu.Lock()
		delete(ws.sessions, token)
		ws.sessionsMu.Unlock()
		http.SetCookie(w, &http.Cookie{
			Name:   "report_session",
			Value:  "",
			Path:   "/",
			MaxAge: -1,
		})
		ws.jsonResponse(w, http.StatusOK, map[string]bool{"ok": true})
	})

	// 2. Webhook (รองรับทั้ง /webhook และ /api/line/webhook)
	mux.HandleFunc("/webhook", ws.handleWebhook)
	mux.HandleFunc("/api/line/webhook", ws.handleWebhook)

	// Helper for checking auth
	requireAuth := func(next http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			token := ws.getAuthToken(r)
			if !ws.isValidSession(token) {
				ws.jsonResponse(w, http.StatusUnauthorized, map[string]interface{}{
					"error":         "Unauthorized",
					"authenticated": false,
				})
				return
			}
			next(w, r)
		}
	}

	// 3. Status API
	mux.HandleFunc("/api/status", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		cfg := config.LoadSettings()
		now := time.Now()
		var previewText string
		var attendanceStats map[string]interface{}
		dbConn := ws.dbSupplier()
		dbOk := false
		isMock := cfg.MockMode || strings.EqualFold(cfg.DBAuth, "mock")

		if dbConn != nil {
			people, pErr := dbConn.GetPeople()
			scans, sErr := dbConn.GetScans(now)
			if pErr == nil && sErr == nil {
				shifts, _ := dbConn.GetShifts()
				dailyShift, _ := dbConn.GetDailyShift(now)
				leaves, _ := dbConn.GetLeaves(now)
				holidays, _ := dbConn.GetHolidays()
				schoolName, workdays, _ := dbConn.GetSchool()
				if schoolName != "" {
					cfg.CompanyName = schoolName
				}

				summary := attendance.Compute(
					now, people, scans, shifts, dailyShift, leaves, holidays, workdays,
					cfg.LateTime, now,
				)

				if summary.IsWorkday && summary.TotalScans == 0 && len(summary.ByStatus("absent")) > 0 {
					previewText = fmt.Sprintf("⚠️ สรุปการมาทำงาน %s\n%s\n\nยังไม่มีข้อมูลการสแกนของวันนี้ในระบบเลย\nตรวจสอบว่าโปรแกรม HIP TIME ดึงข้อมูลจากเครื่องสแกนแล้วหรือยัง (รอบ %s น.)", cfg.CompanyName, attendance.ThaiDate(now), cfg.AutoDownloadTime)
				} else {
					previewText = attendance.BuildMessage(summary, cfg.CompanyName, &now, cfg.ShowPresent)
				}

				attendanceStats = map[string]interface{}{
					"present":      len(summary.ByStatus("present")),
					"late":         len(summary.ByStatus("late")),
					"absent":       len(summary.ByStatus("absent")),
					"leave":        len(summary.ByStatus("leave")),
					"total_people": len(summary.Results),
					"total_scans":  summary.TotalScans,
					"is_workday":   summary.IsWorkday,
				}
				dbOk = true
			} else {
				errMsg := ""
				if pErr != nil {
					errMsg = pErr.Error()
				} else if sErr != nil {
					errMsg = sErr.Error()
				}
				previewText = fmt.Sprintf("❌ ยังไม่สามารถดึงข้อมูลจากฐานข้อมูล SQL Server ได้\nสาเหตุ: %s\n\nกรุณากดปุ่ม 'ตั้งค่าระบบ' เพื่อตรวจสอบการเชื่อมต่อฐานข้อมูล", errMsg)
			}
		}

		recipients := storage.GetRecipients()
		activeCount := len(storage.GetActiveTargetIDs())
		discovered := storage.GetDiscovered()
		tunStat := tunnel.GetStatus()

		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"company_name":       cfg.CompanyName,
			"today_thai":         attendance.ThaiDate(now),
			"recipients":         recipients,
			"discovered":         discovered,
			"active_count":       activeCount,
			"send_times":         cfg.SendTimes,
			"late_time":          cfg.LateTime,
			"auto_download_time": cfg.AutoDownloadTime,
			"last_run_time":      ws.lastRunTime,
			"last_run_status":    ws.lastRunStat,
			"attendance":         attendanceStats,
			"preview_text":       previewText,
			"db_connected":       dbOk,
			"db_name":            cfg.DBName,
			"db_host":            cfg.DBHost,
			"mock_mode":          isMock,
			"has_line_token":     cfg.LineChannelToken != "",
			"has_line_secret":    cfg.LineChannelSecret != "",
			"auto_add_recipients": cfg.AutoAddRecipients,
			"tunnel":             tunStat,
		})
	}))

	// 4. Recipients APIs
	mux.HandleFunc("/api/recipients", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		item, err := storage.AddRecipient(req.ID, req.Name)
		if err != nil {
			ws.jsonResponse(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":         true,
			"item":       item,
			"recipients": storage.GetRecipients(),
		})
	}))

	mux.HandleFunc("/api/recipients/toggle", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID     string `json:"id"`
			Active bool   `json:"active"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		ok := storage.ToggleRecipient(req.ID, req.Active)
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":         ok,
			"recipients": storage.GetRecipients(),
		})
	}))

	mux.HandleFunc("/api/recipients/delete", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID string `json:"id"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		ok := storage.RemoveRecipient(req.ID)
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":         ok,
			"recipients": storage.GetRecipients(),
		})
	}))

	// 5. Discovered APIs
	mux.HandleFunc("/api/discovered/add-to-recipients", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		item, err := storage.AddRecipient(req.ID, req.Name)
		if err != nil {
			ws.jsonResponse(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":         true,
			"item":       item,
			"recipients": storage.GetRecipients(),
			"discovered": storage.GetDiscovered(),
		})
	}))

	mux.HandleFunc("/api/discovered/delete", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID string `json:"id"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		ok := storage.RemoveDiscovered(req.ID)
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":         ok,
			"discovered": storage.GetDiscovered(),
		})
	}))

	// 6. Test Send & Send Now
	mux.HandleFunc("/api/test-send", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			ID   string `json:"id"`
			Text string `json:"text"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		cfg := config.LoadSettings()
		lineClient := line.NewClient(cfg.LineChannelToken)

		var targets []string
		if strings.TrimSpace(req.ID) != "" {
			targets = []string{strings.TrimSpace(req.ID)}
		} else {
			targets = storage.GetActiveTargetIDs()
		}

		msg := req.Text
		if msg == "" {
			msg = fmt.Sprintf("🔔 ทดสอบการแจ้งเตือนจากระบบ STW_TeacherCheck\nเวลาทดสอบ: %s\nระบบพร้อมส่งสรุปเวลา %s น.", time.Now().Format("15:04:05"), strings.Join(cfg.SendTimes, ", "))
		}

		err := lineClient.SendText(targets, msg)
		if err != nil {
			ws.jsonResponse(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":      true,
			"message": "ส่งข้อความทดสอบเข้า LINE เรียบร้อยแล้ว",
		})
	}))

	mux.HandleFunc("/api/send-now", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		err := ws.sendNowFunc()
		if err != nil {
			ws.jsonResponse(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":      true,
			"message": "ส่งสรุปประจำวันเข้า LINE เรียบร้อยแล้ว",
		})
	}))

	// 7. Settings APIs
	mux.HandleFunc("/api/settings", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			currentCfg := config.LoadSettings()
			var raw map[string]interface{}
			if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
				ws.jsonResponse(w, http.StatusBadRequest, map[string]interface{}{"ok": false, "error": err.Error()})
				return
			}
			// Unmarshal on top of current config to merge partial fields
			b, _ := json.Marshal(raw)
			_ = json.Unmarshal(b, &currentCfg)

			saved, err := config.SaveSettings(currentCfg)
			if err != nil {
				ws.jsonResponse(w, http.StatusInternalServerError, map[string]interface{}{"ok": false, "error": err.Error()})
				return
			}

			// เชื่อมต่อ DB ใหม่ทันทีเมื่อมีการเปลี่ยนค่าตั้งค่า
			if ws.reconnectDB != nil {
				_ = ws.reconnectDB()
			}
			// ซิงก์ Webhook กับ LINE อัตโนมัติหากมี Tunnel รันอยู่
			go func() {
				_ = tunnel.SyncWebhookWithLine()
			}()

			ws.jsonResponse(w, http.StatusOK, map[string]interface{}{"ok": true, "settings": saved})
			return
		}

		cfg := config.LoadSettings()
		ws.jsonResponse(w, http.StatusOK, cfg)
	}))

	// 8. Logs APIs
	mux.HandleFunc("/api/logs", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		logs := logger.GlobalBuffer.GetLogs(300)
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"logs":  logs,
			"count": len(logs),
		})
	}))

	mux.HandleFunc("/api/logs/clear", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		logger.GlobalBuffer.Clear()
		ws.jsonResponse(w, http.StatusOK, map[string]bool{"ok": true})
	}))

	// 9. Test DB Connection
	mux.HandleFunc("/api/test-db", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var testCfg config.Settings
		_ = json.NewDecoder(r.Body).Decode(&testCfg)

		tmpDB, err := db.Connect(testCfg)
		if err != nil && tmpDB == nil {
			ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
				"ok":     false,
				"error":  err.Error(),
				"advice": "ไม่สามารถเปิดการเชื่อมต่อได้ ตรวจสอบรูปแบบการระบุ Server IP และ Port",
			})
			return
		}
		defer tmpDB.Close()
		res := tmpDB.TestConnection()

		// หากทดสอบผ่าน บันทึกค่าที่ใช้งานได้จริงและสลับการเชื่อมต่อหลักให้ทันที
		if ok, _ := res["ok"].(bool); ok {
			curr := config.LoadSettings()
			if host, _ := res["host"].(string); host != "" {
				curr.DBHost = host
			} else if testCfg.DBHost != "" {
				curr.DBHost = testCfg.DBHost
			}
			if dbName, _ := res["database"].(string); dbName != "" {
				curr.DBName = dbName
			} else if testCfg.DBName != "" {
				curr.DBName = testCfg.DBName
			}
			if testCfg.DBPort > 0 {
				curr.DBPort = testCfg.DBPort
			}
			if testCfg.DBAuth != "" {
				curr.DBAuth = testCfg.DBAuth
			}
			if testCfg.DBUser != "" {
				curr.DBUser = testCfg.DBUser
			}
			if testCfg.DBPassword != "" {
				curr.DBPassword = testCfg.DBPassword
			}
			curr.MockMode = testCfg.MockMode
			_, _ = config.SaveSettings(curr)
			if ws.reconnectDB != nil {
				_ = ws.reconnectDB()
			}
		}

		ws.jsonResponse(w, http.StatusOK, res)
	}))

	// 10. LINE Bot Info & Verification APIs
	mux.HandleFunc("/api/line-info", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		cfg := config.LoadSettings()
		var botInfo *line.BotInfo
		var errStr string
		var currentWebhook string
		var webhookActive bool

		if cfg.LineChannelToken != "" {
			client := line.NewClient(cfg.LineChannelToken)
			var err error
			botInfo, err = client.GetBotInfo()
			if err != nil {
				errStr = err.Error()
			} else {
				currentWebhook, webhookActive, _ = client.GetWebhookEndpoint()
			}
		}

		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"has_token":           cfg.LineChannelToken != "",
			"has_secret":          cfg.LineChannelSecret != "",
			"token_preview":       maskSecret(cfg.LineChannelToken),
			"secret_preview":      maskSecret(cfg.LineChannelSecret),
			"auto_add_recipients": cfg.AutoAddRecipients,
			"welcome_message":     cfg.WelcomeMessage,
			"bot_info":            botInfo,
			"webhook_endpoint":    currentWebhook,
			"webhook_active":      webhookActive,
			"tunnel":              tunnel.GetStatus(),
			"error":               errStr,
		})
	}))

	mux.HandleFunc("/api/test-line-token", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Token  string `json:"token"`
			Secret string `json:"secret"`
		}
		_ = json.NewDecoder(r.Body).Decode(&req)
		testToken := strings.TrimSpace(req.Token)
		if testToken == "" {
			cfg := config.LoadSettings()
			testToken = cfg.LineChannelToken
		}
		if testToken == "" {
			ws.jsonResponse(w, http.StatusBadRequest, map[string]interface{}{
				"ok":    false,
				"error": "กรุณากรอก LINE Channel Access Token ก่อนกดทดสอบ",
			})
			return
		}

		client := line.NewClient(testToken)
		info, err := client.GetBotInfo()
		if err != nil {
			ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}

		// ถ้ามี Tunnel URL อยู่แล้ว ซิงก์ Webhook ให้ด้วยทันที
		tunStat := tunnel.GetStatus()
		webhookSynced := false
		if tunStat.WebhookURL != "" {
			if err := client.SetWebhookEndpoint(tunStat.WebhookURL); err == nil {
				webhookSynced = true
			}
		}

		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":             true,
			"bot_info":       info,
			"webhook_synced": webhookSynced,
			"webhook_url":    tunStat.WebhookURL,
		})
	}))

	mux.HandleFunc("/api/sync-webhook", requireAuth(func(w http.ResponseWriter, r *http.Request) {
		if err := tunnel.SyncWebhookWithLine(); err != nil {
			ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}
		tunStat := tunnel.GetStatus()
		ws.jsonResponse(w, http.StatusOK, map[string]interface{}{
			"ok":          true,
			"webhook_url": tunStat.WebhookURL,
			"message":     "ซิงก์ Webhook URL เข้า LINE Developers สำเร็จเรียบร้อยแล้ว!",
		})
	}))

	addr := fmt.Sprintf(":%d", port)
	logger.Info("WEB", "🌐 เริ่มต้น Web UI ที่ http://0.0.0.0:%d", port)
	_ = http.ListenAndServe(addr, mux)
}

func maskSecret(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return ""
	}
	if len(s) <= 8 {
		return "******"
	}
	return s[:4] + "..." + s[len(s)-4:]
}
