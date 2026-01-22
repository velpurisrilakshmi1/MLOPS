# Benchmark Harness

Performance testing and regression detection for the LLM Inference Platform.

## Overview

The benchmark harness measures API performance by sending multiple requests and collecting latency, throughput, and error rate metrics. It includes regression detection to ensure performance doesn't degrade over time.

## Files

- **prompts.jsonl** - 10 sample prompts in JSONL format
- **run_bench.py** - Main benchmark script
- **compare.py** - Regression detection script
- **bench_results.json** - Latest benchmark results (generated)
- **baseline.json** - Baseline for comparison (optional)

## Quick Start

### Install Dependencies

```bash
pip install requests
```

### Run Benchmark Against Localhost

```bash
# Start the gateway locally first
cd ..
python -m uvicorn gateway_api.main:app --host 0.0.0.0 --port 8000

# In another terminal, run benchmark
cd bench
python run_bench.py --url http://localhost:8000 -n 100
```

### Run Benchmark Against Kubernetes

```bash
# Ensure port-forward is active
kubectl port-forward svc/llm-gateway-service 8000:80

# Run benchmark
python run_bench.py --url http://localhost:8000 -n 100
```

## Usage

### run_bench.py

Run performance benchmarks and collect metrics.

```bash
# Basic usage (100 requests, sequential)
python run_bench.py

# Custom number of requests
python run_bench.py -n 500

# Concurrent requests (load testing)
python run_bench.py -n 1000 -c 10

# Against different endpoint
python run_bench.py --url http://localhost:8000 -n 200

# Custom output file
python run_bench.py -o my_results.json

# Full options
python run_bench.py \
  --url http://localhost:8000 \
  -n 500 \
  -c 5 \
  --prompts ./prompts.jsonl \
  --output bench_results.json \
  --timeout 30
```

**Options:**
- `--url` - API base URL (default: http://localhost:8000)
- `-n, --num-requests` - Number of requests (default: 100)
- `-c, --concurrency` - Concurrent requests (default: 1)
- `--prompts` - Path to prompts file (default: prompts.jsonl)
- `-o, --output` - Output file (default: bench_results.json)
- `--timeout` - Request timeout in seconds (default: 30)

**Metrics Collected:**
- **Throughput** - Requests per second (RPS)
- **Latency** - Min, mean, median (p50), p95, p99, max
- **Error Rate** - Percentage of failed requests
- **Success Rate** - Percentage of successful requests
- **Tokens/sec** - Average token generation speed

### compare.py

Compare benchmark results to baseline and detect regressions.

```bash
# Set initial baseline
python run_bench.py -n 100
python compare.py --set-baseline

# Run new benchmark and compare
python run_bench.py -n 100
python compare.py

# Compare specific files
python compare.py --current new_results.json --baseline baseline.json

# Quiet mode (only output if regression detected)
python compare.py --quiet
```

**Regression Criteria:**
- ❌ **FAIL** if P95 latency regresses by > 20%
- ❌ **FAIL** if error rate exceeds 1%
- ⚠️ **WARN** if P95 latency regresses by > 10%
- ⚠️ **WARN** if P50 latency changes by > 15%
- ⚠️ **WARN** if throughput changes by > 15%

**Exit Codes:**
- `0` - No regressions detected
- `1` - Regression detected (P95 > 20% or error rate > 1%)

## Example Workflows

### Initial Baseline Setup

```bash
# Run benchmark to establish baseline
python run_bench.py -n 200

# Set as baseline
python compare.py --set-baseline
```

### Pre-Deployment Check

```bash
# Run benchmark against current deployment
python run_bench.py -n 200 -o current.json

# Compare to baseline
python compare.py --current current.json --baseline baseline.json

# Exit code 1 if regression detected - can be used in CI/CD
```

### Load Testing

```bash
# Test with high concurrency
python run_bench.py -n 1000 -c 20

# Check if performance degrades under load
python compare.py
```

### Kubernetes vs Local Comparison

```bash
# Benchmark local
python run_bench.py --url http://localhost:8000 -n 100 -o local_results.json

# Benchmark Kubernetes (with port-forward)
python run_bench.py --url http://localhost:8000 -n 100 -o k8s_results.json

# Compare
python compare.py --current k8s_results.json --baseline local_results.json
```

## CI/CD Integration

### Example GitHub Actions Workflow

```yaml
name: Performance Regression Test

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install requests
      
      - name: Start service
        run: |
          python -m uvicorn gateway_api.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
      
      - name: Run benchmark
        working-directory: bench
        run: python run_bench.py -n 200
      
      - name: Check for regressions
        working-directory: bench
        run: python compare.py
```

## Interpreting Results

### Latency Metrics

- **P50 (median)** - Half of requests complete faster than this
- **P95** - 95% of requests complete faster than this (key SLO metric)
- **P99** - 99% of requests complete faster than this (worst-case)

### What's Acceptable?

For this LLM platform:
- ✅ P95 < 100ms (mock LLM)
- ✅ Error rate < 1%
- ✅ Throughput > 50 req/s (sequential)

### Troubleshooting Poor Performance

**High P95 latency:**
- Check pod resource limits
- Verify backend pods are healthy
- Check for network latency
- Review pod logs for errors

**High error rate:**
- Check service health endpoints
- Review pod logs
- Verify ConfigMap settings
- Check resource exhaustion

**Low throughput:**
- Increase concurrency
- Scale up pods (HPA)
- Check resource requests/limits
- Verify no rate limiting

## Sample Output

```
Running benchmark:
  URL: http://localhost:8000
  Total requests: 100
  Concurrency: 1
  Unique prompts: 10

Progress: 100/100 | Success: 100

============================================================
BENCHMARK RESULTS
============================================================
Timestamp:           2026-01-21 18:45:23
Base URL:            http://localhost:8000
Total Requests:      100
Successful:          100
Failed:              0
Concurrency:         1
Duration:            4.23 seconds
Throughput:          23.64 req/s
Error Rate:          0.00%

Latency Statistics:
  Min:               15.32 ms
  Mean:              42.15 ms
  Median (p50):      40.23 ms
  p95:               68.45 ms
  p99:               75.12 ms
  Max:               89.34 ms
  Std Dev:           12.45 ms

Avg Tokens/sec:      1250.34
============================================================

Results saved to: bench_results.json
```

## Extending the Benchmark

### Add Custom Prompts

Edit `prompts.jsonl`:
```jsonl
{"prompt": "Your custom prompt here", "max_tokens": 150, "temperature": 0.7}
{"prompt": "Another prompt", "max_tokens": 200}
```

### Modify Regression Thresholds

Edit `compare.py` and adjust:
```python
if p95_regression > 0.20:  # Change from 20% to your threshold
if current_error_rate > 0.01:  # Change from 1% to your threshold
```

### Add Custom Metrics

Extend `run_bench.py` to track additional metrics like:
- Cache hit rates
- Model inference time
- Queue depth
- Memory usage

## Best Practices

1. **Consistent Load** - Run benchmarks with same parameters for comparison
2. **Warm-up** - Send a few requests before measurement to warm up services
3. **Environment Parity** - Compare like-to-like (local vs local, k8s vs k8s)
4. **Multiple Runs** - Run 3-5 times and average results
5. **Resource Monitoring** - Watch CPU/memory during benchmarks
6. **Version Tracking** - Tag baseline with git commit or version
7. **Document Changes** - Note configuration changes that affect performance

## Troubleshooting

### Connection Refused
- Ensure service is running
- Verify port-forward is active
- Check firewall settings

### Timeouts
- Increase `--timeout` parameter
- Check pod health and logs
- Verify sufficient resources

### High Variance
- Run with more requests for stability
- Check for background processes
- Ensure consistent load conditions

## Next Steps

- Set up automated regression testing in CI/CD
- Add Prometheus metrics integration
- Create performance dashboards
- Implement SLO alerting
- Profile slow requests
