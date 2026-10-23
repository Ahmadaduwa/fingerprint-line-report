//go:build windows

package tunnel

import (
	"os/exec"
	"syscall"
)

func configureCmdPlatform(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow: true,
	}
}
