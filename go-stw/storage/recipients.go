package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

type Recipient struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Type      string `json:"type"` // "user" or "group"
	Active    bool   `json:"active"`
	CreatedAt string `json:"created_at"`
}

type DiscoveredTarget struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Type       string `json:"type"`
	PictureURL string `json:"picture_url,omitempty"`
	LastSeen   string `json:"last_seen"`
}

var (
	storageMu      sync.RWMutex
	recipientsFile = filepath.Join("data", "recipients.json")
	discoveredFile = filepath.Join("data", "discovered.json")
	targetIDRegex  = regexp.MustCompile(`^[UCR][a-f0-9]{32}$`)
)

func IsValidTargetID(id string) bool {
	return targetIDRegex.MatchString(strings.TrimSpace(id))
}

// ================== RECIPIENTS ==================

func GetRecipients() []Recipient {
	storageMu.RLock()
	defer storageMu.RUnlock()

	_ = os.MkdirAll("data", 0755)
	bytes, err := os.ReadFile(recipientsFile)
	if err != nil {
		return []Recipient{}
	}
	var list []Recipient
	if err := json.Unmarshal(bytes, &list); err != nil {
		return []Recipient{}
	}
	return list
}

func GetActiveTargetIDs() []string {
	all := GetRecipients()
	var res []string
	for _, r := range all {
		if r.Active {
			res = append(res, r.ID)
		}
	}
	return res
}

func AddRecipient(id, name string) (Recipient, error) {
	id = strings.TrimSpace(id)
	name = strings.TrimSpace(name)
	if !IsValidTargetID(id) {
		return Recipient{}, fmt.Errorf("รูปแบบ LINE ID ไม่ถูกต้อง (ต้องขึ้นต้นด้วย U หรือ C และยาว 33 ตัวอักษร)")
	}

	storageMu.Lock()
	defer storageMu.Unlock()

	list := readRecipientsUnsafe()
	for _, r := range list {
		if strings.EqualFold(r.ID, id) {
			return Recipient{}, fmt.Errorf("ID นี้มีอยู่ในรายชื่อผู้รับรายงานแล้ว")
		}
	}

	targetType := "user"
	if strings.HasPrefix(id, "C") {
		targetType = "group"
	}
	if name == "" {
		if targetType == "group" {
			name = "กลุ่ม LINE"
		} else {
			name = "ผู้รับรายงาน"
		}
	}

	newRec := Recipient{
		ID:        id,
		Name:      name,
		Type:      targetType,
		Active:    true,
		CreatedAt: time.Now().Format("2006-01-02 15:04:05"),
	}
	list = append(list, newRec)
	_ = writeRecipientsUnsafe(list)

	// ลบออกจาก Discovered เมื่อเพิ่มเป็นผู้รับแล้ว
	removeDiscoveredUnsafe(id)
	return newRec, nil
}

func AddOrActivateRecipient(id, name string) (Recipient, bool) {
	id = strings.TrimSpace(id)
	name = strings.TrimSpace(name)
	if !IsValidTargetID(id) {
		return Recipient{}, false
	}

	storageMu.Lock()
	defer storageMu.Unlock()

	list := readRecipientsUnsafe()
	for i, r := range list {
		if strings.EqualFold(r.ID, id) {
			changed := false
			if !r.Active {
				list[i].Active = true
				changed = true
			}
			if name != "" && list[i].Name != name {
				list[i].Name = name
				changed = true
			}
			if changed {
				_ = writeRecipientsUnsafe(list)
			}
			removeDiscoveredUnsafe(id)
			return list[i], false
		}
	}

	targetType := "user"
	if strings.HasPrefix(id, "C") {
		targetType = "group"
	}
	if name == "" {
		if targetType == "group" {
			name = "กลุ่ม LINE"
		} else {
			name = "ผู้รับรายงาน"
		}
	}

	newRec := Recipient{
		ID:        id,
		Name:      name,
		Type:      targetType,
		Active:    true,
		CreatedAt: time.Now().Format("2006-01-02 15:04:05"),
	}
	list = append(list, newRec)
	_ = writeRecipientsUnsafe(list)
	removeDiscoveredUnsafe(id)
	return newRec, true
}

func ToggleRecipient(id string, active bool) bool {
	storageMu.Lock()
	defer storageMu.Unlock()

	list := readRecipientsUnsafe()
	found := false
	for i := range list {
		if strings.EqualFold(list[i].ID, id) {
			list[i].Active = active
			found = true
			break
		}
	}
	if found {
		_ = writeRecipientsUnsafe(list)
	}
	return found
}

func RemoveRecipient(id string) bool {
	storageMu.Lock()
	defer storageMu.Unlock()

	list := readRecipientsUnsafe()
	var updated []Recipient
	found := false
	for _, r := range list {
		if strings.EqualFold(r.ID, id) {
			found = true
			continue
		}
		updated = append(updated, r)
	}
	if found {
		_ = writeRecipientsUnsafe(updated)
	}
	return found
}

func readRecipientsUnsafe() []Recipient {
	bytes, err := os.ReadFile(recipientsFile)
	if err != nil {
		return []Recipient{}
	}
	var list []Recipient
	_ = json.Unmarshal(bytes, &list)
	return list
}

func writeRecipientsUnsafe(list []Recipient) error {
	_ = os.MkdirAll("data", 0755)
	b, err := json.MarshalIndent(list, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(recipientsFile, b, 0644)
}

// ================== DISCOVERED ==================

func GetDiscovered() []DiscoveredTarget {
	storageMu.RLock()
	defer storageMu.RUnlock()

	bytes, err := os.ReadFile(discoveredFile)
	if err != nil {
		return []DiscoveredTarget{}
	}
	var list []DiscoveredTarget
	_ = json.Unmarshal(bytes, &list)
	return list
}

func RecordDiscovered(id, name, targetType, picURL string) {
	if !IsValidTargetID(id) {
		return
	}
	storageMu.Lock()
	defer storageMu.Unlock()

	list := readDiscoveredUnsafe()
	now := time.Now().Format("2006-01-02 15:04:05")

	found := false
	for i := range list {
		if strings.EqualFold(list[i].ID, id) {
			if name != "" {
				list[i].Name = name
			}
			if picURL != "" {
				list[i].PictureURL = picURL
			}
			list[i].LastSeen = now
			found = true
			break
		}
	}

	if !found {
		list = append([]DiscoveredTarget{{
			ID:         id,
			Name:       name,
			Type:       targetType,
			PictureURL: picURL,
			LastSeen:   now,
		}}, list...)
	}

	_ = writeDiscoveredUnsafe(list)
}

func RemoveDiscovered(id string) bool {
	storageMu.Lock()
	defer storageMu.Unlock()
	return removeDiscoveredUnsafe(id)
}

func removeDiscoveredUnsafe(id string) bool {
	list := readDiscoveredUnsafe()
	var updated []DiscoveredTarget
	found := false
	for _, d := range list {
		if strings.EqualFold(d.ID, id) {
			found = true
			continue
		}
		updated = append(updated, d)
	}
	if found {
		_ = writeDiscoveredUnsafe(updated)
	}
	return found
}

func readDiscoveredUnsafe() []DiscoveredTarget {
	bytes, err := os.ReadFile(discoveredFile)
	if err != nil {
		return []DiscoveredTarget{}
	}
	var list []DiscoveredTarget
	_ = json.Unmarshal(bytes, &list)
	return list
}

func writeDiscoveredUnsafe(list []DiscoveredTarget) error {
	_ = os.MkdirAll("data", 0755)
	b, err := json.MarshalIndent(list, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(discoveredFile, b, 0644)
}
