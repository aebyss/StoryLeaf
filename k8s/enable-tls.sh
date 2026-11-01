#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
kubectl -n storyleaf get service storyleaf >/dev/null
kubectl apply -f k8s/ingress-tls.yaml
if [[ -n "${TLS_SECRET_NAME:-}" ]]; then
  kubectl -n storyleaf get secret "$TLS_SECRET_NAME" >/dev/null
  # DNS hosts remain the same; select an existing certificate Secret explicitly.
  patch="$(python3 -c 'import json,os; print(json.dumps({"spec":{"tls":[{"hosts":["storyleaf.example.com"],"secretName":os.environ["TLS_SECRET_NAME"]}]}}))')"
  kubectl -n storyleaf patch ingress storyleaf-tls --type merge -p "$patch"
fi
printf '\nTLS route enabled: https://storyleaf.example.com\n'
printf 'Point this hostname to 192.168.178.53 on your client or DNS.\n'
printf 'Certificate trust depends on the certificate configured in Traefik.\n'
