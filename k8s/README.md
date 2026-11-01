# Simple k3s deployment

One shared Storyleaf instance, individual FreshRSS logins. The app uses an SQLite database on a 1 GiB PVC for persistent sessions and per-account bookmarks. Use the HTTPS Traefik route below for login; Secure cookies are enabled. The HTTP NodePort still exposes static pages, but authentication requires HTTPS.

Run **on the Raspberry Pi that runs k3s**, inside your existing StoryLeaf checkout:

```sh
cd ~/StoryLeaf
git pull
bash k8s/deploy.sh
```

The script builds with Podman, imports the image into local k3s containerd, creates a namespace and a Secret from your existing `.env`, and deploys one replica. It pins that replica to the labelled node containing the imported image. Podman’s image store and k3s’s image store are separate, so import is required. Your `.env` remains local; the generated Secret is piped directly into kubectl, not saved as a source file.

If the k3s node name differs from `hostname -s`, find it using `kubectl get nodes`, then run `K3S_NODE=YOUR_NODE bash k8s/deploy.sh`. Run on that node itself, not another machine. Keep the `storyleaf-local-image=true` label on only the node where you imported the image; this is a simple one-node deployment strategy.

If `.env` is missing, copy `.env.example` and set the shared FreshRSS API URL. Each person enters their own username and API password in the app. Legacy `FRESHRSS_USER`, `FRESHRSS_API_PASSWORD`, `APP_USER`, and `APP_PASSWORD` are ignored and should be removed. Old Ollama variables are also ignored.

If port 30088 is already allocated to another Kubernetes Service, choose another free NodePort in `storyleaf.yaml`. The script does not change router/firewall rules; NodePort listens on node interfaces, so LAN-only access assumes your existing firewall permits only your intended networks. Optional HTTPS is configured separately below; login uses HTTPS by default.

After confirming the k3s app works, optionally stop the older Podman copy:

```sh
podman-compose stop storyleaf
```

Future updates: `git pull` then `bash k8s/deploy.sh`. This refreshes the image and credentials and restarts the pod. Bookmarks and preferences now belong to the signed-in account and sync through this instance. Legacy browser-only bookmarks are not automatically assigned to anyone.

Inspect:

```sh
kubectl -n storyleaf get pods,svc
kubectl -n storyleaf logs deployment/storyleaf
```

The PVC now contains upstream authentication tokens, sessions, and saved stories; back it up securely. Removing the namespace can delete that persistent data. Remove this deployment and its data with `kubectl delete namespace storyleaf`. This does not remove FreshRSS, Nextcloud, the old Podman app, or the imported image.

Validation: shell syntax and manifest structure were checked locally. The deployment still needs to run on your k3s cluster; no cluster access was available during preparation.

## Enable TLS with existing Traefik

This adds a standard Kubernetes Ingress using your existing Traefik `websecure` entrypoint on port 443. It uses the same default certificate handling as your Nextcloud `tls: {}`. No Cloudflare Tunnel is involved. HTTP NodePort 30088 remains available; adding TLS does not disable it.

After the k3s app is running:

```sh
cd ~/StoryLeaf
git pull
TLS_HOST=storyleaf.example.com bash k8s/enable-tls.sh
```

Replace `storyleaf.example.com` with your own hostname locally; never commit personal hostnames. Existing installations can omit `TLS_HOST` to reuse the current Ingress hostname and certificate Secret.

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

Renew imported certificates through your existing certificate-management process. Set `TLS_HOST` to use a different hostname. `ingress-tls.yaml` is an example template; the script generates the actual Ingress from local settings. This is deliberately separate from `deploy.sh`, so regular app updates preserve the existing Ingress.

Verify TLS without changing DNS, from a machine with curl:

```sh
curl --resolve storyleaf.example.com:443:192.168.178.53 \
  -I https://storyleaf.example.com/
```

A certificate error means trust or hostname coverage still needs configuring. HTTP 200 (or 401 if app login is enabled) shows the route is responding. The route is reachable wherever your existing Traefik listener is reachable; if Traefik also accepts internet traffic, apply your existing LAN access policy to this route before using it as a LAN-only service.

References: [Traefik TLS annotations](https://doc.traefik.io/traefik/reference/routing-configuration/kubernetes/ingress/), [Kubernetes Ingress TLS](https://kubernetes.io/docs/concepts/services-networking/ingress/#tls).

## Multi-user upgrade

Run `git pull` then `bash k8s/deploy.sh`, and open your existing HTTPS URL. Existing Ingress and TLS Secret are preserved. A PVC named `storyleaf-data` is created using the cluster’s default StorageClass (normally local-path in k3s). The deployment uses Recreate strategy to attach its single ReadWriteOnce volume without competing pods. If the pod stays Pending, check `kubectl -n storyleaf get pvc` and `kubectl -n storyleaf describe pod POD_NAME`.

Only the server URL remains shared in `.env`; every person signs in with their own FreshRSS API password. Keep one replica for this SQLite/local-volume deployment. Deleting the PVC deletes sessions and saved preferences. Cookie expiry is 30 days; a revoked FreshRSS API token requires signing in again. Basic Authentication settings no longer apply.
