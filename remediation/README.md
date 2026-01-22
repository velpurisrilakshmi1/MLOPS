# Auto-Remediation Watcher

Automated performance monitoring and remediation system for the LLM Inference Platform.

## Overview

The remediation watcher monitors benchmark results and automatically generates (or executes) remediation actions when performance degrades beyond acceptable thresholds.

## Components

### 1. Watcher Script (`watcher.py`)

Python script that analyzes benchmark results and generates remediation plans.

**Features**:
- Reads `bench_results.json` from benchmarks
- Analyzes key metrics: P95 latency, P99 latency, error rate, throughput
- Generates prioritized remediation actions
- Can auto-execute critical actions (optional)
- Creates remediation shell scripts

**Thresholds**:
```python
P95_LATENCY_WARNING = 100.0 ms
P95_LATENCY_CRITICAL = 150.0 ms
P99_LATENCY_CRITICAL = 200.0 ms
ERROR_RATE_WARNING = 1%
ERROR_RATE_CRITICAL = 5%
THROUGHPUT_MIN_WARNING = 15.0 req/s
THROUGHPUT_MIN_CRITICAL = 10.0 req/s
```

### 2. Kubernetes CronJob (`k8s/remediation-cronjob.yaml`)

Runs the watcher every 5 minutes in Kubernetes.

**Includes**:
- ServiceAccount with RBAC permissions
- ConfigMap for configuration
- CronJob that runs every 5 minutes
- Alternative continuous monitoring deployment

## Remediation Actions

### Priority Levels

- **🔴 CRITICAL (Priority 1)**: Immediate action required
- **🟡 HIGH (Priority 2)**: Action recommended soon
- **🟢 MEDIUM (Priority 3)**: Investigation needed

### Action Types

#### 1. Scale Gateway Replicas

**Trigger**: High P95 latency or low throughput

**Actions**:
```bash
# Warning level
kubectl scale deployment llm-gateway --replicas=4

# Critical level
kubectl scale deployment llm-gateway --replicas=5

# Emergency
kubectl scale deployment llm-gateway --replicas=10
```

**Rationale**: Distribute load across more instances to reduce latency

#### 2. Scale Backend Replicas

**Trigger**: High P99 latency (tail latency issues)

**Action**:
```bash
kubectl scale deployment llm-backend --replicas=5
```

**Rationale**: Backend bottleneck causing worst-case latency spikes

#### 3. Reduce max_tokens in ConfigMap

**Trigger**: Moderate error rate (1-5%)

**Action**:
```bash
kubectl patch configmap llm-config -p '{"data":{"MAX_TOKENS":"50"}}'
kubectl rollout restart deployment llm-gateway
kubectl rollout restart deployment llm-backend
```

**Rationale**: Reduce per-request processing time to handle more requests

#### 4. Rollback to Previous Version

**Trigger**: Critical error rate (>5%)

**Action**:
```bash
kubectl rollout undo deployment llm-gateway
kubectl rollout undo deployment llm-backend
```

**Rationale**: Recent deployment may have introduced bugs or performance issues

#### 5. Combined Remediation

**Trigger**: Multiple degraded metrics

**Action**:
```bash
kubectl scale deployment llm-gateway --replicas=6
kubectl rollout undo deployment llm-gateway
```

**Rationale**: Scale to handle load while reverting problematic changes

## Usage

### Local Execution

```bash
# Run watcher with default results file
python remediation/watcher.py

# Specify custom results file
python remediation/watcher.py --results bench/bench_results.json

# Generate remediation script
python remediation/watcher.py --generate-script remediate.sh

# Dry run (show what would be done)
python remediation/watcher.py --dry-run

# Auto-execute critical actions (use with caution!)
python remediation/watcher.py --auto-execute
```

### Example Output

```
======================================================================
AUTO-REMEDIATION WATCHER REPORT
======================================================================
Timestamp: 2026-01-21 18:45:23
Results File: bench/bench_results.json

📊 Current Metrics:
  P50 Latency:     45.20 ms
  P95 Latency:     128.50 ms
  P99 Latency:     145.30 ms
  Throughput:      18.50 req/s
  Error Rate:      0.50%
  Success Rate:    99.50%

🎯 Threshold Status:
  P95 Latency:     ⚠️  WARNING (threshold: 100.0ms warning, 150.0ms critical)
  Error Rate:      ✅ OK (threshold: 1% warning, 5% critical)
  Throughput:      ✅ OK (minimum: 15.0 req/s warning)

⚠️  1 Remediation Action(s) Recommended:
----------------------------------------------------------------------

1. [🟡 HIGH] Increase gateway replicas
   Type: scale
   Rationale: P95 latency (128.50ms) exceeds warning threshold (100.0ms)
   Command: kubectl scale deployment llm-gateway --replicas=4

======================================================================

📝 Remediation script saved to: remediate.sh
```

### Kubernetes Deployment

#### Option 1: CronJob (Recommended)

Deploy the CronJob to run every 5 minutes:

```bash
# Apply the CronJob
kubectl apply -f k8s/remediation-cronjob.yaml

# View CronJob status
kubectl get cronjob auto-remediation-watcher

# View recent jobs
kubectl get jobs -l app=auto-remediation

# View logs from latest job
kubectl logs -l job=watcher --tail=100

# Enable auto-execution (careful!)
kubectl patch configmap watcher-config -p '{"data":{"AUTO_EXECUTE":"true"}}'

# Trigger manual run
kubectl create job --from=cronjob/auto-remediation-watcher manual-check-$(date +%s)
```

#### Option 2: Continuous Monitoring Deployment

Run watcher continuously as a deployment:

```bash
# Deploy continuous watcher
kubectl apply -f k8s/remediation-cronjob.yaml

# View watcher pod
kubectl get pods -l mode=continuous

# Stream logs
kubectl logs -f deployment/remediation-watcher-sidecar
```

### Integration with CI/CD

Add to `.github/workflows/nightly-bench.yml`:

```yaml
- name: Run auto-remediation check
  run: |
    python remediation/watcher.py \
      --results bench/bench_results.json \
      --generate-script remediation.sh
    
    if [ -f remediation.sh ]; then
      echo "Remediation actions recommended"
      cat remediation.sh
    fi
```

## Configuration

### Environment Variables

- `AUTO_EXECUTE`: Enable automatic execution of remediation actions (default: false)
- `DRY_RUN`: Show actions without executing (default: false)
- `RESULTS_PATH`: Path to benchmark results file

### Customizing Thresholds

Edit `remediation/watcher.py`:

```python
class PerformanceThresholds:
    P95_LATENCY_WARNING = 100.0      # Your threshold
    P95_LATENCY_CRITICAL = 150.0     # Your threshold
    ERROR_RATE_WARNING = 0.01        # 1%
    ERROR_RATE_CRITICAL = 0.05       # 5%
```

### Adding Custom Actions

Extend the `analyze_metrics` method:

```python
# Add custom remediation logic
if custom_condition:
    self.actions.append(RemediationAction(
        priority=2,
        action_type="custom",
        description="Your custom action",
        command="kubectl your-command",
        rationale="Why this action is needed"
    ))
```

## Best Practices

### Safety

1. **Start with dry-run mode** to validate actions
2. **Test in staging** before production
3. **Monitor remediation effects** with metrics
4. **Set up alerts** for failed remediation jobs
5. **Review actions** before enabling auto-execute

### Monitoring

1. **Track remediation history** in logs
2. **Alert on frequent remediations** (indicates systemic issues)
3. **Measure time to recovery** after remediation
4. **Document patterns** of when remediations occur

### Tuning

1. **Adjust thresholds** based on actual workload
2. **Test remediation actions** manually first
3. **Verify resource limits** allow for scaling
4. **Set max replicas** in HPA to prevent over-scaling
5. **Implement circuit breakers** to prevent remediation loops

## Troubleshooting

### Watcher Not Running

```bash
# Check CronJob status
kubectl describe cronjob auto-remediation-watcher

# Check for failed jobs
kubectl get jobs -l app=auto-remediation

# View job logs
kubectl logs job/auto-remediation-watcher-<timestamp>
```

### Permission Errors

```bash
# Verify RBAC
kubectl auth can-i get deployments --as=system:serviceaccount:default:remediation-watcher
kubectl auth can-i patch deployments --as=system:serviceaccount:default:remediation-watcher

# Check role bindings
kubectl describe rolebinding remediation-watcher
```

### Actions Not Executing

```bash
# Verify auto-execute is enabled
kubectl get configmap watcher-config -o yaml

# Check for errors in logs
kubectl logs -l app=auto-remediation --tail=100

# Test manually
kubectl run test-watcher --rm -it --image=python:3.11-slim -- \
  python /app/watcher.py --dry-run
```

### Remediation Not Effective

1. **Check if actions completed successfully**
   ```bash
   kubectl get deployments
   kubectl rollout status deployment llm-gateway
   ```

2. **Verify new replicas are ready**
   ```bash
   kubectl get pods -l app=gateway
   ```

3. **Run new benchmark** to validate improvement
   ```bash
   python bench/run_bench.py -n 100
   ```

## Advanced Usage

### Webhook Integration

Send alerts to Slack/PagerDuty when remediation occurs:

```python
import requests

def send_alert(actions):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    message = {
        "text": f"🚨 Auto-remediation triggered: {len(actions)} actions"
    }
    requests.post(webhook_url, json=message)
```

### Metrics Export

Export remediation events to Prometheus:

```python
from prometheus_client import Counter, Gauge

remediation_counter = Counter('remediations_total', 'Total remediations')
latency_gauge = Gauge('observed_p95_latency', 'Current P95 latency')

# In analyze_metrics()
latency_gauge.set(p95_latency)
if self.actions:
    remediation_counter.inc()
```

### Machine Learning Integration

Use historical data to predict when remediation will be needed:

```python
def predict_remediation_need(historical_results):
    # Load historical metrics
    # Train simple model
    # Predict if remediation will be needed soon
    # Trigger proactive scaling
    pass
```

## Limitations

- **Reactive, not predictive**: Actions taken after problems occur
- **No complex dependencies**: Each action is independent
- **Stateless**: No memory of previous remediations
- **Simple heuristics**: Threshold-based, not ML-driven
- **Kubernetes-specific**: Requires kubectl and RBAC permissions

## Future Enhancements

- [ ] Predictive remediation using ML
- [ ] Multi-cluster support
- [ ] Rollback verification (test before completing)
- [ ] Cost-aware scaling decisions
- [ ] Integration with APM tools (Datadog, New Relic)
- [ ] Remediation history database
- [ ] Smart cooldown periods to prevent flapping
- [ ] A/B testing of remediation strategies

## Examples

### Example 1: High Latency Scenario

```bash
# Simulate high latency in results
cat > bench/bench_results.json << EOF
{
  "latency_stats": {"p95_ms": 165.0, "p99_ms": 200.0},
  "error_rate": 0.005,
  "throughput_rps": 15.0
}
EOF

# Run watcher
python remediation/watcher.py

# Output: Scale gateway to 5 replicas (CRITICAL)
```

### Example 2: High Error Rate

```bash
# Simulate high error rate
cat > bench/bench_results.json << EOF
{
  "latency_stats": {"p95_ms": 80.0, "p99_ms": 100.0},
  "error_rate": 0.08,
  "throughput_rps": 12.0
}
EOF

# Run watcher
python remediation/watcher.py

# Output: Rollback to previous version (CRITICAL)
```

### Example 3: Multiple Issues

```bash
# Simulate multiple problems
cat > bench/bench_results.json << EOF
{
  "latency_stats": {"p95_ms": 140.0, "p99_ms": 180.0},
  "error_rate": 0.02,
  "throughput_rps": 8.0
}
EOF

# Run watcher with script generation
python remediation/watcher.py --generate-script fix.sh

# Review script
cat fix.sh

# Execute if acceptable
bash fix.sh
```

## Security Considerations

- **Limit RBAC permissions** to only what's needed
- **Use separate namespace** for watcher
- **Enable audit logging** for remediation actions
- **Require approval** for critical actions (disable auto-execute)
- **Rate limit** remediation actions to prevent cascading failures
- **Validate input** from benchmark results (prevent injection)

## Contributing

To add new remediation strategies:

1. Define new thresholds in `PerformanceThresholds`
2. Add logic in `analyze_metrics()` method
3. Create `RemediationAction` with appropriate priority
4. Test thoroughly in staging environment
5. Update documentation

## License

Same as main project (MIT)
