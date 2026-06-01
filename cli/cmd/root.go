package cmd

import (
	"context"

	"github.com/drycc/resources/cli/internal/parser"
	"github.com/drycc/resources/cli/pkg/settings"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "drycc-resources",
	Short: "Drycc Resources CLI - manage service catalog resources",
	Long: `Drycc Resources is a CLI plugin for managing Kubernetes Service Catalog
resources (svcat) for Drycc applications.

This binary is designed to be used as a drycc CLI plugin. When placed in your
$PATH as 'drycc-resources', it can be invoked via 'drycc resources ...'.`,
}

// Execute runs the root command
func Execute(s *settings.Settings) error {
	// Store settings in a global context for subcommands to access
	ctx := context.Background()
	rootCmd.SetContext(settings.WithSettings(ctx, s))

	// Register the persistent --app/-a flag on the root command so that
	// every subcommand inherits it, matching the legacy `drycc resources`
	// behaviour from workflow-cli.
	parser.SetAppFlag(rootCmd)

	// Register subcommands
	rootCmd.AddCommand(parser.NewServicesCommand())
	rootCmd.AddCommand(parser.NewPlansCommand())
	rootCmd.AddCommand(parser.NewListCommand())
	rootCmd.AddCommand(parser.NewCreateCommand())
	rootCmd.AddCommand(parser.NewDescribeCommand())
	rootCmd.AddCommand(parser.NewUpdateCommand())
	rootCmd.AddCommand(parser.NewDestroyCommand())
	rootCmd.AddCommand(parser.NewBindCommand())
	rootCmd.AddCommand(parser.NewUnbindCommand())

	return rootCmd.Execute()
}
