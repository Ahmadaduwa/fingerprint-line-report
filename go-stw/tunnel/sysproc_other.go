//go:build !windows

package tunnel

import "os/exec"

func configureCmdPlatform(cmd *exec.Cmd) {
}
