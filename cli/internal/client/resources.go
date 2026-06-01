package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/drycc/resources/cli/pkg/settings"
)

// ResourcesClient is an HTTP client for the resources backend
type ResourcesClient struct {
	baseURL    string
	token      string
	httpClient *http.Client
}

// New creates a new ResourcesClient
func New(s *settings.Settings) (*ResourcesClient, error) {
	return &ResourcesClient{
		baseURL: s.ResourcesURL,
		token:   s.Token,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}, nil
}

// Resource represents a service catalog resource
type Resource struct {
	UUID        string                 `json:"uuid"`
	AppID       string                 `json:"app_id"`
	WorkspaceID string                 `json:"workspace_id"`
	Name        string                 `json:"name"`
	Plan        string                 `json:"plan"`
	Data        map[string]interface{} `json:"data"`
	Status      string                 `json:"status"`
	Binding     string                 `json:"binding"`
	Options     map[string]interface{} `json:"options"`
	Created     string                 `json:"created"`
	Updated     string                 `json:"updated"`
	Message     string                 `json:"message,omitempty"`
}

// Service represents a service catalog service class
type Service struct {
	ID         string `json:"id"`
	Name       string `json:"name"`
	Updateable bool   `json:"updateable"`
}

// Plan represents a service catalog service plan
type Plan struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

// ListServices returns available service classes
func (c *ResourcesClient) ListServices() ([]Service, error) {
	resp, err := c.doRequest("GET", "/resources/services/", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Results []Service `json:"results"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result.Results, nil
}

// ListPlans returns available plans for a service class
func (c *ResourcesClient) ListPlans(serviceName string) ([]Plan, error) {
	path := fmt.Sprintf("/resources/services/%s/plans/", serviceName)
	resp, err := c.doRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Results []Plan `json:"results"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result.Results, nil
}

// ListResources returns resources for an app
func (c *ResourcesClient) ListResources(appID string) ([]Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/", appID)
	resp, err := c.doRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resources []Resource
	if err := json.NewDecoder(resp.Body).Decode(&resources); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return resources, nil
}

// GetResource returns a single resource
func (c *ResourcesClient) GetResource(appID, name string) (*Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/%s/", appID, name)
	resp, err := c.doRequest("GET", path, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resource Resource
	if err := json.NewDecoder(resp.Body).Decode(&resource); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &resource, nil
}

// CreateResource creates a new resource
func (c *ResourcesClient) CreateResource(appID string, data map[string]interface{}) (*Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/", appID)
	resp, err := c.doRequest("POST", path, data)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resource Resource
	if err := json.NewDecoder(resp.Body).Decode(&resource); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &resource, nil
}

// UpdateResource updates an existing resource
func (c *ResourcesClient) UpdateResource(appID, name string, data map[string]interface{}) (*Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/%s/", appID, name)
	resp, err := c.doRequest("PUT", path, data)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resource Resource
	if err := json.NewDecoder(resp.Body).Decode(&resource); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &resource, nil
}

// DeleteResource deletes a resource
func (c *ResourcesClient) DeleteResource(appID, name string) error {
	path := fmt.Sprintf("/apps/%s/resources/%s/", appID, name)
	resp, err := c.doRequest("DELETE", path, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// BindResource binds a resource
func (c *ResourcesClient) BindResource(appID, name string) (*Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/%s/binding/", appID, name)
	data := map[string]interface{}{"bind_action": "bind"}
	resp, err := c.doRequest("PATCH", path, data)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resource Resource
	if err := json.NewDecoder(resp.Body).Decode(&resource); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &resource, nil
}

// UnbindResource unbinds a resource
func (c *ResourcesClient) UnbindResource(appID, name string) (*Resource, error) {
	path := fmt.Sprintf("/apps/%s/resources/%s/binding/", appID, name)
	data := map[string]interface{}{"bind_action": "unbind"}
	resp, err := c.doRequest("PATCH", path, data)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var resource Resource
	if err := json.NewDecoder(resp.Body).Decode(&resource); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &resource, nil
}

// doRequest performs an HTTP request
func (c *ResourcesClient) doRequest(method, path string, data interface{}) (*http.Response, error) {
	url := c.baseURL + path

	var body io.Reader
	if data != nil {
		jsonData, err := json.Marshal(data)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request data: %w", err)
		}
		body = bytes.NewBuffer(jsonData)
	}

	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "token "+c.token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		bodyBytes, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(bodyBytes))
	}

	return resp, nil
}
