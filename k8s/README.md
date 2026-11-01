# Simple k3s deployment

Same app, same `.env`, plain HTTP. No Ingress, certificate, domain, registry, Ollama, database, or volume is required. The NodePort Service exposes the app at `http://192.168.178.53:30088` on your current Pi.

Run **on the Raspberry Pi that runs k3s**, inside your existing StoryLeaf checkout:

```sh
cd ~/StoryLeaf
git pull
bash k8s/deploy.sh
```

The script builds with Podman, imports the image into local k3s containerd, creates a namespace and a Secret from your existing `.env`, and deploys one replica. It pins that replica to the labelled node containing the imported image. Podman’s image store and k3s’s image store are separate, so import is required. Your `.env` remains local; the generated Secret is piped directly into kubectl, not saved as a source file.

If the k3s node name differs from `hostname -s`, find it using `kubectl get nodes`, then run `K3S_NODE=YOUR_NODE bash k8s/deploy.sh`. Run on that node itself, not another machine. Keep the `storyleaf-local-image=true` label on only the node where you imported the image; this is a simple one-node deployment strategy.

If `.env` is missing, copy `.env.example` and set your FreshRSS username, API password and API URL first. Old Ollama variables are ignored.

If port 30088 is already allocated to another Kubernetes Service, choose another free NodePort in `storyleaf.yaml`. The script does not change router/firewall rules; NodePort listens on node interfaces, so LAN-only access assumes your existing firewall permits only your intended networks. No HTTPS is configured.

After confirming the k3s app works, optionally stop the older Podman copy:

```sh
podman-compose stop storyleaf
```

Future updates: `git pull` then `bash k8s/deploy.sh`. This refreshes the image and credentials and restarts the pod. Bookmarks and category preferences are browser-local and tied to the URL; moving from port 8088 to 30088 starts a separate browser storage area.

Inspect:

```sh
kubectl -n storyleaf get pods,svc
kubectl -n storyleaf logs deployment/storyleaf
```

Remove just this deployment and its credentials with `kubectl delete namespace storyleaf`. This does not remove FreshRSS, Nextcloud, the old Podman app, or the imported image.

Validation: shell syntax and manifest structure were checked locally. The deployment still needs to run on your k3s cluster; no cluster access was available during preparation.

## Enable TLS with existing Traefik

This adds a standard Kubernetes Ingress using your existing Traefik `websecure` entrypoint on port 443. It uses the same default certificate handling as your Nextcloud `tls: {}`. No Cloudflare Tunnel is involved. HTTP NodePort 30088 remains available; adding TLS does not disable it.

After the k3s app is running:

```sh
cd ~/StoryLeaf
git pull
bash k8s/enable-tls.sh
```

Open `https://storyleaf.example.com` after making that hostname resolve to `192.168.178.53`. No public DNS or router changes are made by the script. For a quick local test on a computer, add `192.168.178.53 storyleaf.example.com` to its hosts file. For phones you need a DNS mapping accessible to those devices.

TLS encryption is enabled, but this does **not** automatically obtain a new trusted certificate. Traefik must already have a certificate covering `storyleaf.example.com` (for example `*.example.com`), or you must supply one. A trusted Nextcloud certificate does not necessarily cover Storyleaf. Without a matching certificate, browsers may report a certificate error; do not treat that as verified trusted HTTPS.

If you already have a matching TLS Secret in the `storyleaf` namespace, select it:

```sh
TLS_SECRET_NAME=YOUR_EXISTING_SECRET bash k8s/enable-tls.sh
```

Alternatively import certificate files you own (do not commit private keys):

```sh
kubectl -n storyleaf create secret tls storyleaf-tls \
  --cert=/path/to/fullchain.pem --key=/path/to/privkey.pem
TLS_SECRET_NAME=storyleaf-tls bash k8s/enable-tls.sh
```

Renew imported certificates through your existing certificate-management process. To use a different hostname, edit both occurrences in `ingress-tls.yaml` and the hosts array in `enable-tls.sh` before running it. This is deliberately separate from `deploy.sh`, so regular app updates preserve the existing Ingress.

Verify TLS without changing DNS, from a machine with curl:

```sh
curl --resolve storyleaf.example.com:443:192.168.178.53 \
  -I https://storyleaf.example.com/
```

A certificate error means trust or hostname coverage still needs configuring. HTTP 200 (or 401 if app login is enabled) shows the route is responding. The route is reachable wherever your existing Traefik listener is reachable; if Traefik also accepts internet traffic, apply your existing LAN access policy to this route before using it as a LAN-only service.

References: [Traefik TLS annotations](https://doc.traefik.io/traefik/reference/routing-configuration/kubernetes/ingress/), [Kubernetes Ingress TLS](https://kubernetes.io/docs/concepts/services-networking/ingress/#tls).
