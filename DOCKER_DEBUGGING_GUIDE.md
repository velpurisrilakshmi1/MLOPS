# 🐛 Docker Debugging Guide

A comprehensive guide to troubleshoot and debug Docker containers in development and production environments.

## 📑 Table of Contents

1. [Build-Time Issues](#1-build-time-issues)
2. [Runtime Issues](#2-runtime-issues)
3. [Networking Problems](#3-networking-problems)
4. [Storage & Volume Issues](#4-storage--volume-issues)
5. [Performance Problems](#5-performance-problems)
6. [Multi-Container Issues (Docker Compose)](#6-multi-container-issues-docker-compose)
7. [Security & Permissions](#7-security--permissions)
8. [Resource Exhaustion](#8-resource-exhaustion)
9. [Image Issues](#9-image-issues)
10. [Docker Daemon Problems](#10-docker-daemon-problems)
11. [Universal Debugging Toolkit](#11-universal-debugging-toolkit)
12. [Debugging Checklist](#12-debugging-checklist)
13. [Quick Reference Table](#13-quick-reference-table)

---

## 1️⃣ Build-Time Issues

### Scenario 1.1: Build Context Too Large

**Problem:** Build is extremely slow or fails with "context too large" error.

**Debug Commands:**
```bash
# Check build context size
docker build --no-cache -t myapp . 2>&1 | grep "Sending build context"

# List files in build context
tar -czh . | wc -c
```

**Root Cause:** Sending unnecessary files (node_modules, .git, logs) to Docker daemon.

**Solution:**

❌ **Bad Example:** No `.dockerignore` file
```dockerfile
FROM node:16
WORKDIR /app
COPY . .  # Copies everything including node_modules, .git
RUN npm install
```

✅ **Good Example:** Proper `.dockerignore`
```
# .dockerignore
node_modules
npm-debug.log
.git
.gitignore
.env
*.md
.vscode
dist
coverage
*.log
.DS_Store
```

```dockerfile
FROM node:16
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
```

---

### Scenario 1.2: Layer Caching Not Working

**Problem:** Every build takes full time even when nothing changed.

**Debug Commands:**
```bash
# Build with cache info
docker build --progress=plain --no-cache -t myapp .

# Check image history
docker history myapp
```

**Root Cause:** Invalidating cache early by copying files that change frequently.

**Solution:**

❌ **Bad Example:** Copying all files before installing dependencies
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .  # Changes in any file invalidates all subsequent layers
RUN pip install -r requirements.txt
```

✅ **Good Example:** Copy dependencies first, then source code
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt  # Cached unless requirements.txt changes
COPY . .
```

---

### Scenario 1.3: Package Installation Fails

**Problem:** `pip install` or `npm install` fails during build.

**Debug Commands:**
```bash
# Build with verbose output
docker build --progress=plain -t myapp .

# Test package installation in container
docker run -it python:3.9 bash
pip install <package-name> -vvv
```

**Root Cause:** Missing system dependencies, network issues, or incompatible versions.

**Solution:**

❌ **Bad Example:** Missing system dependencies
```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # Fails if requires gcc, etc.
```

✅ **Good Example:** Install system dependencies first
```dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

For npm issues:
```dockerfile
FROM node:16
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production  # Use 'ci' for reproducible builds
COPY . .
```

---

### Scenario 1.4: Permission Denied During Build

**Problem:** Build fails with "permission denied" error.

**Debug Commands:**
```bash
# Check file permissions in context
ls -la

# Check if files are executable
stat Dockerfile
```

**Root Cause:** Files don't have proper permissions or trying to write to restricted directories.

**Solution:**

❌ **Bad Example:** Writing to restricted directory
```dockerfile
FROM python:3.9
RUN mkdir /protected && \
    echo "data" > /protected/file.txt  # May fail
```

✅ **Good Example:** Create user and set permissions
```dockerfile
FROM python:3.9
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
RUN chown -R appuser:appuser /app
USER appuser
COPY --chown=appuser:appuser . .
```

---

### Scenario 1.5: Multi-Stage Build Issues

**Problem:** `COPY --from` fails with "invalid from flag value" error.

**Debug Commands:**
```bash
# Build specific stage only
docker build --target builder -t myapp-builder .

# Inspect intermediate stages
docker build --target builder -t temp . && docker run temp ls /app
```

**Root Cause:** Wrong stage name or path in `COPY --from`.

**Solution:**

❌ **Bad Example:** Wrong stage name or missing files
```dockerfile
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html  # Wrong name: 'build' vs 'builder'
```

✅ **Good Example:** Correct stage name and path
```dockerfile
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 2️⃣ Runtime Issues

### Scenario 2.1: Container Exits Immediately

**Problem:** Container starts but exits immediately with no obvious error.

**Debug Commands:**
```bash
# Check container logs
docker logs <container-id>

# Check exit code
docker ps -a
docker inspect <container-id> | grep -A 5 "State"

# Run container interactively
docker run -it myapp /bin/sh

# Check last exit code
docker inspect <container-id> --format='{{.State.ExitCode}}'
```

**Exit Code Reference:**
- `0`: Success
- `1`: Application error
- `137`: Killed (OOM - Out of Memory)
- `139`: Segmentation fault
- `143`: Terminated (SIGTERM)

**Root Cause:** No foreground process or command fails immediately.

**Solution:**

❌ **Bad Example:** Background process or script exits
```dockerfile
FROM ubuntu:20.04
CMD service nginx start  # Starts in background, container exits
```

✅ **Good Example:** Run process in foreground
```dockerfile
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y nginx
CMD ["nginx", "-g", "daemon off;"]  # Foreground process
```

For Python apps:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
CMD ["python", "-u", "app.py"]  # -u for unbuffered output
```

---

### Scenario 2.2: Application Not Responding

**Problem:** Container is running but application doesn't respond.

**Debug Commands:**
```bash
# Check if process is running
docker exec <container-id> ps aux

# Check network ports
docker exec <container-id> netstat -tlnp
# Or if netstat not available
docker exec <container-id> ss -tlnp

# Check application logs
docker logs -f <container-id>

# Test from inside container
docker exec <container-id> curl localhost:8080
```

**Root Cause:** Application crashed, listening on wrong interface, or port not exposed.

**Solution:**

❌ **Bad Example:** Listening on localhost only
```python
# app.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World!"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)  # Only accessible from inside container
```

✅ **Good Example:** Listen on all interfaces
```python
# app.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello World!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Accessible from outside
```

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

---

### Scenario 2.3: Environment Variables Not Working

**Problem:** Application can't read environment variables.

**Debug Commands:**
```bash
# Check environment variables in running container
docker exec <container-id> env

# Inspect container environment
docker inspect <container-id> | grep -A 20 "Env"
```

**Root Cause:** Using `ARG` instead of `ENV`, or not passing variables correctly.

**Solution:**

❌ **Bad Example:** ARG is only available at build time
```dockerfile
FROM python:3.9
ARG DATABASE_URL=postgres://localhost/db  # Not available at runtime
COPY . .
CMD ["python", "app.py"]
```

✅ **Good Example:** Use ENV for runtime variables
```dockerfile
FROM python:3.9
ENV DATABASE_URL=postgres://localhost/db
ENV PYTHONUNBUFFERED=1
COPY . .
CMD ["python", "app.py"]
```

Run with environment variables:
```bash
# Pass env var at runtime
docker run -e DATABASE_URL=postgres://prod/db myapp

# Or use env file
docker run --env-file .env myapp
```

```bash
# .env file
DATABASE_URL=postgres://prod/db
SECRET_KEY=mysecret123
DEBUG=false
```

---

### Scenario 2.4: File Not Found Errors

**Problem:** Application can't find required files.

**Debug Commands:**
```bash
# Check working directory
docker exec <container-id> pwd

# List files in container
docker exec <container-id> ls -la /app

# Check specific file
docker exec <container-id> cat /app/config.json
```

**Root Cause:** Incorrect `WORKDIR`, wrong `COPY` path, or missing files.

**Solution:**

❌ **Bad Example:** Inconsistent WORKDIR usage
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
# WORKDIR changed implicitly
COPY app.py /code/  # File copied to different location
CMD ["python", "app.py"]  # Looks in /app, but file is in /code
```

✅ **Good Example:** Consistent paths
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
COPY config/ ./config/
CMD ["python", "app.py"]
```

---

### Scenario 2.5: Permission Denied at Runtime

**Problem:** Application can't write to files or directories.

**Debug Commands:**
```bash
# Check file ownership
docker exec <container-id> ls -la /app

# Check current user
docker exec <container-id> whoami
docker exec <container-id> id

# Try to write
docker exec <container-id> touch /app/test.txt
```

**Root Cause:** Files owned by root, but app runs as non-root user.

**Solution:**

❌ **Bad Example:** Files owned by root, app runs as user
```dockerfile
FROM python:3.9
COPY . /app
RUN useradd -m appuser
USER appuser
WORKDIR /app
CMD ["python", "app.py"]  # Can't write to /app (owned by root)
```

✅ **Good Example:** Fix ownership
```dockerfile
FROM python:3.9
RUN useradd -m appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
RUN chmod +x entrypoint.sh
USER appuser
CMD ["python", "app.py"]
```

Or fix at runtime:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser
CMD ["python", "app.py"]
```

---

## 3️⃣ Networking Problems

### Scenario 3.1: Container Can't Reach External Network

**Problem:** Container can't access internet or external APIs.

**Debug Commands:**
```bash
# Test DNS resolution
docker exec <container-id> nslookup google.com
docker exec <container-id> cat /etc/resolv.conf

# Test connectivity
docker exec <container-id> ping -c 3 8.8.8.8
docker exec <container-id> curl -v https://api.example.com

# Check Docker network
docker network inspect bridge
```

**Root Cause:** DNS issues, firewall, or proxy configuration.

**Solution:**

✅ **Solution 1:** Configure DNS servers
```bash
# Run with custom DNS
docker run --dns 8.8.8.8 --dns 8.8.4.4 myapp

# Or in docker-compose.yml
services:
  app:
    image: myapp
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

✅ **Solution 2:** Configure proxy
```dockerfile
FROM python:3.9
ENV HTTP_PROXY=http://proxy.example.com:8080
ENV HTTPS_PROXY=http://proxy.example.com:8080
ENV NO_PROXY=localhost,127.0.0.1
COPY . .
CMD ["python", "app.py"]
```

---

### Scenario 3.2: Container-to-Container Communication Fails

**Problem:** Containers can't communicate with each other.

**Debug Commands:**
```bash
# List networks
docker network ls

# Inspect network
docker network inspect <network-name>

# Test connectivity between containers
docker exec container1 ping container2
docker exec container1 curl http://container2:8080
```

**Root Cause:** Containers on different networks or wrong hostname.

**Solution:**

❌ **Bad Example:** Containers on default bridge network
```bash
docker run -d --name app1 myapp1
docker run -d --name app2 myapp2
# Can't communicate by name, only by IP
```

✅ **Good Example:** Create custom network
```bash
# Create network
docker network create mynetwork

# Run containers on same network
docker run -d --name app1 --network mynetwork myapp1
docker run -d --name app2 --network mynetwork myapp2

# Now app1 can reach app2 by name
docker exec app1 curl http://app2:8080
```

Using Docker Compose:
```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    networks:
      - mynetwork
    
  backend:
    build: ./backend
    networks:
      - mynetwork
    environment:
      - DATABASE_URL=postgres://db:5432/mydb
    
  db:
    image: postgres:13
    networks:
      - mynetwork

networks:
  mynetwork:
    driver: bridge
```

---

### Scenario 3.3: Port Already in Use

**Problem:** "port is already allocated" error when starting container.

**Debug Commands:**
```bash
# Check which process is using the port (Linux/Mac)
lsof -i :8080
netstat -tlnp | grep 8080

# Check which process is using the port (Windows)
netstat -ano | findstr :8080

# List Docker containers using the port
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

**Root Cause:** Another process or container already using the port.

**Solution:**

✅ **Solution 1:** Stop conflicting container
```bash
# Find container using port
docker ps | grep 8080

# Stop it
docker stop <container-id>
```

✅ **Solution 2:** Use different host port
```bash
# Map to different host port
docker run -p 8081:8080 myapp  # Host:Container

# Or let Docker choose random port
docker run -p 8080 myapp
docker port <container-id>  # See which port was assigned
```

✅ **Solution 3:** Kill process using the port
```bash
# Linux/Mac
sudo kill -9 $(lsof -ti:8080)

# Windows (run as admin)
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

---

### Scenario 3.4: Cannot Access Container from Host

**Problem:** Can't access container service from host browser.

**Debug Commands:**
```bash
# Check port mapping
docker port <container-id>

# Check if container is listening on correct interface
docker exec <container-id> netstat -tlnp

# Test from inside container
docker exec <container-id> curl localhost:8080

# Check firewall
sudo iptables -L -n
```

**Root Cause:** Application binding to localhost (127.0.0.1) instead of 0.0.0.0.

**Solution:**

❌ **Bad Example:** Binding to localhost only
```javascript
// server.js
const express = require('express');
const app = express();

app.get('/', (req, res) => res.send('Hello'));
app.listen(3000, '127.0.0.1');  // Only accessible inside container
```

✅ **Good Example:** Bind to all interfaces
```javascript
// server.js
const express = require('express');
const app = express();

app.get('/', (req, res) => res.send('Hello'));
app.listen(3000, '0.0.0.0');  // Accessible from host
console.log('Server running on port 3000');
```

```dockerfile
FROM node:16
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

Run container:
```bash
docker run -p 3000:3000 myapp
# Now accessible at http://localhost:3000
```

---

## 4️⃣ Storage & Volume Issues

### Scenario 4.1: Data Lost After Container Restart

**Problem:** Data disappears when container is restarted or recreated.

**Debug Commands:**
```bash
# Check volumes
docker volume ls

# Inspect container volumes
docker inspect <container-id> | grep -A 10 "Mounts"

# Check data persistence
docker exec <container-id> ls -la /data
```

**Root Cause:** Data stored in container filesystem instead of volume.

**Solution:**

❌ **Bad Example:** No volume, data stored in container
```bash
docker run -d --name postgres postgres:13
# Data lost when container is removed
```

✅ **Good Example:** Use named volume
```bash
# Create named volume
docker volume create pgdata

# Run with volume
docker run -d --name postgres \
  -v pgdata:/var/lib/postgresql/data \
  postgres:13

# Data persists even if container is removed
docker stop postgres
docker rm postgres
docker run -d --name postgres \
  -v pgdata:/var/lib/postgresql/data \
  postgres:13
# Data still there!
```

Using Docker Compose:
```yaml
version: '3.8'
services:
  db:
    image: postgres:13
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: example

volumes:
  pgdata:
```

---

### Scenario 4.2: Volume Mount Not Working

**Problem:** Files not showing up in container or host.

**Debug Commands:**
```bash
# Check mount path
docker inspect <container-id> | grep -A 20 "Mounts"

# List files in container
docker exec <container-id> ls -la /app

# Check if path exists on host
ls -la /host/path
```

**Root Cause:** Relative paths, wrong paths, or SELinux issues.

**Solution:**

❌ **Bad Example:** Using relative path
```bash
# Relative path - may not work as expected
docker run -v ./data:/app/data myapp
```

✅ **Good Example:** Use absolute paths
```bash
# Absolute path
docker run -v /home/user/data:/app/data myapp

# Or use $PWD for current directory
docker run -v $PWD/data:/app/data myapp

# For SELinux systems (Fedora, RHEL, CentOS)
docker run -v /home/user/data:/app/data:Z myapp
```

Docker Compose:
```yaml
version: '3.8'
services:
  app:
    build: .
    volumes:
      - ./data:/app/data  # Relative to compose file
      - /absolute/path:/app/config  # Absolute path
```

---

### Scenario 4.3: Permission Denied on Volume

**Problem:** Application can't read/write to mounted volume.

**Debug Commands:**
```bash
# Check ownership on host
ls -la /host/data

# Check ownership in container
docker exec <container-id> ls -la /app/data

# Check user in container
docker exec <container-id> id
```

**Root Cause:** UID/GID mismatch between host and container.

**Solution:**

❌ **Bad Example:** Root owns files, app runs as user
```bash
# Host
sudo mkdir /data
sudo chown root:root /data
ls -la /data  # drwxr-xr-x root root

# Container runs as user 1000
docker run -u 1000 -v /data:/app/data myapp
# Permission denied!
```

✅ **Good Example:** Match UID/GID
```bash
# Check your user ID on host
id -u  # e.g., 1000
id -g  # e.g., 1000

# Create directory with correct ownership
mkdir -p /host/data
chown 1000:1000 /host/data

# Run container with matching user
docker run -u 1000:1000 -v /host/data:/app/data myapp
```

Or fix in Dockerfile:
```dockerfile
FROM python:3.9
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} appuser && \
    useradd -u ${UID} -g appuser appuser
USER appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
CMD ["python", "app.py"]
```

Build and run:
```bash
# Build with your UID/GID
docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) -t myapp .

# Run with volume
docker run -v $PWD/data:/app/data myapp
```

---

### Scenario 4.4: Disk Space Full

**Problem:** "no space left on device" error.

**Debug Commands:**
```bash
# Check Docker disk usage
docker system df

# Detailed view
docker system df -v

# Check host disk space
df -h

# Check specific paths
du -sh /var/lib/docker/*
```

**Root Cause:** Too many containers, images, volumes, or build cache.

**Solution:**

✅ **Clean up Docker resources:**

```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove unused networks
docker network prune -f

# Remove build cache
docker builder prune -a -f

# Remove everything (careful!)
docker system prune -a --volumes -f
```

**Automate cleanup:**
```bash
# Create cleanup script
cat > docker-cleanup.sh << 'EOF'
#!/bin/bash
echo "Removing stopped containers..."
docker container prune -f

echo "Removing dangling images..."
docker image prune -f

echo "Removing unused volumes..."
docker volume prune -f

echo "Disk usage:"
docker system df
EOF

chmod +x docker-cleanup.sh

# Run weekly via cron
crontab -e
# Add: 0 2 * * 0 /path/to/docker-cleanup.sh
```

---

## 5️⃣ Performance Problems

### Scenario 5.1: Container Using Too Much CPU

**Problem:** Container consuming 100% CPU, slowing down host.

**Debug Commands:**
```bash
# Monitor resource usage
docker stats

# Check processes in container
docker top <container-id>

# Detailed stats
docker stats --no-stream <container-id>
```

**Root Cause:** No CPU limits set or application bug.

**Solution:**

❌ **Bad Example:** No resource limits
```bash
docker run -d myapp
# Can use all available CPU
```

✅ **Good Example:** Set CPU limits
```bash
# Limit to 1 CPU core
docker run -d --cpus="1.0" myapp

# Limit to 50% of one core
docker run -d --cpus="0.5" myapp

# Set CPU shares (relative weight)
docker run -d --cpu-shares=512 myapp
```

Docker Compose:
```yaml
version: '3.8'
services:
  app:
    build: .
    deploy:
      resources:
        limits:
          cpus: '1.0'
        reservations:
          cpus: '0.5'
```

---

### Scenario 5.2: Out of Memory (OOM)

**Problem:** Container killed with exit code 137.

**Debug Commands:**
```bash
# Check container exit code
docker inspect <container-id> --format='{{.State.ExitCode}}'

# Check OOM in logs
docker logs <container-id> | grep -i "killed\|oom"

# Monitor memory usage
docker stats --no-stream <container-id>

# Check dmesg for OOM killer
dmesg | grep -i "killed process"
```

**Exit Code 137** = Container killed by OOM (Out of Memory) killer

**Root Cause:** Memory leak or insufficient memory limit.

**Solution:**

❌ **Bad Example:** No memory limits
```bash
docker run -d myapp
# Can use all host memory
```

✅ **Good Example:** Set memory limits
```bash
# Limit to 512MB
docker run -d -m 512m myapp

# Set memory + swap limit
docker run -d -m 512m --memory-swap 1g myapp

# Prevent OOM killer (container will hang instead)
docker run -d -m 512m --oom-kill-disable myapp
```

Docker Compose:
```yaml
version: '3.8'
services:
  app:
    build: .
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

Application-level fix (Python example):
```python
# app.py
import gc
import psutil

def check_memory():
    process = psutil.Process()
    mem_mb = process.memory_info().rss / 1024 / 1024
    if mem_mb > 400:  # 400MB threshold
        gc.collect()  # Force garbage collection
        print(f"Memory usage: {mem_mb}MB - triggered GC")

# Call periodically in your app
```

---

### Scenario 5.3: Slow Container Startup

**Problem:** Container takes too long to start and be ready.

**Debug Commands:**
```bash
# Time the startup
time docker run --rm myapp echo "ready"

# Check what's happening during startup
docker run --rm myapp sh -c "set -x; exec ./entrypoint.sh"

# Profile dockerfile build
docker build --progress=plain -t myapp .
```

**Root Cause:** Large image, slow initialization, or loading all data at startup.

**Solution:**

❌ **Bad Example:** Load everything at startup
```python
# app.py
import pandas as pd

# Load huge dataset at startup
df = pd.read_csv('large_dataset.csv')  # 5GB file!

def process_data():
    return df.head()

if __name__ == '__main__':
    app.run()
```

✅ **Good Example:** Lazy loading
```python
# app.py
import pandas as pd

df = None

def get_data():
    global df
    if df is None:
        df = pd.read_csv('large_dataset.csv')  # Load on first use
    return df

def process_data():
    data = get_data()
    return data.head()

if __name__ == '__main__':
    app.run()  # Starts quickly
```

Use smaller base images:
```dockerfile
# Instead of
FROM python:3.9  # ~900MB

# Use
FROM python:3.9-slim  # ~150MB

# Or
FROM python:3.9-alpine  # ~50MB
```

Multi-stage build:
```dockerfile
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Runtime stage - much smaller
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/index.js"]
```

---

## 6️⃣ Multi-Container Issues (Docker Compose)

### Scenario 6.1: Services Start in Wrong Order

**Problem:** App tries to connect to database before it's ready.

**Debug Commands:**
```bash
# Check service startup order
docker-compose logs

# Check service status
docker-compose ps

# Check service dependencies
docker-compose config
```

**Root Cause:** `depends_on` doesn't wait for service to be ready, only started.

**Solution:**

❌ **Bad Example:** Basic depends_on (doesn't wait for ready state)
```yaml
version: '3.8'
services:
  app:
    build: .
    depends_on:
      - db  # Only waits for container to start, not be ready
    environment:
      - DATABASE_URL=postgres://db:5432/mydb
  
  db:
    image: postgres:13
```

✅ **Good Example:** Use healthcheck with depends_on
```yaml
version: '3.8'
services:
  app:
    build: .
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgres://db:5432/mydb
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
```

Or use wait script in application:
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Install wait-for-it script
ADD https://github.com/vishnubob/wait-for-it/raw/master/wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

CMD ["/wait-for-it.sh", "db:5432", "--", "python", "app.py"]
```

---

### Scenario 6.2: Services Can't Communicate

**Problem:** Service can't reach another service by name.

**Debug Commands:**
```bash
# Check networks
docker-compose ps
docker network ls

# Test connectivity
docker-compose exec app ping db
docker-compose exec app curl http://api:8080

# Check DNS resolution
docker-compose exec app nslookup db
```

**Root Cause:** Services on different networks or wrong service name.

**Solution:**

❌ **Bad Example:** Using localhost or IP addresses
```yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - API_URL=http://localhost:8080  # Wrong!
  
  api:
    build: ./api
    ports:
      - "8080:8080"
```

✅ **Good Example:** Use service names
```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    environment:
      - API_URL=http://backend:8080  # Use service name
    networks:
      - mynetwork
  
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgres://db:5432/mydb
    networks:
      - mynetwork
  
  db:
    image: postgres:13
    networks:
      - mynetwork

networks:
  mynetwork:
```

---

### Scenario 6.3: Environment Variables Not Working

**Problem:** Services can't read environment variables from `.env` file.

**Debug Commands:**
```bash
# Check environment in service
docker-compose exec app env

# Validate compose file
docker-compose config

# Check .env file
cat .env
```

**Root Cause:** Wrong `.env` file location or syntax.

**Solution:**

❌ **Bad Example:** Wrong .env usage
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    env_file: .env  # This passes .env contents to container
    environment:
      - NODE_ENV=production  # This overrides .env
```

✅ **Good Example:** Proper .env usage
```bash
# .env file (in same directory as docker-compose.yml)
POSTGRES_PASSWORD=secretpass
DATABASE_NAME=mydb
API_KEY=abc123
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgres://db:5432/${DATABASE_NAME}
      - API_KEY=${API_KEY}
    env_file:
      - .env
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${DATABASE_NAME}
```

Run compose:
```bash
# Verify variables are loaded
docker-compose config

# Start services
docker-compose up -d
```

---

## 7️⃣ Security & Permissions

### Scenario 7.1: Cannot Run Privileged Operation

**Problem:** Operation requires capabilities that container doesn't have.

**Debug Commands:**
```bash
# Check capabilities
docker exec <container-id> capsh --print

# Try to run operation
docker exec <container-id> tcpdump -i eth0
# Error: permission denied
```

**Root Cause:** Container runs with restricted capabilities by default.

**Solution:**

❌ **Bad Example:** Run as root with full privileges
```bash
docker run --privileged myapp  # Security risk!
```

✅ **Good Example:** Add only required capabilities
```bash
# Add specific capability
docker run --cap-add=NET_ADMIN myapp

# Multiple capabilities
docker run --cap-add=NET_ADMIN --cap-add=SYS_TIME myapp

# For network debugging
docker run --cap-add=NET_ADMIN --cap-add=NET_RAW myapp
```

Docker Compose:
```yaml
version: '3.8'
services:
  app:
    build: .
    cap_add:
      - NET_ADMIN
      - SYS_TIME
```

Common capabilities:
- `NET_ADMIN`: Network configuration
- `NET_RAW`: Raw sockets
- `SYS_TIME`: Change system time
- `SYS_ADMIN`: Mount filesystems (avoid if possible)

---

### Scenario 7.2: Secret Management

**Problem:** Secrets exposed in environment variables or image layers.

**Debug Commands:**
```bash
# Check environment variables (bad!)
docker inspect <container-id> | grep -i pass

# Check image history
docker history myapp
```

**Root Cause:** Storing secrets in ENV, Dockerfile, or committing to image.

**Solution:**

❌ **Bad Example:** Secrets in Dockerfile or ENV
```dockerfile
FROM python:3.9
ENV API_KEY=abc123secret  # Visible in image!
ENV DATABASE_PASSWORD=mysecret  # Anyone can see this
COPY . .
CMD ["python", "app.py"]
```

✅ **Good Example 1:** Use Docker secrets (Swarm)
```bash
# Create secret
echo "mysecretpassword" | docker secret create db_password -

# Use in service
docker service create \
  --name myapp \
  --secret db_password \
  myapp

# Read in application from /run/secrets/db_password
```

✅ **Good Example 2:** Use secret files with bind mounts
```bash
# Store secrets in files (not in repo!)
echo "mysecret" > /secure/api_key.txt
chmod 600 /secure/api_key.txt

# Mount as read-only
docker run -v /secure/api_key.txt:/run/secrets/api_key:ro myapp
```

```python
# app.py - read secret from file
def get_secret(name):
    with open(f'/run/secrets/{name}', 'r') as f:
        return f.read().strip()

api_key = get_secret('api_key')
```

✅ **Good Example 3:** Use .env file (keep out of git!)
```bash
# .env (add to .gitignore!)
API_KEY=abc123secret
DATABASE_PASSWORD=mysecret
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    env_file: .env
```

---

## 8️⃣ Resource Exhaustion

### Scenario 8.1: Too Many Containers

**Problem:** System slowing down, can't create new containers.

**Debug Commands:**
```bash
# List all containers (including stopped)
docker ps -a

# Count containers
docker ps -a | wc -l

# Check system resources
docker system df
```

**Root Cause:** Not removing stopped containers.

**Solution:**

```bash
# Remove all stopped containers
docker container prune -f

# Remove specific stopped containers
docker rm $(docker ps -a -q -f status=exited)

# Auto-remove container when it exits
docker run --rm myapp

# Remove after specific time
docker run --rm -d myapp
```

Docker Compose:
```yaml
version: '3.8'
services:
  app:
    build: .
    restart: unless-stopped  # Don't create new containers unnecessarily
```

---

### Scenario 8.2: Too Many Images

**Problem:** Disk space exhausted by old Docker images.

**Debug Commands:**
```bash
# List all images
docker images

# Show disk usage
docker system df

# Find dangling images
docker images -f "dangling=true"
```

**Root Cause:** Old images accumulating from builds.

**Solution:**

```bash
# Remove dangling images (untagged)
docker image prune -f

# Remove all unused images
docker image prune -a -f

# Remove specific image
docker rmi <image-id>

# Remove images older than 24h
docker image prune -a --filter "until=24h"

# Keep only latest 3 images
docker images | grep myapp | tail -n +4 | awk '{print $3}' | xargs docker rmi
```

Automated cleanup script:
```bash
#!/bin/bash
# cleanup.sh
echo "Cleaning Docker resources..."
docker container prune -f
docker image prune -a -f --filter "until=168h"  # 1 week
docker volume prune -f
docker system df
```

---

## 9️⃣ Image Issues

### Scenario 9.1: Image Too Large

**Problem:** Image is several GB, slow to build and deploy.

**Debug Commands:**
```bash
# Check image size
docker images myapp

# Check layer sizes
docker history myapp

# Detailed layer inspection
docker history --no-trunc myapp
```

**Root Cause:** Using large base image or not cleaning up in same layer.

**Solution:**

❌ **Bad Example:** Large base image, not cleaning up
```dockerfile
FROM ubuntu:20.04
RUN apt-get update
RUN apt-get install -y python3 python3-pip curl git
RUN pip3 install flask requests pandas numpy
COPY . /app
WORKDIR /app
CMD ["python3", "app.py"]
# Result: ~1.5GB
```

✅ **Good Example:** Slim base image, multi-stage build
```dockerfile
# Build stage
FROM python:3.9 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
# Result: ~200MB
```

✅ **Good Example:** Alpine-based (smallest)
```dockerfile
FROM python:3.9-alpine
RUN apk add --no-cache gcc musl-dev
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
# Result: ~100MB
```

Clean up in same layer:
```dockerfile
FROM ubuntu:20.04
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# All in one layer, removes cache
```

---

### Scenario 9.2: Cannot Push/Pull Image

**Problem:** Authentication failed when pushing/pulling from registry.

**Debug Commands:**
```bash
# Test registry connection
curl -v https://registry.hub.docker.com/v2/

# Check logged in registries
cat ~/.docker/config.json

# Try manual login
docker login
```

**Root Cause:** Not logged in or wrong credentials.

**Solution:**

```bash
# Login to Docker Hub
docker login
# Enter username and password

# Login to private registry
docker login registry.example.com
# Enter username and password

# Login with token
echo $TOKEN | docker login -u username --password-stdin

# Tag image correctly
docker tag myapp:latest username/myapp:latest

# Push image
docker push username/myapp:latest

# Pull image
docker pull username/myapp:latest
```

For CI/CD (GitHub Actions example):
```yaml
- name: Login to Docker Hub
  uses: docker/login-action@v2
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}

- name: Build and push
  run: |
    docker build -t username/myapp:latest .
    docker push username/myapp:latest
```

---

## 🔟 Docker Daemon Problems

### Scenario 10.1: Docker Daemon Not Running

**Problem:** "Cannot connect to Docker daemon" error.

**Debug Commands:**
```bash
# Check daemon status
sudo systemctl status docker

# Check if docker process is running
ps aux | grep docker

# Check docker socket
ls -la /var/run/docker.sock
```

**Root Cause:** Docker daemon not started or crashed.

**Solution:**

```bash
# Start Docker daemon (Linux)
sudo systemctl start docker

# Enable auto-start on boot
sudo systemctl enable docker

# Check status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check logs
sudo journalctl -u docker.service -f
```

For Docker Desktop:
```bash
# macOS
open -a Docker

# Windows
# Start Docker Desktop from Start menu
```

Fix permissions (if needed):
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again, or use
newgrp docker

# Verify
docker ps
```

---

### Scenario 10.2: Docker Commands Hang

**Problem:** Docker commands hang indefinitely.

**Debug Commands:**
```bash
# Check daemon responsiveness
docker info

# Check daemon logs
sudo journalctl -u docker.service --no-pager

# Check system resources
top
df -h
```

**Root Cause:** Daemon deadlock, disk full, or resource exhaustion.

**Solution:**

```bash
# Restart Docker daemon
sudo systemctl restart docker

# If that doesn't work, kill and restart
sudo pkill dockerd
sudo systemctl start docker

# Check disk space
df -h
# Clean up if needed
docker system prune -a --volumes -f

# Check for Docker updates
docker version
```

Reset Docker (last resort):
```bash
# Stop Docker
sudo systemctl stop docker

# Remove Docker data (WARNING: loses all containers/images)
sudo rm -rf /var/lib/docker

# Start Docker
sudo systemctl start docker
```

---

## 1️⃣1️⃣ Universal Debugging Toolkit

Essential commands for troubleshooting any Docker issue.

### 📋 Container Logs

```bash
# View logs
docker logs <container-id>

# Follow logs in real-time
docker logs -f <container-id>

# Last 100 lines
docker logs --tail 100 <container-id>

# Logs since timestamp
docker logs --since 2024-01-01T10:00:00 <container-id>

# Logs with timestamps
docker logs -t <container-id>
```

---

### 🔍 Inspect Resources

```bash
# Inspect container (full details)
docker inspect <container-id>

# Get specific field
docker inspect <container-id> --format='{{.State.Status}}'
docker inspect <container-id> --format='{{.NetworkSettings.IPAddress}}'

# Use jq for better formatting
docker inspect <container-id> | jq '.[0].NetworkSettings'
docker inspect <container-id> | jq '.[0].Mounts'

# Inspect image
docker inspect <image-name>

# Inspect network
docker network inspect <network-name>

# Inspect volume
docker volume inspect <volume-name>
```

---

### 💻 Execute Commands in Container

```bash
# Interactive bash shell
docker exec -it <container-id> bash

# If bash not available, use sh
docker exec -it <container-id> sh

# Run single command
docker exec <container-id> ps aux
docker exec <container-id> ls -la /app

# Run as specific user
docker exec -u root <container-id> whoami

# Run with environment variable
docker exec -e DEBUG=true <container-id> python app.py
```

---

### 📊 Monitor Resource Usage

```bash
# Real-time stats for all containers
docker stats

# Single container stats
docker stats <container-id>

# Stats without streaming (single snapshot)
docker stats --no-stream

# Format output
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

### 📡 Event Monitoring

```bash
# Watch all Docker events
docker events

# Filter events by type
docker events --filter event=start
docker events --filter event=die

# Filter by container
docker events --filter container=<container-id>

# Filter by time
docker events --since '2024-01-01T10:00:00'
```

---

### 📈 Process Monitoring

```bash
# View processes in container
docker top <container-id>

# With custom format
docker top <container-id> aux

# See process tree
docker exec <container-id> ps auxf
```

---

### 🔌 Port Inspection

```bash
# View port mappings
docker port <container-id>

# Specific port
docker port <container-id> 8080

# List all containers with ports
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

---

### 🌐 Network Inspection

```bash
# List networks
docker network ls

# Inspect network
docker network inspect <network-name>

# See which containers are on network
docker network inspect <network-name> --format='{{range .Containers}}{{.Name}} {{end}}'

# Test connectivity
docker exec <container-id> ping <other-container>
docker exec <container-id> curl http://<service>:8080
```

---

### 💾 Volume Inspection

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect <volume-name>

# Find where volume is mounted on host
docker volume inspect <volume-name> --format='{{.Mountpoint}}'

# List containers using volume
docker ps -a --filter volume=<volume-name>
```

---

### 🗄️ System Information

```bash
# Disk usage
docker system df

# Detailed disk usage
docker system df -v

# System-wide information
docker info

# Docker version
docker version
```

---

## 1️⃣2️⃣ Debugging Checklist

Follow this 10-step checklist when troubleshooting Docker issues:

### ✅ Step 1: Check Container Status
```bash
docker ps -a
```
- Is container running?
- What's the exit code?
- When did it last restart?

### ✅ Step 2: Check Logs
```bash
docker logs --tail 50 <container-id>
```
- Any error messages?
- What was the last log entry?
- Are there stack traces?

### ✅ Step 3: Inspect Container
```bash
docker inspect <container-id> | jq '.[0].State'
```
- What's the exit code?
- When did it start/stop?
- What's the restart policy?

### ✅ Step 4: Check Resource Usage
```bash
docker stats --no-stream <container-id>
```
- Is it using too much CPU/memory?
- Is there memory pressure?
- Network I/O normal?

### ✅ Step 5: Verify Environment Variables
```bash
docker exec <container-id> env
```
- Are all required env vars present?
- Are values correct?
- Any typos?

### ✅ Step 6: Check File System
```bash
docker exec <container-id> ls -la /app
```
- Are all files present?
- Correct permissions?
- Volumes mounted correctly?

### ✅ Step 7: Test Network Connectivity
```bash
docker exec <container-id> ping -c 3 8.8.8.8
docker exec <container-id> curl http://other-service
```
- Can reach external network?
- Can reach other containers?
- DNS working?

### ✅ Step 8: Check Ports
```bash
docker port <container-id>
netstat -tlnp | grep <port>
```
- Ports exposed correctly?
- Port conflicts?
- Listening on correct interface?

### ✅ Step 9: Review Dockerfile
```bash
docker history <image-name>
```
- Base image appropriate?
- Commands in correct order?
- Caching optimized?

### ✅ Step 10: Check Host Resources
```bash
df -h
free -h
top
```
- Disk space available?
- Memory available?
- CPU not maxed out?

---

## 1️⃣3️⃣ Quick Reference Table

| **Error Message** | **Likely Cause** | **Quick Fix** |
|-------------------|------------------|---------------|
| `Cannot connect to Docker daemon` | Docker not running | `sudo systemctl start docker` |
| `port is already allocated` | Port in use | `lsof -i :<port>` and kill process or use different port |
| `no space left on device` | Disk full | `docker system prune -a --volumes -f` |
| `exit code 137` | Out of memory (OOM) | Add memory limit: `-m 512m` or increase limit |
| `exit code 1` | Application error | Check logs: `docker logs <container-id>` |
| `connection refused` | Service not listening on 0.0.0.0 | Bind to `0.0.0.0` instead of `127.0.0.1` |
| `permission denied` | Wrong file permissions | `chown` in Dockerfile or fix host permissions |
| `cannot remove container` | Container still running | `docker stop <container-id>` then `docker rm <container-id>` |
| `network not found` | Network doesn't exist | `docker network create <network-name>` |
| `volume not found` | Volume doesn't exist | `docker volume create <volume-name>` |
| `image not found` | Image not pulled/built | `docker pull <image>` or `docker build` |
| `unauthorized` | Not logged into registry | `docker login` |
| `context deadline exceeded` | Network timeout | Check DNS, proxy, or increase timeout |
| `layer already being pulled` | Concurrent pulls | Wait for existing pull to complete |
| `manifest unknown` | Wrong image name/tag | Verify image name and tag exist |

---

## 🎯 Best Practices Summary

1. **Always use `.dockerignore`** to exclude unnecessary files
2. **Order Dockerfile commands** from least to most frequently changing
3. **Use multi-stage builds** to reduce image size
4. **Set resource limits** (CPU, memory) for all containers
5. **Use health checks** to ensure containers are actually ready
6. **Bind to `0.0.0.0`** not `127.0.0.1` for network services
7. **Use named volumes** for persistent data
8. **Run as non-root user** for security
9. **Never put secrets in Dockerfile** or environment variables
10. **Clean up regularly** with `docker system prune`
11. **Use absolute paths** for volume mounts
12. **Check logs first** when debugging issues
13. **Use `--no-cache`** when package installation fails
14. **Match UID/GID** between host and container for volumes

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**Remember:** Most Docker issues fall into a few categories: permissions, networking, resource limits, or file paths. Check logs first, then systematically verify configuration. The debugging toolkit and checklist above will solve 90% of issues! 🚀