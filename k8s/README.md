# Kubernetes Deployment Guide

## Overview
This directory contains Kubernetes manifests for deploying the LLM Inference Platform on a local kind cluster.

## Architecture

### Components
- **Gateway** (`app=gateway`): API gateway that routes requests to backend workers
- **Backend** (`app=backend`): LLM inference workers that process requests
- **ConfigMap**: Centralized configuration for both services
- **HPA**: Horizontal Pod Autoscaler for the gateway to handle variable load
- **Ingress**: NGINX-based ingress for external access

## Prerequisites

1. Docker installed and running
2. kind (Kubernetes in Docker) installed
3. kubectl installed
4. NGINX Ingress Controller (optional, for ingress)

## Quick Start

### 1. Create the Kind Cluster
```bash
kind create cluster --name llm
kubectl cluster-info
```

### 2. Load Docker Images into Kind
Since we're using local images, load them into the kind cluster:
```bash
kind load docker-image llm-gateway:dev --name llm
kind load docker-image llm-backend:dev --name llm
```

### 3. Deploy the Application
Apply all manifests in order:
```bash
# Apply ConfigMap first
kubectl apply -f k8s/configmap.yaml

# Deploy backend
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Deploy gateway
kubectl apply -f k8s/gateway-deployment.yaml
kubectl apply -f k8s/gateway-service.yaml
kubectl apply -f k8s/gateway-hpa.yaml
```

### 4. Verify Deployment
```bash
# Check pods
kubectl get pods

# Check services
kubectl get svc

# Check HPA
kubectl get hpa

# View logs
kubectl logs -l app=gateway --tail=50
kubectl logs -l app=backend --tail=50
```

## Accessing the Application

### Option 1: Port Forward (Recommended for Local Development)

Forward the gateway service to your local machine:
```bash
kubectl port-forward service/llm-gateway-service 8000:80
```

Then access the application at:
- http://localhost:8000

Test with curl:
```bash
curl http://localhost:8000/health
```

### Option 2: Using Ingress (Requires NGINX Ingress Controller)

#### Install NGINX Ingress Controller for Kind
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

Wait for the ingress controller to be ready:
```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

#### Apply Ingress Manifest
```bash
kubectl apply -f k8s/ingress.yaml
```

#### Update Hosts File
Add this entry to your hosts file:
- Windows: `C:\Windows\System32\drivers\etc\hosts`
- Linux/Mac: `/etc/hosts`

```
127.0.0.1 llm-platform.local
```

Then access at:
- http://llm-platform.local

Or without hostname:
- http://localhost

## Resource Configuration

### Gateway Resources
- **Requests**: 250m CPU, 256Mi memory
- **Limits**: 500m CPU, 512Mi memory
- **Replicas**: 2-10 (auto-scaled based on CPU/memory)

### Backend Resources
- **Requests**: 500m CPU, 512Mi memory
- **Limits**: 2000m CPU, 2Gi memory
- **Replicas**: 3 (fixed, can be manually scaled)

## Health Checks

### Gateway
- **Liveness**: `GET /health` (checks every 10s)
- **Readiness**: `GET /ready` (checks every 5s)

### Backend
- **Liveness**: `GET /health` (checks every 15s)
- **Readiness**: `GET /ready` (checks every 10s)

## Scaling

### Manual Scaling
Scale the backend deployment:
```bash
kubectl scale deployment llm-backend --replicas=5
```

### Auto-Scaling (Gateway)
The gateway has HPA configured:
- Scales based on CPU (target: 70%) and memory (target: 80%)
- Min replicas: 2
- Max replicas: 10

Monitor HPA:
```bash
kubectl get hpa llm-gateway-hpa --watch
```

## Monitoring

### View Pod Status
```bash
kubectl get pods -o wide
```

### View Pod Logs
```bash
# Gateway logs
kubectl logs -l app=gateway -f

# Backend logs
kubectl logs -l app=backend -f

# Specific pod
kubectl logs <pod-name> -f
```

### Describe Resources
```bash
kubectl describe deployment llm-gateway
kubectl describe deployment llm-backend
kubectl describe hpa llm-gateway-hpa
```

### Resource Usage
```bash
kubectl top nodes
kubectl top pods
```

## Configuration Updates

To update configuration:
1. Edit `k8s/configmap.yaml`
2. Apply changes: `kubectl apply -f k8s/configmap.yaml`
3. Restart deployments:
```bash
kubectl rollout restart deployment llm-gateway
kubectl rollout restart deployment llm-backend
```

## Troubleshooting

### Pods Not Starting
```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Image Pull Issues
Since using local images, ensure they're loaded into kind:
```bash
kind load docker-image llm-gateway:dev --name llm
kind load docker-image llm-backend:dev --name llm
```

### Service Not Accessible
Check service and endpoints:
```bash
kubectl get svc
kubectl get endpoints
```

### HPA Not Scaling
Check metrics server is installed:
```bash
kubectl get deployment metrics-server -n kube-system
```

If not installed:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

For kind, you may need to patch metrics-server:
```bash
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

## Cleanup

### Delete All Resources
```bash
kubectl delete -f k8s/
```

### Delete the Kind Cluster
```bash
kind delete cluster --name llm
```

## Manifest Files

- **configmap.yaml**: Application configuration
- **backend-deployment.yaml**: Backend deployment with 3 replicas
- **backend-service.yaml**: Backend ClusterIP service
- **gateway-deployment.yaml**: Gateway deployment with 2 replicas
- **gateway-service.yaml**: Gateway ClusterIP service
- **gateway-hpa.yaml**: Horizontal Pod Autoscaler for gateway
- **ingress.yaml**: NGINX ingress for external access

## Next Steps

1. Set up monitoring with Prometheus/Grafana
2. Add logging aggregation (ELK/Loki)
3. Configure persistent storage for models
4. Add network policies for security
5. Set up CI/CD for automated deployments
