package tunnel

import (
	"bufio"
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"sync"
	"time"

	"stw_teacher_check/config"
	"stw_teacher_check/line"
	"stw_teacher_check/logger"
)

const win7CloudflaredURL = "https://github.com/cloudflare/cloudflared/releases/download/2023.8.2/cloudflared-windows-386.exe"

var (
	mu            sync.RWMutex
	publicURL     string
	webhookURL    string
	webhookSynced bool
	syncError     string
	tunnelRunning bool
	urlRegex      = regexp.MustCompile(`https://[a-zA-Z0-9-]+\.trycloudflare\.com`)
)

type Status struct {
	Running       bool   `json:"running"`
	PublicURL     string `json:"public_url"`
	WebhookURL    string `json:"webhook_url"`
	WebhookSynced bool   `json:"webhook_synced"`
	SyncError     string `json:"sync_error,omitempty"`
}

func GetStatus() Status {
	mu.RLock()
	defer mu.RUnlock()
	return Status{
		Running:       tunnelRunning,
		PublicURL:     publicURL,
		WebhookURL:    webhookURL,
		WebhookSynced: webhookSynced,
		SyncError:     syncError,
	}
}

func SyncWebhookWithLine() error {
	mu.RLock()
	whURL := webhookURL
	mu.RUnlock()

	if whURL == "" {
		return fmt.Errorf("ยังไม่มี URL จาก Cloudflare Tunnel")
	}

	cfg := config.LoadSettings()
	if strings.TrimSpace(cfg.LineChannelToken) == "" {
		return fmt.Errorf("ยังไม่ได้ตั้งค่า LINE Channel Access Token")
	}

	client := line.NewClient(cfg.LineChannelToken)
	// รอให้ DNS/Edge ของ Cloudflare พร้อมก่อนยิงให้ LINE ตรวจสอบ
	var lastErr error
	for attempt := 1; attempt <= 3; attempt++ {
		err := client.SetWebhookEndpoint(whURL)
		if err == nil {
			mu.Lock()
			webhookSynced = true
			syncError = ""
			mu.Unlock()
			return nil
		}
		lastErr = err
		time.Sleep(2 * time.Second)
	}

	mu.Lock()
	webhookSynced = false
	if lastErr != nil {
		syncError = lastErr.Error()
	}
	mu.Unlock()
	return lastErr
}

func findOrDownloadCloudflared() (string, error) {
	if runtime.GOOS == "windows" {
		var candidates []string
		if exePath, err := os.Executable(); err == nil {
			exeDir := filepath.Dir(exePath)
			candidates = append(candidates, filepath.Join(exeDir, "cloudflared.exe"))
		}
		candidates = append(candidates,
			"cloudflared.exe",
			filepath.Join("release-windows7", "cloudflared.exe"),
		)
		for _, c := range candidates {
			if info, err := os.Stat(c); err == nil && !info.IsDir() && info.Size() > 1024*1024 {
				return c, nil
			}
		}
		if p, err := exec.LookPath("cloudflared.exe"); err == nil {
			return p, nil
		}

		// ดาวน์โหลดรุ่น 2023.8.2 (Go 1.20 รองรับ Windows 7 32-bit) อัตโนมัติ
		targetPath := "cloudflared.exe"
		if exePath, err := os.Executable(); err == nil {
			targetPath = filepath.Join(filepath.Dir(exePath), "cloudflared.exe")
		}
		logger.Info("TUNNEL", "กำลังดาวน์โหลด cloudflared รุ่นรองรับ Windows 7 32-bit...")
		tr := &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		}
		client := &http.Client{Timeout: 120 * time.Second, Transport: tr}
		resp, err := client.Get(win7CloudflaredURL)
		if err != nil {
			return "", fmt.Errorf("ดาวน์โหลด cloudflared.exe ไม่สำเร็จ: %w", err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			return "", fmt.Errorf("ดาวน์โหลด cloudflared.exe ไม่สำเร็จ (HTTP %d)", resp.StatusCode)
		}
		out, err := os.Create(targetPath)
		if err != nil {
			return "", err
		}
		_, err = io.Copy(out, resp.Body)
		_ = out.Close()
		if err != nil {
			return "", err
		}
		logger.Info("TUNNEL", "✅ ดาวน์โหลด cloudflared.exe สำเร็จเรียบร้อย")
		return targetPath, nil
	}

	if p, err := exec.LookPath("cloudflared"); err == nil {
		return p, nil
	}
	return "", fmt.Errorf("ไม่พบโปรแกรม cloudflared ในระบบ")
}

func StartBackground(port int) {
	go func() {
		for {
			cfg := config.LoadSettings()
			if !cfg.EnableTunnel {
				time.Sleep(10 * time.Second)
				continue
			}

			binPath, err := findOrDownloadCloudflared()
			if err != nil {
				logger.Warning("TUNNEL", "ไม่สามารถเริ่ม Cloudflare Tunnel ได้: %v", err)
				mu.Lock()
				tunnelRunning = false
				syncError = err.Error()
				mu.Unlock()
				time.Sleep(30 * time.Second)
				continue
			}

			localTarget := fmt.Sprintf("http://127.0.0.1:%d", port)
			cmd := exec.Command(binPath, "tunnel", "--url", localTarget, "--no-autoupdate", "--protocol", "http2")
			configureCmdPlatform(cmd)

			stdout, _ := cmd.StdoutPipe()
			stderr, _ := cmd.StderrPipe()

			if err := cmd.Start(); err != nil {
				logger.Error("TUNNEL", err, "รัน cloudflared ไม่สำเร็จ")
				mu.Lock()
				tunnelRunning = false
				syncError = err.Error()
				mu.Unlock()
				time.Sleep(15 * time.Second)
				continue
			}

			mu.Lock()
			tunnelRunning = true
			mu.Unlock()
			logger.Info("TUNNEL", "กำลังสร้าง Cloudflare Tunnel เชื่อมต่อไปยัง %s...", localTarget)

			scanPipe := func(r io.Reader) {
				if r == nil {
					return
				}
				scanner := bufio.NewScanner(r)
				for scanner.Scan() {
					lineText := scanner.Text()
					if match := urlRegex.FindString(lineText); match != "" {
						mu.Lock()
						changed := (publicURL != match)
						publicURL = match
						webhookURL = match + "/webhook"
						mu.Unlock()

						if changed {
							logger.Info("TUNNEL", "🌐 ได้รับ Public Webhook URL: %s", match+"/webhook")
							go func() {
								time.Sleep(3 * time.Second)
								if err := SyncWebhookWithLine(); err != nil {
									logger.Warning("TUNNEL", "อัปเดต Webhook อัตโนมัติยังไม่สำเร็จ: %v", err)
								}
							}()
						}
					}
				}
			}

			go scanPipe(stdout)
			go scanPipe(stderr)

			_ = cmd.Wait()
			mu.Lock()
			tunnelRunning = false
			publicURL = ""
			webhookURL = ""
			webhookSynced = false
			mu.Unlock()
			logger.Warning("TUNNEL", "Cloudflare Tunnel หยุดทำงาน กำลังเริ่มใหม่อีกครั้งใน 10 วินาที...")
			time.Sleep(10 * time.Second)
		}
	}()
}
