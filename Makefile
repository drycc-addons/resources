DRYCC_REGISTRY ?= $(DEV_REGISTRY)
IMAGE_PREFIX ?= drycc-addons
COMPONENT ?= resources
SHORT_NAME ?= $(COMPONENT)
PLATFORM ?= linux/amd64,linux/arm64

include versioning.mk

SHELL_SCRIPTS = $(wildcard rootfs/bin/*) $(shell find "rootfs" -name '*.sh') $(wildcard _scripts/*.sh)

# Test processes used in quick unit testing
TEST_PROCS ?= 4

check-podman:
	@if [ -z $$(which podman) ]; then \
	  echo "Missing \`podman\` client which is required for development"; \
	  exit 2; \
	fi

build: podman-build

podman-build: check-podman
	podman build --build-arg CODENAME=${CODENAME} -t ${IMAGE} rootfs
	podman tag ${IMAGE} ${MUTABLE_IMAGE}

podman-build-test: check-podman
	podman build --build-arg CODENAME=${CODENAME} -t ${IMAGE}.test -f rootfs/Dockerfile.test rootfs

deploy: podman-build podman-push
	kubectl --namespace=drycc patch deployment drycc-$(COMPONENT) --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value":"$(IMAGE)"}]'

clean: check-podman
	podman rmi $(IMAGE)

full-clean: check-podman
	podman images -q $(IMAGE_PREFIX)/$(COMPONENT) | xargs podman rmi -f

test: test-style test-unit

test-style: podman-build-test
	podman run -v ${CURDIR}:/test -w /test/rootfs ${IMAGE}.test /test/rootfs/bin/test-style

test-unit: podman-build-test
	podman run -v ${CURDIR}:/test -w /test/rootfs ${IMAGE}.test /test/rootfs/bin/test-unit

test-integration:
	@echo "Check https://github.com/drycc/workflow-e2e for the complete integration test suite"

upload-coverage:
	$(eval CI_ENV := $(shell curl -s https://codecov.io/env | bash))
	podman run --rm ${CI_ENV} -v ${CURDIR}:/test -w /test/rootfs -e CODECOV_TOKEN=${CODECOV_TOKEN} ${IMAGE}.test /test/rootfs/bin/upload-coverage

# CLI targets
build-cli:
	cd cli && ./scripts/build.sh

test-cli:
	cd cli && go test ./...

.PHONY: check-podman build podman-build podman-build-test deploy clean full-clean test test-style test-unit test-integration upload-coverage build-cli test-cli
