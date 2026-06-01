package main

import (
	"fmt"
	"os"

	"github.com/drycc/resources/cli/cmd"
	"github.com/drycc/resources/cli/pkg/settings"
)

func main() {
	s, err := settings.LoadFromEnv()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading settings: %v\n", err)
		os.Exit(1)
	}
	if err := cmd.Execute(s); err != nil {
		os.Exit(1)
	}
}
