# 🎯 Complete Kubernetes Debugging Guide - All Scenarios

A comprehensive guide covering every debugging scenario you'll encounter while working with Kubernetes, with actual code examples, commands, and step-by-step solutions.

## 📑 Table of Contents

1. [Pod Issues](#1-pod-issues)
2. [Deployment & ReplicaSet Problems](#2-deployment--replicaset-problems)
3. [Service & Networking Issues](#3-service--networking-issues)
4. [ConfigMap & Secret Issues](#4-configmap--secret-issues)
5. [Persistent Volume Issues](#5-persistent-volume-issues)
6. [Resource Quota & Limit Issues](#6-resource-quota--limit-issues)
7. [RBAC & Security Issues](#7-rbac--security-issues)
8. [Ingress Issues](#8-ingress-issues)
9. [Node Issues](#9-node-issues)
10. [StatefulSet Issues](#10-statefulset-issues)
11. [Job & CronJob Issues](#11-job--cronjob-issues)
12. [Debugging Toolkit & Best Practices](#12-debugging-toolkit--best-practices)

---

## 1️⃣ Pod Issues

### Scenario 1.1: Pod Stuck in Pending State

**Problem:** Pod remains in Pending state and never starts.

```bash
$ kubectl get pods
NAME                          READY   STATUS    RESTARTS   AGE
llm-backend-7d9f8c5b-xk2lp   0/1     Pending   0          5m
```

**Debug Commands:**

```bash
# Get detailed pod information
kubectl describe pod llm-backend-7d9f8c5b-xk2lp

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check node resources
kubectl describe nodes

# Check if PVC exists
kubectl get pvc
```

**Root Causes:**

1. **Insufficient Resources**
```
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  2m    default-scheduler  0/3 nodes are available: 3 Insufficient cpu.
```

2. **Node Selector Mismatch**
3. **PersistentVolumeClaim Not Available**
4. **ImagePullBackOff** (covered in 1.3)

**Solution:**

❌ **Bad Example:** Requesting more resources than cluster has

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-hog
spec:
  containers:
  - name: app
    image: nginx
    resources:
      requests:
        memory: "64Gi"  # Cluster only has 32Gi total
        cpu: "16"       # Cluster only has 8 cores
```

✅ **Good Example:** Reasonable resource requests

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: nginx
    resources:
      requests:
        memory: "512Mi"
        cpu: "250m"
      limits:
        memory: "1Gi"
        cpu: "500m"
```

**Commands to Fix:**

```bash
# Check available resources on nodes
kubectl top nodes

# Reduce replicas if needed
kubectl scale deployment llm-backend --replicas=2

# Delete pending pod to retry
kubectl delete pod llm-backend-7d9f8c5b-xk2lp
```

---

### Scenario 1.2: Pod in CrashLoopBackOff

**Problem:** Pod keeps restarting repeatedly.

```bash
$ kubectl get pods
NAME                          READY   STATUS             RESTARTS   AGE
llm-gateway-6b8f9d-xk2lp     0/1     CrashLoopBackOff   5          3m
```

**Debug Commands:**

```bash
# Check current logs
kubectl logs llm-gateway-6b8f9d-xk2lp

# Check previous container logs
kubectl logs llm-gateway-6b8f9d-xk2lp --previous

# Describe pod for events
kubectl describe pod llm-gateway-6b8f9d-xk2lp

# Check if it's a probe issue
kubectl get pod llm-gateway-6b8f9d-xk2lp -o yaml | grep -A 10 livenessProbe
```

**Root Causes:**

1. **Application Error**

```python
# Bad Python code causing crash
import os

# Missing required environment variable
BACKEND_URL = os.environ["BACKEND_URL"]  # KeyError if not set

def main():
    connect_to_backend(BACKEND_URL)
```

2. **Missing Environment Variables**
3. **Wrong Command/Entrypoint**
4. **Liveness Probe Too Aggressive**

**Solution:**

✅ **Good Python Code with Error Handling:**

```python
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Graceful handling of missing env vars
    backend_url = os.getenv("BACKEND_URL")
    if not backend_url:
        logger.error("BACKEND_URL environment variable not set")
        sys.exit(1)
    
    # Retry logic for startup
    max_retries = 5
    for attempt in range(max_retries):
        try:
            connect_to_backend(backend_url)
            logger.info("Successfully connected to backend")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to connect after {max_retries} attempts")
                sys.exit(1)

if __name__ == "__main__":
    main()
```

❌ **Bad YAML:** Missing environment variable

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1
    # Missing BACKEND_URL env var that app requires
```

✅ **Good YAML:** With environment variables and proper probes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1
    env:
    - name: BACKEND_URL
      value: "http://backend-service:8001"
    - name: LOG_LEVEL
      value: "INFO"
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8000
      initialDelaySeconds: 30  # Give app time to start
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
```

**Commands to Fix:**

```bash
# Edit deployment to add missing env vars
kubectl edit deployment llm-gateway

# Or apply updated manifest
kubectl apply -f gateway-deployment.yaml

# Watch pods restart
kubectl get pods -w
```

---

### Scenario 1.3: Pod in ImagePullBackOff

**Problem:** Kubernetes cannot pull the container image.

```bash
$ kubectl get pods
NAME                          READY   STATUS             RESTARTS   AGE
llm-backend-7d9f8c5b-xk2lp   0/1     ImagePullBackOff   0          2m
```

**Debug Commands:**

```bash
# Describe pod to see error
kubectl describe pod llm-backend-7d9f8c5b-xk2lp

# Check events
kubectl get events | grep -i "pull"

# Verify image exists
docker pull llm-backend:v1  # On your machine
```

**Root Causes:**

1. **Image Doesn't Exist**

```
Events:
  Type     Reason     Age   From               Message
  ----     ------     ----  ----               -------
  Warning  Failed     1m    kubelet            Failed to pull image "llm-backend:v2": rpc error: code = Unknown desc = Error response from daemon: manifest for llm-backend:v2 not found
```

2. **No Image Pull Credentials**

```
Failed to pull image "private-registry.io/myapp:v1": rpc error: code = Unknown desc = Error response from daemon: pull access denied
```

3. **Registry Unreachable**

**Solution:**

✅ **Create Docker Registry Secret:**

```bash
# Create secret for private registry
kubectl create secret docker-registry regcred   --docker-server=private-registry.io   --docker-username=myuser   --docker-password=mypassword   --docker-email=myemail@example.com

# Or from existing docker config
kubectl create secret generic regcred   --from-file=.dockerconfigjson=$HOME/.docker/config.json   --type=kubernetes.io/dockerconfigjson
```

❌ **Bad YAML:** No imagePullSecrets for private registry

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: private-registry.io/myapp:v1  # Will fail without credentials
```

✅ **Good YAML:** With imagePullSecrets

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  imagePullSecrets:
  - name: regcred
  containers:
  - name: app
    image: private-registry.io/myapp:v1
    imagePullPolicy: IfNotPresent
```

**For Local Development (kind/minikube):**

```bash
# Load image directly into kind
kind load docker-image llm-backend:dev --name my-cluster

# Or use imagePullPolicy: Never
```

```yaml
spec:
  containers:
  - name: backend
    image: llm-backend:dev
    imagePullPolicy: Never  # Don't try to pull, use local
```

---

### Scenario 1.4: Pod Running But Not Ready

**Problem:** Pod is running but readiness probe keeps failing.

```bash
$ kubectl get pods
NAME                          READY   STATUS    RESTARTS   AGE
llm-gateway-6b8f9d-xk2lp     0/1     Running   0          2m
```

**Debug Commands:**

```bash
# Check pod status
kubectl describe pod llm-gateway-6b8f9d-xk2lp

# Check logs for errors
kubectl logs llm-gateway-6b8f9d-xk2lp

# Manually test the readiness endpoint
kubectl exec llm-gateway-6b8f9d-xk2lp -- curl -f http://localhost:8000/readyz

# Check if all init containers completed
kubectl get pod llm-gateway-6b8f9d-xk2lp -o jsonpath='{.status.initContainerStatuses[*].ready}'
```

**Root Causes:**

1. **Readiness Probe Failing**

```
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Warning  Unhealthy  30s (x10 over 2m)  kubelet            Readiness probe failed: HTTP probe failed with statuscode: 503
```

2. **Dependency Not Available** (e.g., database, backend service)
3. **Application Still Initializing**

**Solution:**

✅ **Good Python Readiness Endpoint:**

```python
from fastapi import FastAPI, Response
import httpx
import os

app = FastAPI()

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-service:8001")

@app.get("/healthz")
async def health_check():
    """Liveness probe - is the app alive?"""
    return {"status": "ok"}

@app.get("/readyz")
async def readiness_check():
    """Readiness probe - is the app ready to serve traffic?"""
    try:
        # Check if backend is reachable
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{BACKEND_URL}/healthz")
            if response.status_code != 200:
                return Response(
                    content='{"status":"not ready","reason":"backend unhealthy"}',
                    status_code=503
                )
        
        return {"status": "ready"}
    except Exception as e:
        return Response(
            content=f'{{"status":"not ready","reason":"{str(e)}"}}',
            status_code=503
        )
```

✅ **Good YAML with InitContainers:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gateway
spec:
  initContainers:
  - name: wait-for-backend
    image: busybox:1.36
    command: 
    - 'sh'
    - '-c'
    - |
      until nc -z backend-service 8001; do
        echo "Waiting for backend service..."
        sleep 2
      done
      echo "Backend is ready!"
  containers:
  - name: gateway
    image: llm-gateway:v1
    ports:
    - containerPort: 8000
    readinessProbe:
      httpGet:
        path: /readyz
        port: 8000
      initialDelaySeconds: 10  # Give time to initialize
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1       # Must succeed once
      failureThreshold: 3       # Allow 3 failures before marking unready
```

---

### Scenario 1.5: Pod OOMKilled

**Problem:** Pod is killed due to Out Of Memory (OOM).

```bash
$ kubectl get pods
NAME                          READY   STATUS      RESTARTS   AGE
llm-backend-7d9f8c5b-xk2lp   0/1     OOMKilled   3          5m
```

**Debug Commands:**

```bash
# Check pod status
kubectl describe pod llm-backend-7d9f8c5b-xk2lp

# Look for exit code 137 (OOMKilled)
kubectl get pod llm-backend-7d9f8c5b-xk2lp -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'

# Check memory usage
kubectl top pod llm-backend-7d9f8c5b-xk2lp

# Check node memory
kubectl top nodes
```

**Output:**

```
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
```

**Root Causes:**

1. **Memory Limit Too Low**
2. **Memory Leak in Application**
3. **Unexpected High Load**

**Solution:**

❌ **Bad YAML:** Memory limit too low

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backend
spec:
  containers:
  - name: backend
    image: llm-backend:v1
    resources:
      limits:
        memory: "128Mi"  # Too low for LLM backend
```

✅ **Good YAML:** Appropriate memory limits

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backend
spec:
  containers:
  - name: backend
    image: llm-backend:v1
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "2Gi"  # Adequate for workload
        cpu: "2000m"
```

✅ **Python Memory Profiling:**

```python
import tracemalloc
import logging

logger = logging.getLogger(__name__)

def monitor_memory():
    """Monitor memory usage"""
    tracemalloc.start()
    
    # Your application code here
    
    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"Current memory: {current / 1024 / 1024:.2f} MB")
    logger.info(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
    tracemalloc.stop()

# Use memory-efficient generators instead of lists
def process_large_dataset():
    # Bad: Loads everything into memory
    # data = [process(item) for item in huge_dataset]
    
    # Good: Processes one item at a time
    for item in huge_dataset:
        yield process(item)
```

✅ **HPA for Auto-Scaling:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 70  # Scale when memory > 70%
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

---

### Scenario 1.6: Cannot Execute Into Pod

**Problem:** Unable to exec into a running pod.

```bash
$ kubectl exec -it llm-gateway-6b8f9d-xk2lp -- /bin/bash
error: Internal error occurred: error executing command in container: failed to exec in container: failed to start exec "abc123": OCI runtime exec failed: exec failed: unable to start container process: exec: "/bin/bash": stat /bin/bash: no such file or directory: unknown
```

**Debug Commands:**

```bash
# Check if pod is running
kubectl get pod llm-gateway-6b8f9d-xk2lp

# List containers in pod (for multi-container pods)
kubectl get pod llm-gateway-6b8f9d-xk2lp -o jsonpath='{.spec.containers[*].name}'

# Try different shells
kubectl exec -it llm-gateway-6b8f9d-xk2lp -- /bin/sh
kubectl exec -it llm-gateway-6b8f9d-xk2lp -- sh
```

**Root Causes:**

1. **Shell Not Available** (Alpine images often don't have bash)
2. **Wrong Container** (multi-container pod)
3. **Pod Not Running**

**Solution:**

```bash
# For Alpine-based images, use sh instead of bash
kubectl exec -it llm-gateway-6b8f9d-xk2lp -- sh

# For multi-container pods, specify container
kubectl exec -it llm-gateway-6b8f9d-xk2lp -c gateway -- sh

# Run a single command without interactive shell
kubectl exec llm-gateway-6b8f9d-xk2lp -- ps aux
kubectl exec llm-gateway-6b8f9d-xk2lp -- env
kubectl exec llm-gateway-6b8f9d-xk2lp -- cat /etc/os-release
```

---

## 2️⃣ Deployment & ReplicaSet Problems

### Scenario 2.1: Deployment Not Rolling Out

**Problem:** New deployment version is not rolling out.

```bash
$ kubectl rollout status deployment/llm-gateway
Waiting for deployment "llm-gateway" rollout to finish: 1 old replicas are pending termination...
```

**Debug Commands:**

```bash
# Check rollout status
kubectl rollout status deployment/llm-gateway

# Describe deployment
kubectl describe deployment llm-gateway

# Check ReplicaSets
kubectl get rs -l app=gateway

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20

# Check if PodDisruptionBudget is blocking
kubectl get pdb
```

**Root Causes:**

1. **New Pods Failing to Start**
2. **Insufficient Resources**
3. **PodDisruptionBudget (PDB) Blocking Termination**

**Solution:**

❌ **Bad PDB:** Too restrictive

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway-pdb
spec:
  minAvailable: 2  # If you only have 2 replicas, can't terminate any!
  selector:
    matchLabels:
      app: gateway
```

✅ **Good PDB:** Allows rolling updates

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway-pdb
spec:
  maxUnavailable: 1  # Allow one pod to be unavailable during updates
  selector:
    matchLabels:
      app: gateway
```

**Commands to Fix:**

```bash
# Check what's preventing rollout
kubectl describe deployment llm-gateway | grep -A 10 Conditions

# Force delete problematic pods
kubectl delete pod llm-gateway-old-xxx --grace-period=0 --force

# Rollback if needed
kubectl rollout undo deployment/llm-gateway

# Pause rollout to investigate
kubectl rollout pause deployment/llm-gateway
```

---

### Scenario 2.2: Wrong Number of Replicas

**Problem:** Deployment shows desired replicas but different number is running.

```bash
$ kubectl get deployment llm-backend
NAME          READY   UP-TO-DATE   AVAILABLE   AGE
llm-backend   2/3     3            2           5m
```

**Debug Commands:**

```bash
# Get detailed deployment info
kubectl describe deployment llm-backend

# Check ReplicaSets
kubectl get rs -l app=backend

# Check if HPA is conflicting
kubectl get hpa

# Check events
kubectl get events | grep llm-backend
```

**Root Causes:**

1. **Pods Failing Readiness Checks**
2. **HPA Overriding Manual Scale**
3. **Resource Constraints**

**Solution:**

```bash
# Check if HPA is managing replicas
kubectl get hpa llm-backend-hpa -o yaml

# If HPA exists, don't manually scale
# Instead, adjust HPA or delete it
kubectl delete hpa llm-backend-hpa

# Then scale deployment
kubectl scale deployment llm-backend --replicas=3

# Or edit deployment spec
kubectl edit deployment llm-backend
```

---

### Scenario 2.3: Deployment Update Stuck

**Problem:** Deployment is paused and not updating.

```bash
$ kubectl rollout status deployment/llm-gateway
deployment "llm-gateway" is paused
```

**Debug Commands:**

```bash
# Check if deployment is paused
kubectl get deployment llm-gateway -o jsonpath='{.spec.paused}'

# Resume the deployment
kubectl rollout resume deployment/llm-gateway

# Watch the rollout
kubectl rollout status deployment/llm-gateway -w
```

---

## 3️⃣ Service & Networking Issues

### Scenario 3.1: Service Not Routing to Pods

**Problem:** Service exists but requests are not reaching pods.

```bash
$ curl http://gateway-service:8000/healthz
curl: (7) Failed to connect to gateway-service port 8000: Connection refused
```

**Debug Commands:**

```bash
# Check if service has endpoints
kubectl get endpoints gateway-service

# Check service definition
kubectl describe service gateway-service

# Check pod labels
kubectl get pods --show-labels

# Test from within cluster
kubectl run debug --rm -it --image=busybox:1.36 -- sh
# Inside the pod:
wget -O- http://gateway-service:8000/healthz
```

**Root Causes:**

1. **Label Selector Mismatch**
2. **Wrong Port Configuration**
3. **Pods Not Ready**

**Solution:**

❌ **Bad Example:** Label mismatch

```yaml
# Service
apiVersion: v1
kind: Service
metadata:
  name: gateway-service
spec:
  selector:
    app: gateway-api  # Wrong label!
  ports:
  - port: 8000
    targetPort: 8000

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
spec:
  selector:
    matchLabels:
      app: gateway  # Different label!
  template:
    metadata:
      labels:
        app: gateway
```

✅ **Good Example:** Matching labels

```yaml
# Service
apiVersion: v1
kind: Service
metadata:
  name: gateway-service
spec:
  selector:
    app: gateway  # Matches pod label
  ports:
  - name: http
    port: 8000
    targetPort: 8000
    protocol: TCP

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
spec:
  selector:
    matchLabels:
      app: gateway  # Same label
  template:
    metadata:
      labels:
        app: gateway  # Same label
    spec:
      containers:
      - name: gateway
        image: llm-gateway:v1
        ports:
        - containerPort: 8000  # Matches targetPort
```

**Commands to Fix:**

```bash
# Check endpoints
kubectl get endpoints gateway-service
# If <none>, labels don't match

# Fix labels on deployment
kubectl label pods -l app=gateway-api app=gateway --overwrite

# Or update the service selector
kubectl edit service gateway-service
```

---

### Scenario 3.2: DNS Resolution Failing

**Problem:** Pods cannot resolve service names.

```bash
# Inside a pod
$ nslookup backend-service
Server:    10.96.0.10
Address 1: 10.96.0.10

nslookup: can't resolve 'backend-service'
```

**Debug Commands:**

```bash
# Check DNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Test DNS resolution
kubectl run debug --rm -it --image=busybox:1.36 -- nslookup kubernetes.default

# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns
```

**Root Causes:**

1. **CoreDNS Pods Not Running**
2. **Wrong Service Name** (missing namespace)
3. **Network Plugin Issues**

**Solution:**

```bash
# Full service DNS name format:
# <service-name>.<namespace>.svc.cluster.local

# From same namespace:
curl http://backend-service:8001/healthz

# From different namespace:
curl http://backend-service.default.svc.cluster.local:8001/healthz
```

✅ **Good Python Code with Full DNS Names:**

```python
import os

# Get namespace from pod
namespace = os.getenv("POD_NAMESPACE", "default")

# Use full DNS name for cross-namespace communication
BACKEND_URL = f"http://backend-service.{namespace}.svc.cluster.local:8001"

# Or use short name if in same namespace
BACKEND_URL = "http://backend-service:8001"
```

---

### Scenario 3.3: Network Policy Blocking Traffic

**Problem:** Pods cannot communicate due to network policies.

```bash
$ kubectl exec gateway-pod -- curl http://backend-service:8001/healthz
curl: (28) Failed to connect to backend-service port 8001: Connection timed out
```

**Debug Commands:**

```bash
# Check network policies
kubectl get networkpolicies

# Describe network policy
kubectl describe networkpolicy deny-all

# Check pod labels
kubectl get pods --show-labels
```

**Root Causes:**

1. **Default Deny Policy**
2. **Missing Ingress/Egress Rules**

**Solution:**

✅ **Network Policy Allowing Specific Traffic:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gateway-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gateway
    ports:
    - protocol: TCP
      port: 8001
```

---

### Scenario 3.4: LoadBalancer Service Pending

**Problem:** LoadBalancer service stuck in Pending state.

```bash
$ kubectl get svc gateway-service
NAME              TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
gateway-service   LoadBalancer   10.96.100.200   <pending>     80:30080/TCP   5m
```

**Debug Commands:**

```bash
# Check service events
kubectl describe service gateway-service

# Check if cloud provider controller is running
kubectl get pods -n kube-system | grep cloud-controller
```

**Root Causes:**

1. **No Load Balancer Support** (local clusters like kind/minikube)
2. **Cloud Provider Not Configured**

**Solution:**

```bash
# For local development, use NodePort or Port-Forward
kubectl port-forward service/gateway-service 8000:8000

# Or change service type to NodePort
kubectl patch service gateway-service -p '{"spec":{"type":"NodePort"}}'

# For kind, use ingress instead
kubectl apply -f ingress.yaml
```

---

### Scenario 3.5: ClusterIP Not Accessible from Outside

**Problem:** Cannot access ClusterIP service from outside cluster.

**Root Cause:** ClusterIP is only accessible from within the cluster by design.

**Solution:**

```bash
# Option 1: Use kubectl port-forward
kubectl port-forward service/gateway-service 8000:8000

# Option 2: Create NodePort service
kubectl expose deployment llm-gateway --type=NodePort --port=8000

# Option 3: Create LoadBalancer (cloud environments)
kubectl expose deployment llm-gateway --type=LoadBalancer --port=8000

# Option 4: Use Ingress
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
spec:
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8000
EOF
```

---

## 4️⃣ ConfigMap & Secret Issues

### Scenario 4.1: ConfigMap Not Found

**Problem:** Pod fails to start because ConfigMap doesn't exist.

```bash
Events:
  Type     Reason     Age   From               Message
  ----     ------     ----  ----               -------
  Warning  Failed     10s   kubelet            Error: configmap "llm-config" not found
```

**Debug Commands:**

```bash
# List ConfigMaps
kubectl get configmaps

# Check if ConfigMap exists
kubectl get configmap llm-config

# Describe pod for detailed error
kubectl describe pod llm-gateway-xxx
```

**Solution:**

```bash
# Create ConfigMap from literals
kubectl create configmap llm-config   --from-literal=GATEWAY_PORT=8000   --from-literal=BACKEND_URL=http://backend-service:8001

# Or from file
kubectl create configmap llm-config --from-file=config.properties

# Or from YAML
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-config
data:
  GATEWAY_PORT: "8000"
  BACKEND_URL: "http://backend-service:8001"
  LOG_LEVEL: "INFO"
EOF
```

---

### Scenario 4.2: Secret Not Mounted Correctly

**Problem:** Secret exists but application can't read it.

**Debug Commands:**

```bash
# Check if secret exists
kubectl get secrets

# View secret (base64 encoded)
kubectl get secret db-credentials -o yaml

# Decode secret
kubectl get secret db-credentials -o jsonpath='{.data.password}' | base64 -d

# Check how it's mounted in pod
kubectl exec pod-name -- ls -la /etc/secrets/
kubectl exec pod-name -- cat /etc/secrets/password
```

**Solution:**

✅ **Create and Use Secrets:**

```bash
# Create secret
kubectl create secret generic db-credentials   --from-literal=username=admin   --from-literal=password=secretpass

# Or from files
kubectl create secret generic db-credentials   --from-file=username=./username.txt   --from-file=password=./password.txt
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1
    env:
    # Option 1: Mount as environment variable
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
    # Option 2: Mount as volume
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/secrets
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

**Read Secrets in Python:**

```python
import os

# From environment variable
db_password = os.getenv("DB_PASSWORD")

# From file
with open("/etc/secrets/password", "r") as f:
    db_password = f.read().strip()
```

---

### Scenario 4.3: ConfigMap Update Not Reflected

**Problem:** Updated ConfigMap but pods still use old values.

**Root Cause:** ConfigMaps and Secrets are cached and not automatically reloaded.

**Solution:**

```bash
# Option 1: Restart deployment to pick up changes
kubectl rollout restart deployment/llm-gateway

# Option 2: Use a reloader (e.g., Reloader by Stakater)
# Automatically restarts pods when ConfigMap/Secret changes

# Option 3: Use checksum annotation to force update
kubectl patch deployment llm-gateway -p   "{"spec":{"template":{"metadata":{"annotations":{"configmap-hash":"$(kubectl get configmap llm-config -o yaml | sha256sum | cut -d' ' -f1)"}}}}}"
```

---

## 5️⃣ Persistent Volume Issues

### Scenario 5.1: PVC Stuck in Pending

**Problem:** PersistentVolumeClaim is not bound to a PersistentVolume.

```bash
$ kubectl get pvc
NAME        STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
data-pvc    Pending                                      standard       5m
```

**Debug Commands:**

```bash
# Check PVC
kubectl describe pvc data-pvc

# Check available PVs
kubectl get pv

# Check StorageClass
kubectl get storageclass

# Check events
kubectl get events | grep -i persistentvolume
```

**Root Causes:**

1. **No Available PersistentVolume**
2. **No StorageClass** (for dynamic provisioning)
3. **Access Mode Mismatch**

**Solution:**

```bash
# Check if StorageClass exists
kubectl get storageclass

# Set default StorageClass
kubectl patch storageclass standard -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

✅ **Good PVC Definition:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: standard  # Use available StorageClass
  resources:
    requests:
      storage: 10Gi
```

---

### Scenario 5.2: Permission Denied on Volume Mount

**Problem:** Pod runs but application cannot write to mounted volume.

```bash
$ kubectl logs app-pod
Error: EACCES: permission denied, open '/data/output.txt'
```

**Debug Commands:**

```bash
# Check volume ownership
kubectl exec app-pod -- ls -ld /data

# Check which user the container runs as
kubectl exec app-pod -- id
```

**Solution:**

✅ **Fix Permissions with SecurityContext:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  securityContext:
    fsGroup: 1000  # Set group ownership of volume
    runAsUser: 1000  # Run container as this user
  containers:
  - name: app
    image: myapp:v1
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: data-pvc
```

---

### Scenario 5.3: Volume Already Mounted on Another Node

**Problem:** Pod cannot start because volume is attached to different node.

```
Warning  FailedAttachVolume  Multi-Attach error for volume "pvc-xxx" Volume is already exclusively attached to one node and can't be attached to another
```

**Root Cause:** Volume with ReadWriteOnce access mode can only be mounted on one node.

**Solution:**

```bash
# Option 1: Use ReadWriteMany if supported
kubectl edit pvc data-pvc
# Change accessModes to ReadWriteMany

# Option 2: Delete old pod first
kubectl delete pod old-pod --grace-period=0

# Option 3: Use local volumes with node affinity
```

✅ **Good PVC for Multi-Node Access:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-data-pvc
spec:
  accessModes:
  - ReadWriteMany  # Can be mounted on multiple nodes
  storageClassName: nfs  # Requires storage class that supports RWX
  resources:
    requests:
      storage: 50Gi
```

---

## 6️⃣ Resource Quota & Limit Issues

### Scenario 6.1: ResourceQuota Exceeded

**Problem:** Cannot create pods due to resource quota limits.

```bash
Error from server (Forbidden): error when creating "deployment.yaml": pods "app-pod" is forbidden: exceeded quota: compute-quota, requested: limits.memory=2Gi, used: limits.memory=8Gi, limited: limits.memory=10Gi
```

**Debug Commands:**

```bash
# Check ResourceQuota
kubectl get resourcequota

# Describe quota
kubectl describe resourcequota compute-quota

# Check current resource usage
kubectl top nodes
kubectl top pods
```

**Solution:**

```bash
# Increase quota (if you have permission)
kubectl edit resourcequota compute-quota

# Or delete old resources
kubectl delete pod old-pod

# Reduce resource requests in deployment
kubectl edit deployment app
```

---

### Scenario 6.2: LimitRange Blocking Pod Creation

**Problem:** Pod cannot be created due to LimitRange restrictions.

```
Error: Pod "app-pod" is forbidden: maximum memory usage per Container is 1Gi, but limit is 2Gi
```

**Debug Commands:**

```bash
# Check LimitRange
kubectl get limitrange

# Describe limit range
kubectl describe limitrange limits
```

**Solution:**

```yaml
# Update pod to comply with LimitRange
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
  - name: app
    image: myapp:v1
    resources:
      limits:
        memory: "1Gi"  # Within LimitRange
        cpu: "500m"
      requests:
        memory: "512Mi"
        cpu: "250m"
```

---

### Scenario 6.3: QoS Class Issues

**Problem:** Pods being evicted during resource pressure.

**Debug Commands:**

```bash
# Check QoS class of pod
kubectl get pod app-pod -o jsonpath='{.status.qosClass}'

# Check which pods get evicted first (BestEffort -> Burstable -> Guaranteed)
kubectl describe node worker-node | grep -A 5 "Non-terminated Pods"
```

**Solution:**

✅ **Guaranteed QoS (Highest Priority):**

```yaml
# Requests = Limits for both memory and CPU
apiVersion: v1
kind: Pod
metadata:
  name: critical-app
spec:
  containers:
  - name: app
    image: myapp:v1
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"
      limits:
        memory: "1Gi"  # Same as requests
        cpu: "500m"    # Same as requests
```

❌ **BestEffort QoS (Evicted First):**

```yaml
# No resources specified
apiVersion: v1
kind: Pod
metadata:
  name: non-critical-app
spec:
  containers:
  - name: app
    image: myapp:v1
    # No resources defined - will be evicted first
```

---

## 7️⃣ RBAC & Security Issues

### Scenario 7.1: Forbidden - Insufficient Permissions

**Problem:** Service account lacks permissions to perform operations.

```bash
$ kubectl logs myapp-pod
Error from server (Forbidden): pods is forbidden: User "system:serviceaccount:default:myapp" cannot list resource "pods" in API group "" in the namespace "default"
```

**Debug Commands:**

```bash
# Check service account
kubectl get serviceaccount

# Check role bindings
kubectl get rolebindings

# Check what service account can do
kubectl auth can-i --list --as=system:serviceaccount:default:myapp
```

**Solution:**

✅ **Create ServiceAccount with Proper RBAC:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: myapp-role
subjects:
- kind: ServiceAccount
  name: myapp-sa
  namespace: default

---
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  serviceAccountName: myapp-sa  # Use the service account
  containers:
  - name: app
    image: myapp:v1
```

---

### Scenario 7.2: Pod Security Policy Violations

**Problem:** Pod fails to start due to PodSecurityPolicy.

```
Error: pods "app" is forbidden: unable to validate against any pod security policy: [spec.securityContext.runAsUser: Invalid value: 0: running as root is not allowed]
```

**Solution:**

✅ **Run as Non-Root User:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: app
    image: myapp:v1
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

**Update Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Switch to non-root user
USER appuser

CMD ["python", "-m", "gateway_api.main"]
```

---

### Scenario 7.3: ImagePullPolicy Security Issue

**Problem:** Using images from untrusted registries.

**Solution:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  imagePullSecrets:
  - name: private-registry-secret
  containers:
  - name: app
    image: trusted-registry.company.com/myapp:v1.2.3  # Use specific version
    imagePullPolicy: Always  # Always verify image
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
```

---

## 8️⃣ Ingress Issues

### Scenario 8.1: Ingress Not Routing Traffic

**Problem:** Ingress exists but traffic not reaching services.

**Debug Commands:**

```bash
# Check ingress
kubectl get ingress

# Describe ingress for address
kubectl describe ingress gateway-ingress

# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx <ingress-controller-pod>

# Test from inside cluster
kubectl run debug --rm -it --image=curlimages/curl -- sh
curl -H "Host: gateway.example.com" http://<ingress-controller-service-ip>
```

**Root Causes:**

1. **Ingress Controller Not Installed**
2. **Wrong Host/Path Configuration**
3. **Backend Service Issues**

**Solution:**

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# For kind:
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

✅ **Good Ingress Configuration:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8000
  - host: backend.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8001
```

---

### Scenario 8.2: TLS/HTTPS Not Working

**Problem:** HTTPS not working with ingress.

**Solution:**

```bash
# Create TLS secret
kubectl create secret tls gateway-tls   --cert=path/to/tls.crt   --key=path/to/tls.key
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: gateway-ingress
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - gateway.example.com
    secretName: gateway-tls
  rules:
  - host: gateway.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8000
```

---

### Scenario 8.3: Path-Based Routing Issues

**Problem:** Different paths not routing correctly.

**Solution:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /gateway(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: gateway-service
            port:
              number: 8000
      - path: /backend(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8001
```

---

## 9️⃣ Node Issues

### Scenario 9.1: Node NotReady

**Problem:** Node is in NotReady state.

```bash
$ kubectl get nodes
NAME           STATUS     ROLES           AGE   VERSION
worker-node1   NotReady   <none>          5d    v1.28.0
```

**Debug Commands:**

```bash
# Check node status
kubectl describe node worker-node1

# Check node conditions
kubectl get node worker-node1 -o jsonpath='{.status.conditions[?(@.type=="Ready")]}'

# Check kubelet logs (SSH to node)
journalctl -u kubelet -f

# Check if disk/memory/PID pressure
kubectl get nodes -o json | jq '.items[] | {name:.metadata.name, conditions:.status.conditions}'
```

**Root Causes:**

1. **Kubelet Not Running**
2. **Network Plugin Issues**
3. **Resource Pressure**

**Solution:**

```bash
# Restart kubelet (on the node)
systemctl restart kubelet

# Check disk space
df -h

# Drain and uncordon node
kubectl drain worker-node1 --ignore-daemonsets
kubectl uncordon worker-node1
```

---

### Scenario 9.2: Pods Not Scheduling on Node

**Problem:** Pods avoid specific node.

**Debug Commands:**

```bash
# Check node taints
kubectl describe node worker-node1 | grep Taints

# Check pod tolerations
kubectl get pod app-pod -o jsonpath='{.spec.tolerations}'
```

**Solution:**

```bash
# Remove taint from node
kubectl taint nodes worker-node1 key:NoSchedule-

# Or add toleration to pod
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  tolerations:
  - key: "node.kubernetes.io/disk-pressure"
    operator: "Exists"
    effect: "NoSchedule"
  containers:
  - name: app
    image: myapp:v1
```

---

### Scenario 9.3: Node Resource Exhaustion

**Problem:** Node running out of resources.

**Debug Commands:**

```bash
# Check node resources
kubectl top node worker-node1

# Check resource allocation
kubectl describe node worker-node1 | grep -A 5 "Allocated resources"

# List pods on node
kubectl get pods --field-selector spec.nodeName=worker-node1 -o wide
```

**Solution:**

```bash
# Add more nodes to cluster

# Or evict low-priority pods
kubectl delete pod <low-priority-pod>

# Set resource limits on pods
kubectl set resources deployment myapp --limits=cpu=500m,memory=512Mi --requests=cpu=250m,memory=256Mi
```

---

## 🔟 StatefulSet Issues

### Scenario 10.1: StatefulSet Pod Not Starting in Order

**Problem:** StatefulSet pods not starting sequentially.

**Debug Commands:**

```bash
# Check StatefulSet status
kubectl get statefulset

# Check pods
kubectl get pods -l app=database

# Describe StatefulSet
kubectl describe statefulset database
```

**Root Cause:** Previous pod not ready.

**Solution:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: database
spec:
  serviceName: "database"
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: db
        image: postgres:15
        ports:
        - containerPort: 5432
        readinessProbe:  # Critical for sequential startup
          tcpSocket:
            port: 5432
          initialDelaySeconds: 10
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

---

### Scenario 10.2: PVC Not Created for StatefulSet

**Problem:** PersistentVolumeClaims not created for StatefulSet pods.

**Root Cause:** No StorageClass or volumeClaimTemplates misconfigured.

**Solution:**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: database
spec:
  serviceName: database
  replicas: 3
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: db
        image: postgres:15
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: standard  # Must exist
      resources:
        requests:
          storage: 10Gi
```

---

## 1️⃣1️⃣ Job & CronJob Issues

### Scenario 11.1: Job Not Completing

**Problem:** Job pods keep failing or running forever.

**Debug Commands:**

```bash
# Check job status
kubectl get jobs

# Check job pods
kubectl get pods -l job-name=my-job

# Check logs
kubectl logs -l job-name=my-job

# Describe job
kubectl describe job my-job
```

**Solution:**

✅ **Good Job Configuration:**

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-migration
spec:
  backoffLimit: 3  # Retry up to 3 times
  activeDeadlineSeconds: 600  # Timeout after 10 minutes
  template:
    spec:
      restartPolicy: OnFailure  # Required for Jobs
      containers:
      - name: migrate
        image: myapp:v1
        command: ["python", "migrate.py"]
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
```

---

### Scenario 11.2: CronJob Not Running

**Problem:** CronJob not creating jobs at scheduled time.

**Debug Commands:**

```bash
# Check CronJob
kubectl get cronjobs

# Check last schedule time
kubectl get cronjob remediation-cronjob -o jsonpath='{.status.lastScheduleTime}'

# Check if suspended
kubectl get cronjob remediation-cronjob -o jsonpath='{.spec.suspend}'

# Check recent jobs
kubectl get jobs --sort-by=.metadata.creationTimestamp
```

**Solution:**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: remediation-cronjob
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  concurrencyPolicy: Forbid  # Don't allow overlapping jobs
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: remediation
            image: remediation:v1
            command: ["python", "remediation.py"]
```

**Common Schedule Issues:**

```bash
# Wrong: "* * * * *" runs every minute
# Right: "0 2 * * *" runs at 2 AM daily

# Every 5 minutes: "*/5 * * * *"
# Every hour: "0 * * * *"
# Every day at midnight: "0 0 * * *"
# Every Monday at 9 AM: "0 9 * * 1"
```

---

## 1️⃣2️⃣ Debugging Toolkit & Best Practices

### Essential Debug Commands

```bash
# Get all resources in namespace
kubectl get all

# Get resources across all namespaces
kubectl get pods --all-namespaces

# Watch resources in real-time
kubectl get pods -w

# Get YAML definition of resource
kubectl get pod mypod -o yaml

# Get JSON for parsing
kubectl get pod mypod -o json | jq '.status.phase'

# Check resource usage
kubectl top pods
kubectl top nodes

# Get events sorted by time
kubectl get events --sort-by=.metadata.creationTimestamp

# Port forward for local testing
kubectl port-forward pod/mypod 8000:8000
kubectl port-forward service/myservice 8000:8000

# Logs with timestamp
kubectl logs mypod --timestamps

# Logs for previous container instance
kubectl logs mypod --previous

# Follow logs
kubectl logs -f mypod

# Multi-container pod logs
kubectl logs mypod -c container-name

# Execute commands in pod
kubectl exec -it mypod -- sh
kubectl exec mypod -- env

# Copy files to/from pod
kubectl cp mypod:/path/to/file ./local-file
kubectl cp ./local-file mypod:/path/to/file

# Debug with ephemeral container (K8s 1.23+)
kubectl debug mypod -it --image=busybox:1.36

# Create debug pod on same node
kubectl debug node/worker-node1 -it --image=ubuntu
```

### Quick Debugging Pod

```bash
# Run debug pod with networking tools
kubectl run debug --rm -it --image=nicolaka/netshoot -- bash

# Inside the pod:
# - curl, wget, nslookup, dig, ping, traceroute
# - netstat, ss, iftop, iperf
# - tcpdump, nmap
```

### Best Practices

1. **Always Set Resource Limits**

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

2. **Use Readiness and Liveness Probes**

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 10
```

3. **Use Labels Consistently**

```yaml
metadata:
  labels:
    app: myapp
    version: v1
    environment: production
```

4. **Enable Structured Logging**

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log_record)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger()
logger.addHandler(handler)
```

5. **Use ConfigMaps for Configuration**

```yaml
# Don't hardcode config in images
env:
- name: LOG_LEVEL
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: LOG_LEVEL
```

6. **Use Secrets for Sensitive Data**

```yaml
env:
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: api-secrets
      key: api-key
```

7. **Implement Graceful Shutdown**

```python
import signal
import sys

def signal_handler(sig, frame):
    logger.info("Shutting down gracefully...")
    # Close connections, save state, etc.
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

8. **Use Init Containers for Setup**

```yaml
initContainers:
- name: wait-for-db
  image: busybox:1.36
  command: ['sh', '-c', 'until nc -z database 5432; do sleep 2; done']
```

### Debugging Checklist

When troubleshooting Kubernetes issues, follow this checklist:

- [ ] Check pod status: `kubectl get pods`
- [ ] Describe pod: `kubectl describe pod <pod-name>`
- [ ] Check logs: `kubectl logs <pod-name>`
- [ ] Check previous logs if crashed: `kubectl logs <pod-name> --previous`
- [ ] Check events: `kubectl get events --sort-by=.metadata.creationTimestamp`
- [ ] Check service endpoints: `kubectl get endpoints <service-name>`
- [ ] Verify labels match: `kubectl get pods --show-labels`
- [ ] Check resource usage: `kubectl top pods`
- [ ] Check node status: `kubectl get nodes`
- [ ] Test connectivity: `kubectl exec <pod> -- curl <service>`
- [ ] Check RBAC permissions: `kubectl auth can-i <verb> <resource>`
- [ ] Review resource definitions: `kubectl get <resource> <name> -o yaml`

### Common Error Codes

- **Exit Code 0**: Success
- **Exit Code 1**: Application error
- **Exit Code 137**: OOMKilled (128 + 9)
- **Exit Code 139**: Segmentation fault
- **Exit Code 143**: SIGTERM (128 + 15)

---

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Kubernetes Debugging Guide](https://kubernetes.io/docs/tasks/debug/)
- [CNCF Landscape](https://landscape.cncf.io/)

---

**Happy Debugging! 🐛🔧**
