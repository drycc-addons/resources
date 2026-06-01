package parser

import (
	"bufio"
	"encoding/base64"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/drycc/resources/cli/internal/client"
	"github.com/drycc/resources/cli/pkg/settings"
	"github.com/spf13/cobra"
)

// app is the persistent --app flag value, registered on the root command.
var app string

// limit is the per-command --limit flag value.
var limit int

// SetAppFlag wires the persistent --app/-a flag onto the given (root) command.
func SetAppFlag(cmd *cobra.Command) {
	cmd.PersistentFlags().StringVarP(&app, "app", "a", "",
		"the uniquely identifiable name for the application")
}

// resolveLimit replicates the workflow-cli behaviour: when --limit is 0,
// fall back to the response limit configured in settings.
func resolveLimit(s *settings.Settings) int {
	if limit > 0 {
		return limit
	}
	return s.ResponseLimit
}

func requireApp() error {
	if app == "" {
		return fmt.Errorf("the --app/-a flag is required")
	}
	return nil
}

func newClientFromCmd(cmd *cobra.Command) (*client.ResourcesClient, *settings.Settings, error) {
	s, ok := settings.FromContext(cmd.Context())
	if !ok {
		return nil, nil, fmt.Errorf("settings not found in context")
	}
	c, err := client.New(s)
	if err != nil {
		return nil, nil, err
	}
	return c, s, nil
}

// formatTime mirrors workflow-cli's d.formatTime: pretty-print RFC3339 strings.
func formatTime(raw string) string {
	if raw == "" {
		return ""
	}
	t, err := time.Parse(time.RFC3339, raw)
	if err != nil {
		return raw
	}
	return t.Format("2006-01-02T15:04:05Z07:00")
}

// parseParams parses key=value (or key.subkey=value) parameter strings into
// a map. Mirrors workflow-cli's parseParams in commands/resources.go.
func parseParams(paramsMap map[string]interface{}, params []string) (map[string]interface{}, error) {
	regex := regexp.MustCompile(`^([A-Za-z_]+[A-Za-z0-9_]*\.{0,1}[A-Za-z0-9_]*)=([\s\S]*)$`)
	for _, param := range params {
		if !regex.MatchString(param) {
			return nil, fmt.Errorf("'%s' does not match the pattern 'key=var', ex: MODE=test", param)
		}
		captures := regex.FindStringSubmatch(param)
		paramsMap[captures[1]] = captures[2]
	}
	return paramsMap, nil
}

// loadValuesFile reads a YAML values file and base64-encodes it as
// options["rawValues"], matching workflow-cli's behaviour. The raw bytes are
// stored verbatim; YAML parsing is left to the server side, which is what
// workflow-cli effectively did as well.
func loadValuesFile(values string, paramsMap map[string]interface{}) error {
	info, err := os.Stat(values)
	if err != nil {
		return err
	}
	if info.Size() == 0 {
		return fmt.Errorf("%s is empty", values)
	}
	raw, err := os.ReadFile(values)
	if err != nil {
		return err
	}
	paramsMap["rawValues"] = base64.StdEncoding.EncodeToString(raw)
	return nil
}

func sortedKeys(m map[string]interface{}) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// NewServicesCommand creates the services command.
func NewServicesCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "services",
		Short: "List all available resource services",
		RunE: func(cmd *cobra.Command, args []string) error {
			c, s, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			results := resolveLimit(s)
			services, err := c.ListServices()
			if err != nil {
				return err
			}
			if results > 0 && len(services) > results {
				services = services[:results]
			}
			if len(services) == 0 {
				fmt.Println("Could not find any services")
				return nil
			}
			w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
			fmt.Fprintln(w, "ID\tNAME\tUPDATEABLE")
			for _, svc := range services {
				fmt.Fprintf(w, "%s\t%s\t%s\n",
					svc.ID, svc.Name, strconv.FormatBool(svc.Updateable))
			}
			return w.Flush()
		},
	}
	cmd.Flags().IntVarP(&limit, "limit", "l", 0,
		"the maximum number of results to display")
	return cmd
}

// NewPlansCommand creates the plans command.
func NewPlansCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "plans <service>",
		Short: "List all available plans for a resource service",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			c, s, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			service := args[0]
			results := resolveLimit(s)
			plans, err := c.ListPlans(service)
			if err != nil {
				return err
			}
			if results > 0 && len(plans) > results {
				plans = plans[:results]
			}
			if len(plans) == 0 {
				fmt.Printf("Could not find any plans in %s service.\n", service)
				return nil
			}
			w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
			fmt.Fprintln(w, "ID\tNAME\tDESCRIPTION")
			for _, plan := range plans {
				fmt.Fprintf(w, "%s\t%s\t%s\n",
					plan.ID, plan.Name, plan.Description)
			}
			return w.Flush()
		},
	}
	cmd.Flags().IntVarP(&limit, "limit", "l", 0,
		"the maximum number of results to display")
	return cmd
}

// NewListCommand creates the list command.
func NewListCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "list",
		Short: "List resources in the application",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, s, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			results := resolveLimit(s)
			resources, err := c.ListResources(app)
			if err != nil {
				return err
			}
			if results > 0 && len(resources) > results {
				resources = resources[:results]
			}
			if len(resources) == 0 {
				fmt.Printf("No resources found in %s app.\n", app)
				return nil
			}
			w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
			fmt.Fprintln(w, "NAME\tPLAN\tUPDATED")
			for _, r := range resources {
				fmt.Fprintf(w, "%s\t%s\t%s\n",
					r.Name, r.Plan, formatTime(r.Updated))
			}
			return w.Flush()
		},
	}
	cmd.Flags().IntVarP(&limit, "limit", "l", 0,
		"the maximum number of results to display")
	return cmd
}

// NewCreateCommand creates the create command.
//
//	create <name> <service> <plan> [<param>=<value>...]
func NewCreateCommand() *cobra.Command {
	var values string
	cmd := &cobra.Command{
		Use:   "create <name> <service> <plan> [<param>=<value>...]",
		Short: "Create a resource for the application",
		Args:  cobra.MinimumNArgs(3),
		Example: "  drycc-resources create myredis redis standard-128 -f file.yaml\n" +
			"  drycc-resources create myredis redis standard-128 MODE=test --app demo01",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			name := args[0]
			plan := fmt.Sprintf("%s:%s", args[1], args[2])
			params := args[3:]

			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}

			paramsMap := make(map[string]interface{})
			if values != "" {
				if err := loadValuesFile(values, paramsMap); err != nil {
					return err
				}
				// Mirror workflow-cli: when --values is set, params are discarded.
				params = nil
			}
			if paramsMap, err = parseParams(paramsMap, params); err != nil {
				return err
			}

			fmt.Printf("Creating %s to %s... ", name, app)

			data := map[string]interface{}{
				"name":    name,
				"plan":    plan,
				"options": paramsMap,
			}
			if _, err := c.CreateResource(app, data); err != nil {
				fmt.Println()
				return err
			}
			fmt.Println("done")
			return nil
		},
	}
	cmd.Flags().StringVarP(&values, "values", "f", "",
		"specify values in a YAML file. If set, params will be discarded")
	return cmd
}

// NewDescribeCommand creates the describe command.
func NewDescribeCommand() *cobra.Command {
	var details bool
	cmd := &cobra.Command{
		Use:   "describe <name>",
		Short: "Get a resource's detail in the application",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			name := args[0]
			r, err := c.GetResource(app, name)
			if err != nil {
				return err
			}

			w := tabwriter.NewWriter(os.Stdout, 0, 8, 2, ' ', 0)
			row := func(cols ...string) {
				fmt.Fprintln(w, joinCols(cols))
			}
			row("App:", app)
			row("UUID:", r.UUID)
			row("Name:", r.Name)
			row("Plan:", r.Plan)
			row("Status:", r.Status)
			row("Binding:", r.Binding)
			row("Data:")
			for _, k := range sortedKeys(r.Data) {
				row("", fmt.Sprintf("%s:", k), fmt.Sprintf("%v", r.Data[k]))
			}
			if details {
				row("Options:")
				for _, k := range sortedKeys(r.Options) {
					row("", fmt.Sprintf("%s:", k), fmt.Sprintf("%v", r.Options[k]))
				}
				if r.Message != "" {
					row("Message:", r.Message)
				}
			}
			row("Created:", formatTime(r.Created))
			row("Updated:", formatTime(r.Updated))
			return w.Flush()
		},
	}
	cmd.Flags().BoolVarP(&details, "details", "d", false,
		"show detailed resource info including options and message")
	return cmd
}

// joinCols joins tab-separated columns for the tabwriter table.
func joinCols(cols []string) string {
	out := ""
	for i, c := range cols {
		if i > 0 {
			out += "\t"
		}
		out += c
	}
	return out
}

// NewUpdateCommand creates the update command.
//
//	update <name> [<param>=<value>...]
func NewUpdateCommand() *cobra.Command {
	var values string
	cmd := &cobra.Command{
		Use:   "update <name> [<param>=<value>...]",
		Short: "Update a resource in the application",
		Args:  cobra.MinimumNArgs(1),
		Example: "  drycc-resources update myredis -f file.yaml --app demo01\n" +
			"  drycc-resources update myredis MODE=test --app demo01",
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			name := args[0]
			params := args[1:]

			paramsMap := make(map[string]interface{})
			if values != "" {
				if err := loadValuesFile(values, paramsMap); err != nil {
					return err
				}
				params = nil
			}
			if paramsMap, err = parseParams(paramsMap, params); err != nil {
				return err
			}

			fmt.Printf("Updating %s to %s... ", name, app)
			data := map[string]interface{}{"options": paramsMap}
			if _, err := c.UpdateResource(app, name, data); err != nil {
				fmt.Println()
				return err
			}
			fmt.Println("done")
			return nil
		},
	}
	cmd.Flags().StringVarP(&values, "values", "f", "",
		"specify values in a YAML file. If set, params will be discarded")
	return cmd
}

// NewDestroyCommand creates the destroy command.
func NewDestroyCommand() *cobra.Command {
	var confirm string
	cmd := &cobra.Command{
		Use:          "destroy <name>",
		Short:        "Delete a resource from the application",
		Args:         cobra.ExactArgs(1),
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			name := args[0]
			if confirm == "" {
				fmt.Printf(
					" !    WARNING: Potentially Destructive Action\n"+
						" !    This command will destroy the resource: %s\n"+
						" !    To proceed, type \"%s\" or re-run this command with --confirm=%s\n\n"+
						"> ",
					name, name, name)
				reader := bufio.NewReader(os.Stdin)
				input, err := reader.ReadString('\n')
				if err != nil {
					return fmt.Errorf("failed to read confirmation: %w", err)
				}
				confirm = strings.TrimSpace(input)
			}
			if confirm != name {
				return fmt.Errorf("confirmation %q does not match resource name %q", confirm, name)
			}
			fmt.Printf("Deleting %s from %s... ", name, app)
			if err := c.DeleteResource(app, name); err != nil {
				fmt.Println()
				return err
			}
			fmt.Println("done")
			return nil
		},
	}
	cmd.Flags().StringVar(&confirm, "confirm", "",
		"skips the prompt for confirmation")
	return cmd
}

// NewBindCommand creates the bind command.
func NewBindCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "bind <name>",
		Short: "Mount a resource to process of the application",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			fmt.Print("Binding resource... ")
			if _, err := c.BindResource(app, args[0]); err != nil {
				fmt.Println()
				return err
			}
			fmt.Println("done")
			return nil
		},
	}
	return cmd
}

// NewUnbindCommand creates the unbind command.
func NewUnbindCommand() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "unbind <name>",
		Short: "Unmount a resource from the application",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if err := requireApp(); err != nil {
				return err
			}
			c, _, err := newClientFromCmd(cmd)
			if err != nil {
				return err
			}
			fmt.Print("Unbinding resource... ")
			if _, err := c.UnbindResource(app, args[0]); err != nil {
				fmt.Println()
				return err
			}
			fmt.Println("done")
			return nil
		},
	}
	return cmd
}
