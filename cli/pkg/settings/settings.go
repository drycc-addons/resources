package settings

import (
	"context"
	"fmt"
	"os"

	"github.com/drycc/resources/cli/internal/urlderive"
)

// Settings holds the configuration for the CLI
type Settings struct {
	ResourcesURL  string // Optional override
	Token         string
	SSLVerify     bool
	ResponseLimit int
}

type contextKey string

const settingsKey contextKey = "settings"

// WithSettings adds settings to a context
func WithSettings(ctx context.Context, s *Settings) context.Context {
	return context.WithValue(ctx, settingsKey, s)
}

// FromContext retrieves settings from a context
func FromContext(ctx context.Context) (*Settings, bool) {
	s, ok := ctx.Value(settingsKey).(*Settings)
	return s, ok
}

// LoadFromEnv loads settings from environment variables.
//
// The resources backend URL is resolved as follows:
//  1. If DRYCC_RESOURCES_URL is set, it is used verbatim.
//  2. Otherwise DRYCC_CONTROLLER_URL is used, with its first host label
//     replaced by "drycc-resources"
//     (e.g. http://drycc.example.drycc.cc -> http://drycc-resources.example.drycc.cc).
func LoadFromEnv() (*Settings, error) {
	s := &Settings{
		Token:     os.Getenv("DRYCC_TOKEN"),
		SSLVerify: os.Getenv("DRYCC_SSL_VERIFY") != "false",
	}

	resourcesURL, err := urlderive.DeriveResourcesURL(
		os.Getenv("DRYCC_CONTROLLER_URL"),
		os.Getenv("DRYCC_RESOURCES_URL"),
	)
	if err != nil {
		return nil, err
	}
	s.ResourcesURL = resourcesURL

	// Parse response limit
	if limit := os.Getenv("DRYCC_RESPONSE_LIMIT"); limit != "" {
		fmt.Sscanf(limit, "%d", &s.ResponseLimit)
	} else {
		s.ResponseLimit = 100
	}

	if s.Token == "" {
		return nil, fmt.Errorf("DRYCC_TOKEN is required")
	}

	return s, nil
}
