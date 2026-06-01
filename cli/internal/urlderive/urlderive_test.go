package urlderive

import (
	"testing"
)

func TestDeriveResourcesURL(t *testing.T) {
	tests := []struct {
		name          string
		controllerURL string
		overrideURL   string
		expected      string
		expectError   bool
	}{
		{
			name:          "basic subdomain",
			controllerURL: "https://drycc.example.drycc.cc",
			overrideURL:   "",
			expected:      "https://drycc-resources.example.drycc.cc",
			expectError:   false,
		},
		{
			name:          "with port",
			controllerURL: "https://drycc.example.com:8443",
			overrideURL:   "",
			expected:      "https://drycc-resources.example.com:8443",
			expectError:   false,
		},
		{
			name:          "http scheme single label",
			controllerURL: "http://drycc-controller.drycc",
			overrideURL:   "",
			expected:      "http://drycc-resources.drycc",
			expectError:   false,
		},
		{
			name:          "IP literal should fail",
			controllerURL: "http://10.0.0.1:8000",
			overrideURL:   "",
			expected:      "",
			expectError:   true,
		},
		{
			name:          "override URL",
			controllerURL: "https://drycc.example.com",
			overrideURL:   "http://localhost:8080",
			expected:      "http://localhost:8080",
			expectError:   false,
		},
		{
			name:          "with path",
			controllerURL: "https://drycc.example.com/api",
			overrideURL:   "",
			expected:      "https://drycc-resources.example.com/api",
			expectError:   false,
		},
		{
			name:          "empty controller URL should fail",
			controllerURL: "",
			overrideURL:   "",
			expected:      "",
			expectError:   true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := DeriveResourcesURL(tt.controllerURL, tt.overrideURL)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
				}
			} else {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				if result != tt.expected {
					t.Errorf("expected %s, got %s", tt.expected, result)
				}
			}
		})
	}
}
