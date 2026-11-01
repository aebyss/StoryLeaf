#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  echo 'Missing .env. Copy .env.example to .env and enter your FreshRSS credentials first.' >&2
  exit 1
fi
for tool in podman kubectl sudo; do command -v "$tool" >/dev/null || { echo "Missing command: $tool" >&2; exit 1; }; done
node="${K3S_NODE:-$(hostname -s)}"
if ! kubectl get node "$node" >/dev/null 2>&1; then
  echo 'Cannot find the local k3s node. Run kubectl get nodes, then K3S_NODE=YOUR_NODE bash k8s/deploy.sh' >&2
  exit 1
fi
# Run on the same machine as K3S_NODE; its local containerd receives the image.
podman build -t localhost/storyleaf:k3s .
archive="$(mktemp /tmp/storyleaf-image.XXXXXX.tar)"
trap 'rm -f "$archive"' EXIT
podman save --format docker-archive -o "$archive" localhost/storyleaf:k3s
sudo k3s ctr -n k8s.io images import "$archive"
kubectl create namespace storyleaf --dry-run=client -o yaml | kubectl apply -f -
kubectl -n storyleaf create secret generic storyleaf-env --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
kubectl label node "$node" storyleaf-local-image=true --overwrite
kubectl apply -f k8s/storyleaf.yaml
# Also replaces existing pods when a new image was imported under the same tag.
kubectl -n storyleaf rollout restart deployment/storyleaf
kubectl -n storyleaf rollout status deployment/storyleaf --timeout=120s
printf '\nStoryleaf is ready on HTTP port 30088 of your node IP.\n'
