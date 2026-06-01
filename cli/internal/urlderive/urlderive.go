package urlderive

import (
	"fmt"
	"net"
	"net/url"
	"strings"
)

// DeriveResourcesURL converts a controller URL to the resources backend URL.
// Rule: replace the first label of the host with "drycc-resources".
// Scheme/port/path are preserved.
//
// Examples:
//
//	http://drycc.example.drycc.cc      -> http://drycc-resources.example.drycc.cc
//	https://drycc.example.com:8443     -> https://drycc-resources.example.com:8443
//	http://drycc-controller.drycc      -> http://drycc-resources.drycc
//	http://10.0.0.1:8000               -> error (IP literal not supported)
//
// Escape hatch: if overrideURL (DRYCC_RESOURCES_URL) is set, it is returned
// verbatim (local dev only).
func DeriveResourcesURL(controllerURL string, overrideURL string) (string, error) {
	// If override is set, use it directly
	if overrideURL != "" {
		return overrideURL, nil
	}

	if controllerURL == "" {
		return "", fmt.Errorf("DRYCC_CONTROLLER_URL is required")
	}

	// Parse the controller URL
	u, err := url.Parse(controllerURL)
	if err != nil {
		return "", fmt.Errorf("invalid controller URL: %w", err)
	}

	// Extract host and port
	host := u.Hostname()
	port := u.Port()

	if host == "" {
		return "", fmt.Errorf("invalid controller URL: missing host in %q", controllerURL)
	}

	// Check if host is an IP address
	if net.ParseIP(host) != nil {
		return "", fmt.Errorf("IP literal not supported for URL derivation: %s", host)
	}

	// Replace the first host label with "drycc-resources".
	labels := strings.SplitN(host, ".", 2)
	newHost := "drycc-resources"
	if len(labels) == 2 {
		newHost = newHost + "." + labels[1]
	}

	// Reconstruct the host with port if present
	if port != "" {
		newHost = newHost + ":" + port
	}

	// Build the new URL
	u.Host = newHost

	return strings.TrimSuffix(u.String(), "/"), nil
}
