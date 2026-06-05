#!/usr/bin/env bash
set -eo pipefail
shopt -s expand_aliases

# default vars
DRYCC_REGISTRY="${DRYCC_REGISTRY:-registry.drycc.cc}"
CHARTS_URL=oci://registry.drycc.cc/$([ "$CHANNEL" == "stable" ] && echo charts || echo charts-testing)
CERT_MANAGER_ENABLED="${CERT_MANAGER_ENABLED:-false}"
PLATFORM_DOMAIN="${PLATFORM_DOMAIN:?PLATFORM_DOMAIN is required}"

# get_latest_github_release fetches the latest GitHub release tag matching a regex pattern.
# Usage: get_latest_github_release <org/repo> <pattern>
#   org/repo  - GitHub organization and repository (e.g. "helm/helm")
#   pattern   - extended regex that the tag must match (e.g. "^v[0-9]+\.[0-9]+\.[0-9]+$")
# The function automatically selects the mirror URL based on INSTALL_DRYCC_MIRROR.
function get_latest_github_release {
  local repo="$1"
  local pattern="$2"
  local base_url

  if [[ "${INSTALL_DRYCC_MIRROR}" == "cn" ]]; then
    base_url="https://drycc-mirrors.drycc.cc/${repo}"
  else
    base_url="https://github.com/${repo}"
  fi

  curl -Ls "${base_url}/releases" \
    | grep -o "href=\"/${repo}/releases/tag/[^\"]*\"" \
    | sed "s|href=\"/${repo}/releases/tag/||; s|\"$||" \
    | grep -E "${pattern}" \
    | sort -Vr \
    | head -1
}

# helm_upgrade wraps "helm upgrade --install" with retry logic and a default timeout.
# Usage: helm_upgrade <release> <chart> [helm-options...]
#   HELM_MAX_RETRIES    - max number of retry attempts (default: 3)
#   HELM_RETRY_INTERVAL - seconds between retries (default: 10)
# A default timeout of 10m0s is applied unless --timeout is explicitly passed.
function helm_upgrade {
  local max_retries=${HELM_MAX_RETRIES:-3}
  local retry_interval=${HELM_RETRY_INTERVAL:-10}
  local has_timeout=false
  for arg in "$@"; do
    if [[ "$arg" == "--timeout" ]]; then
      has_timeout=true
      break
    fi
  done
  local timeout_args=()
  if [[ "$has_timeout" == "false" ]]; then
    timeout_args=(--timeout 10m0s)
  fi
  for (( attempt=1; attempt<=max_retries; attempt++ )); do
    if helm upgrade --install "$@" "${timeout_args[@]}"; then
      return 0
    fi
    if [[ $attempt -lt $max_retries ]]; then
      echo -e "\033[33m---> Warning: helm upgrade --install failed (attempt $attempt/$max_retries), retrying in ${retry_interval}s...\033[0m"
      sleep "$retry_interval"
    fi
  done
  echo -e "\033[31m---> Error: helm upgrade --install failed after $max_retries attempts\033[0m"
  return 1
}

# install_resources deploys the Drycc Resources service via Helm.
# Usage: install_resources [helm-options...]
function install_resources {
  options=${1:-""}
  echo -e "\033[32m---> Start install resources...\033[0m"

  if [[ "$CHANNEL" == "stable" ]]; then
    RESOURCES_VERSION=$(get_latest_github_release "drycc-addons/resources" "^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$")
    RESOURCES_IMAGE=${DRYCC_REGISTRY}/drycc-addons/resources:$(sed 's#v##' <<< $RESOURCES_VERSION)
    RESOURCES_IMAGE_PULL_POLICY="IfNotPresent"
  else
    RESOURCES_IMAGE=${DRYCC_REGISTRY}/drycc-addons/resources:canary
    RESOURCES_IMAGE_PULL_POLICY="Always"
  fi

cat << EOF > "/tmp/resources-values.yaml"
image:
  repository: ${RESOURCES_IMAGE%:*}
  tag: ${RESOURCES_IMAGE##*:}
  pullPolicy: ${RESOURCES_IMAGE_PULL_POLICY}

controller:
  url: ${CONTROLLER_URL:-http://drycc-controller-api.drycc}
  verifyTLS: ${CONTROLLER_VERIFY_TLS:-true}
  authCacheTTL: ${CONTROLLER_AUTH_CACHE_TTL:-30}

database:
  persistence:
    enabled: true
    size: ${PERSISTENCE_SIZE:-10Gi}
    storageClass: ${PERSISTENCE_STORAGE_CLASS:-""}

valkey:
  replicas: 3
  persistence:
    enabled: true
    size: ${PERSISTENCE_SIZE:-10Gi}
    storageClass: ${PERSISTENCE_STORAGE_CLASS:-""}

kubernetes:
  apiVerifyTLS: ${K8S_API_VERIFY_TLS:-true}

secretKey: ${DRYCC_SECRET_KEY:-$(openssl rand -hex 32)}

global:
  platformDomain: ${PLATFORM_DOMAIN}
  certManagerEnabled: ${CERT_MANAGER_ENABLED}
EOF

  helm_upgrade resources $CHARTS_URL/resources \
    --namespace drycc-resources \
    --values /tmp/resources-values.yaml \
    --create-namespace --wait --timeout 10m0s $options
  echo -e "\033[32m---> Resources install completed!\033[0m"
}

# install_catalog deploys the Kubernetes Service Catalog via Helm.
# Uses the "canary" image by default; fetches the latest stable version when CHANNEL is "stable".
# Usage: install_catalog [helm-options...]
function install_catalog() {
  service_catalog_version="canary"
  if [[ "$CHANNEL" == "stable" ]]; then
    service_catalog_version=$(get_latest_github_release "drycc-addons/service-catalog" "^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$")
  fi

  options=${1:-""}
  echo -e "\033[32m---> Start install catalog...\033[0m"
  helm_upgrade catalog $CHARTS_URL/catalog \
    --set asyncBindingOperationsEnabled=true \
    --set image=registry.drycc.cc/drycc-addons/service-catalog:${service_catalog_version#v} \
    --namespace catalog \
    --create-namespace --wait $options
  echo -e "\033[32m---> Catalog install completed!\033[0m"
}

# install_helmbroker deploys the Helm Broker and registers it as a ClusterServiceBroker.
# Usage: install_helmbroker [helm-options...]
#   HELMBROKER_USERNAME - override the auto-generated broker username
#   HELMBROKER_PASSWORD - override the auto-generated broker password
function install_helmbroker {
  if [[ "${INSTALL_DRYCC_MIRROR}" == "cn" ]] ; then
    addons_base_url="https://drycc-mirrors.drycc.cc/drycc-addons/addons"
  else
    addons_base_url="https://github.com/drycc-addons/addons"
  fi
  version="latest"
  if [[ "$CHANNEL" == "stable" ]]; then
    version=$(get_latest_github_release "drycc-addons/addons" "^v[0-9]+$")
    version=${version:-latest}
  fi
  addons_url="${addons_base_url}/releases/download/${version}/index.yaml"

  options=${1:-""}
  local VALKEY_PASSWORD=$(kubectl get secrets -n drycc valkey-creds -o jsonpath="{.data.password}"| base64 -d)
  local HELMBROKER_USERNAME=${HELMBROKER_USERNAME:-$(cat /proc/sys/kernel/random/uuid)}
  local HELMBROKER_PASSWORD=${HELMBROKER_PASSWORD:-$(cat /proc/sys/kernel/random/uuid)}

  echo -e "\033[32m---> Start install helmbroker...\033[0m"

  helm_upgrade helmbroker $CHARTS_URL/helmbroker \
    --set persistence.size=${HELMBROKER_PERSISTENCE_SIZE:-5Gi} \
    --set persistence.storageClass=${HELMBROKER_PERSISTENCE_STORAGE_CLASS:-"longhorn"} \
    --set username=${HELMBROKER_USERNAME} \
    --set password=${HELMBROKER_PASSWORD} \
    --set replicas=${HELMBROKER_REPLICAS} \
    --set api.replicas=${HELMBROKER_API_REPLICAS} \
    --set celery.replicas=${HELMBROKER_CELERY_REPLICAS} \
    --namespace drycc-helmbroker --create-namespace $options --wait -f - <<EOF
repositories:
- name: drycc-helmbroker
  url: ${addons_url}
EOF

  kubectl apply -f - <<EOF
apiVersion: servicecatalog.k8s.io/v1beta1
kind: ClusterServiceBroker
metadata:
  finalizers:
  - kubernetes-incubator/service-catalog
  generation: 1
  labels:
    app.kubernetes.io/managed-by: Helm
    heritage: Helm
  name: helmbroker
spec:
  relistBehavior: Duration
  relistRequests: 5
  url: http://${HELMBROKER_USERNAME}:${HELMBROKER_PASSWORD}@drycc-helmbroker.drycc-helmbroker.svc
EOF

  echo -e "\033[32m---> Helmbroker username: $HELMBROKER_USERNAME\033[0m"
  echo -e "\033[32m---> Helmbroker password: $HELMBROKER_PASSWORD\033[0m"
  echo -e "\033[32m---> Helmbroker install completed!\033[0m"
}

if [[ -f /etc/rancher/k3s/k3s.yaml ]] ; then
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
fi

# upgrade upgrades the resources installation using --reset-then-reuse-values.
function upgrade {
  install_catalog --reset-then-reuse-values
  install_helmbroker --reset-then-reuse-values
  install_resources --reset-then-reuse-values
  echo -e "\033[32m---> Upgrade complete, enjoy life...\033[0m"
}

if [[ -z "$@" ]] ; then
  install_catalog
  install_helmbroker
  install_resources
  echo -e "\033[32m---> Installation complete, enjoy life...\033[0m"
else
  for command in "$@"
  do
    $command
    echo -e "\033[32m---> Execute $command complete, enjoy life...\033[0m"
  done
fi
