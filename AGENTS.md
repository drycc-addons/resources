# Resources Agent Instructions

## Testing

To run tests, set the following environment variables and use `make test`:

```bash
export DEV_REGISTRY=registry.drycc.cc
export CODENAME=trixie
make test
```

This will run:
- `test-style` — flake8 linting
- `test-unit` — Django unit tests with coverage
