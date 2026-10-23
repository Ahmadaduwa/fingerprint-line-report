# Implementation Plan: Real DB & LINE Auto-Webhook Fix

## Tasks
1. **Fix Database Layer (`go-stw/db/database.go`)**:
   - Add `encrypt=disable;trustservercertificate=true` to `buildConnString`.
   - Fix `GetScans` parameter placeholder from `?` to `@p1`.
   - Verify connection with `Ping()` inside `Connect()` and implement automatic fallback across database names (`Synctime`, `hiptime`), hosts (`127.0.0.1`, `.\SQLEXPRESS`, `SS-PC\SQLEXPRES`), and auth modes.
2. **Fix Settings & Env Loading (`go-stw/config/settings.go` & `.env`)**:
   - Load `LINE_CHANNEL_ACCESS_TOKEN` and `DB_PASSWORD` from `.env` or Web UI (`data/settings.json`) without hardcoding secrets in source code.
   - Remove forced overrides of `DBHost` and `DBAuth` when loading `settings.json`.
3. **Add LINE Webhook Auto-Sync & Broadcast (`go-stw/line/client.go`)**:
   - Add `SetWebhookEndpoint`, `GetWebhookEndpoint`, and `BroadcastText`.
   - Fallback to `BroadcastText` when no individual recipient IDs are configured, or send to active recipient IDs when present.
4. **Add Built-in Cloudflare Tunnel Manager (`go-stw/tunnel/tunnel.go`)**:
   - Bundle Windows 7 32-bit compatible `cloudflared.exe` (v2023.8.2 built with Go 1.20) in `release-windows7/` with `--no-autoupdate`.
   - Automatically start tunnel on startup, capture `https://*.trycloudflare.com`, and call `PUT /v2/bot/channel/webhook/endpoint` to register `/webhook` with LINE automatically.
5. **Update Web Server & UI (`go-stw/web/server.go`, `go-stw/web/index.html`, `go-stw/main.go`)**:
   - Reconnect DB immediately when settings are saved (`POST /api/settings`) or tested (`POST /api/test-db`).
   - Report accurate `db_connected` status, actual database name, tunnel status, and auto-synced LINE webhook URL on the dashboard.
6. **Verify & Build**:
   - Stop old conflicting `hip_line_report` container on port 8090 if needed, run unit tests, test live against `hip_sqlserver` (`Synctime`) and real LINE API (`@143smwig`), and compile Windows 7 32-bit binaries (`STW_TeacherCheck.exe` & `STW_TeacherCheck_Silent.exe`).
