package logger

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type LogEntry struct {
	Time         string `json:"time"`
	Level        string `json:"level"`
	Name         string `json:"name"`
	Message      string `json:"message"`
	ErrorDetails string `json:"error_details,omitempty"`
}

type RingBuffer struct {
	mu      sync.RWMutex
	entries []LogEntry
	maxSize int
	file    *os.File
}

var GlobalBuffer *RingBuffer

func InitLogger() {
	_ = os.MkdirAll("data", 0755)
	logPath := filepath.Join("data", "app.log")
	f, _ := os.OpenFile(logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)

	GlobalBuffer = &RingBuffer{
		entries: make([]LogEntry, 0, 500),
		maxSize: 500,
		file:    f,
	}
}

func Log(level, name, msg string, errDetails string) {
	if GlobalBuffer == nil {
		InitLogger()
	}
	GlobalBuffer.Add(level, name, msg, errDetails)
}

func Info(name, format string, a ...interface{}) {
	Log("INFO", name, fmt.Sprintf(format, a...), "")
}

func Warning(name, format string, a ...interface{}) {
	Log("WARNING", name, fmt.Sprintf(format, a...), "")
}

func Warn(name, format string, a ...interface{}) {
	Warning(name, format, a...)
}

func Error(name string, err error, format string, a ...interface{}) {
	msg := fmt.Sprintf(format, a...)
	var details string
	if err != nil {
		details = err.Error()
	}
	Log("ERROR", name, msg, details)
}

func (r *RingBuffer) Add(level, name, msg, errDetails string) {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now().Format("2006-01-02 15:04:05")
	entry := LogEntry{
		Time:         now,
		Level:        level,
		Name:         name,
		Message:      msg,
		ErrorDetails: errDetails,
	}

	if len(r.entries) >= r.maxSize {
		r.entries = r.entries[1:]
	}
	r.entries = append(r.entries, entry)

	line := fmt.Sprintf("%s [%s] %s: %s\n", now, level, name, msg)
	if errDetails != "" {
		line += fmt.Sprintf("  Details: %s\n", errDetails)
	}
	fmt.Print(line)

	if r.file != nil {
		_, _ = r.file.WriteString(line)
	}
}

func (r *RingBuffer) GetLogs(limit int) []LogEntry {
	r.mu.RLock()
	defer r.mu.RUnlock()

	total := len(r.entries)
	if limit <= 0 || limit > total {
		limit = total
	}
	start := total - limit
	res := make([]LogEntry, limit)
	copy(res, r.entries[start:])
	return res
}

func (r *RingBuffer) Clear() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.entries = make([]LogEntry, 0, r.maxSize)
}
