# Drycc Resources

Drycc Resources is a standalone service extracted from the Drycc Controller. It manages
Kubernetes Service Catalog (svcat) resources — provisioning, binding, and lifecycle
management of external services for applications.

## Architecture

- **Backend**: Django + DRF service with passthrough authentication to the Drycc Controller
- **CLI**: Go binary (`drycc-resources`) that operates as a kubectl-style plugin for the `drycc` CLI
- **Storage**: Independent PostgreSQL database
- **K8s**: Direct interaction with the Kubernetes Service Catalog API (svcat)

## Prerequisites

- Kubernetes cluster with Service Catalog (svcat) installed
- Wildcard DNS (`*.<base-domain>`) configured for the cluster
- Drycc Controller running (for authentication passthrough)

## Quick Start

```bash
# Build the Docker image
make build

# Build the CLI plugin
make build-cli

# Run tests
make test
make test-cli
```

## Deployment

Deploy via Helm chart at `charts/resources/`. The service is exposed at
`resources.<base-domain>` using the cluster's wildcard DNS and TLS certificate.

## CLI Plugin

The `drycc-resources` binary is designed to be used as a `drycc` CLI plugin:

```bash
# Install: place the binary in your $PATH
cp drycc-resources /usr/local/bin/

# Use via the drycc CLI
drycc resources services
drycc resources list --app myapp
drycc resources create --app myapp --name mydb --plan postgresql:default
```

## License

See [LICENSE](LICENSE) for details.
