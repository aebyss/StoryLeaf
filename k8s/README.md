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
