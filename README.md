# Kubernetes Demo Application

## Concepts

| Concept | Implementation | Purpose |
|---------|---------------|---------|
| **Namespace** | demo, logging, monitoring | Isolates resources into logical groups |
| **Deployment** | API, Worker | Manages stateless pods with rolling updates and scaling |
| **StatefulSet** | Redis, Loki | Manages stateful pods with stable identity and storage |
| **DaemonSet** | Alloy | Runs a pod on every node |
| **CronJob** | Stats collector | Runs pods on a schedule |
| **Service** | API service | Exposes pods via stable network endpoint |
| **Ingress** | Traefik IngressRoute | Routes external traffic to services |
| **ConfigMap** | App configuration | Stores non-sensitive configuration data |
| **Secret** | Credentials | Stores sensitive data |
| **ServiceMonitor** | Prometheus metrics | Defines targets for Prometheus scraping |

## Quick Start

### Prerequisites

- minikube
- helm
- helmfile
- uv (Python package manager)

```bash
# macOS
brew install minikube helm helmfile uv

# Linux (see official docs)
# https://minikube.sigs.k8s.io/docs/start/
# https://helm.sh/docs/intro/install/
# https://helmfile.readthedocs.io/en/latest/#installation
# https://docs.astral.sh/uv/getting-started/installation/
```

> **Tip:** For a better cluster management experience, consider using [k9s](https://k9scli.io/) (terminal UI) or [Freelens](https://github.com/freelensapp/freelens) (desktop app) instead of plain kubectl.

### Kubeconfig

Kubernetes stores cluster connection settings in `~/.kube/config`.

```bash
# View current context
kubectl config current-context

# List all contexts
kubectl config get-contexts

# Switch context
kubectl config use-context minikube

# View config
kubectl config view
```

### Setup

```bash
# Start minikube
minikube start

# Build Docker image in minikube
eval $(minikube docker-env)
docker build -t kube-demo:latest -f docker/Dockerfile .
```

### Deploy

```bash
# Deploy everything
helmfile sync

# Deploy with interactive diff
helmfile apply -i

# Deploy specific release
helmfile sync -l name=demo
helmfile sync -l name=loki -l name=alloy
```

### Test

```bash
# Start tunnel (run in separate terminal)
minikube tunnel

# Health check
curl localhost/api/health

# Create a task
curl -X POST localhost/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"payload":"Hello Kubernetes!"}'

# List tasks
curl localhost/api/tasks

# Check metrics
curl localhost/api/metrics
```

### Monitor

```bash
# Grafana (admin/admin)
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Watch API logs
kubectl logs -f -l app=api -n demo

# Watch worker logs
kubectl logs -f -l app=worker -n demo

# Check cronjob runs
kubectl get jobs -n demo

# Check ServiceMonitor
kubectl get servicemonitor -n demo
```

### Cleanup

```bash
helmfile destroy
```

## Local Development

```bash
# Install dependencies
uv sync

# Run API locally
REDIS_HOST=localhost uv run python -m app.api

# Run worker locally
REDIS_HOST=localhost uv run python -m app.worker

# Run cronjob locally
REDIS_HOST=localhost uv run python -m app.cronjob
```

## Project Structure

```
kube_meetup/
├── app/
│   ├── api.py          # Flask API
│   ├── worker.py       # Background worker
│   └── cronjob.py      # Scheduled stats
├── docker/
│   └── Dockerfile      # Multi-stage with uv
├── charts/
│   └── demo-app/       # Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── helmfile.yaml       # Orchestration
├── pyproject.toml      # Python config
└── uv.lock             # Locked deps
```
