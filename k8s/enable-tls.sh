#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
kubectl -n storyleaf get service storyleaf >/dev/null
host="${TLS_HOST:-$(kubectl -n storyleaf get ingress storyleaf-tls -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || true)}"
if [[ -z "$host" ]]; then
  echo 'Set TLS_HOST to your own hostname, e.g. TLS_HOST=storyleaf.example.com bash k8s/enable-tls.sh' >&2
  exit 1
fi
secret="${TLS_SECRET_NAME:-$(kubectl -n storyleaf get ingress storyleaf-tls -o jsonpath='{.spec.tls[0].secretName}' 2>/dev/null || true)}"
if [[ -n "$secret" ]]; then kubectl -n storyleaf get secret "$secret" >/dev/null; fi
TLS_HOST="$host" TLS_SECRET_NAME="$secret" python3 - <<'PY' | kubectl apply -f -
import json, os, re
host=os.environ['TLS_HOST']
if len(host)>253 or not all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?',part) for part in host.split('.')):
    raise SystemExit('Invalid TLS_HOST: enter a DNS hostname without scheme or port.')
tls={'hosts':[host]}
if os.environ.get('TLS_SECRET_NAME'): tls['secretName']=os.environ['TLS_SECRET_NAME']
print(json.dumps({'apiVersion':'networking.k8s.io/v1','kind':'Ingress','metadata':{'name':'storyleaf-tls','namespace':'storyleaf','annotations':{'traefik.ingress.kubernetes.io/router.entrypoints':'websecure','traefik.ingress.kubernetes.io/router.tls':'true'}},'spec':{'ingressClassName':'traefik','tls':[tls],'rules':[{'host':host,'http':{'paths':[{'path':'/','pathType':'Prefix','backend':{'service':{'name':'storyleaf','port':{'number':8080}}}}]}}]}}))
PY
printf '\nTLS route enabled: https://%s\n' "$host"
printf 'Point this hostname to your Traefik LAN IP on your client or DNS.\n'
printf 'Certificate trust depends on the certificate configured in Traefik.\n'
