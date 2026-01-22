# LLM Inference Platform

[![PR CI](https://github.com/<owner>/<repo>/actions/workflows/pr.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/pr.yml)
[![Main CI/CD](https://github.com/<owner>/<repo>/actions/workflows/main.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/main.yml)
[![Nightly Benchmark](https://github.com/<owner>/<repo>/actions/workflows/nightly-bench.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/nightly-bench.yml)

A lightweight LLM inference gateway built with FastAPI, designed for Kubernetes deployment with performance monitoring and auto-remediation capabilities.

## Features

- **FastAPI Gateway**: High-performance API endpoints for LLM inference
- **Mock Backend**: Simulated LLM worker for testing and development
- **Structured Logging**: JSON-formatted logs for observability
- **Health Checks**: `/healthz` and `/readyz` endpoints for Kubernetes
- **Metrics**: `/metrics` endpoint for monitoring
- **Docker Support**: Multi-stage builds with non-root user
- **Kubernetes Ready**: Full K8s manifests with auto-scaling

## Project Structure

```
llm-inference-platform/
├── gateway_api/
│   └── main.py              # FastAPI application
├── llm_backend/
│   └── worker.py            # Mock LLM worker
├── tests/
│   └── test_smoke.py        # Smoke tests
├── Dockerfile.gateway       # Gateway container
├── Dockerfile.backend       # Backend worker container
├── docker-compose.yml       # Local orchestration
├── Makefile                 # Build automation
└── requirements.txt         # Python dependencies
```

## Quick Start

### Local Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the API**:
```bash
# Set PYTHONPATH and run
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH="$PWD"    # Windows PowerShell

python -m gateway_api.main
```

3. **Test the API**:
```bash
# Health check
curl http://localhost:8001/healthz

# Generate text
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "max_tokens": 50}'

# View metrics
curl http://localhost:8001/metrics
```

4. **Run tests**:
```bash
pytest tests/ -v
```

### Docker

**Build images**:
```bash
make docker-build
```

**Run container**:
```bash
make docker-run PORT=8000
```

**Run tests**:
```bash
make test
```

**Clean up**:
```bash
make clean
```

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/readyz` | GET | Readiness probe |
| `/metrics` | GET | Prometheus-style metrics |
| `/generate` | POST | Generate text from LLM |

### Generate Request Body

```json
{
  "prompt": "Your prompt here",
  "max_tokens": 100,
  "temperature": 0.7
}
```

### Generate Response

```json
{
  "text": "Generated text...",
  "tokens_per_sec": 125.5,
  "latency_ms": 45.2,
  "model": "mock-llm-v1"
}
```

## Development

### Prerequisites

- Python 3.11+
- Docker (optional)
- kubectl (for Kubernetes deployment)
- kind (for local Kubernetes testing)

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_smoke.py::test_generate -v

# With coverage
pytest tests/ --cov=gateway_api --cov=llm_backend
```

## Monitoring

The `/metrics` endpoint provides:
- `request_count`: Total number of generate requests
- `avg_latency_ms`: Average response latency
- `total_latency_ms`: Cumulative latency
- `worker_status`: Backend worker status

## Benchmarking

Performance testing with regression detection.

### Quick Benchmark

```bash
cd bench

# Install requests library
pip install requests

# Run benchmark against localhost
python run_bench.py --url http://localhost:8000 -n 100

# Run against Kubernetes (with port-forward active)
python run_bench.py --url http://localhost:8000 -n 100
```

### Regression Detection

```bash
# Set baseline
python run_bench.py -n 200
python compare.py --set-baseline

# Run new benchmark and compare
python run_bench.py -n 200
python compare.py

# Exits with code 1 if:
#   - P95 latency regresses > 20%
#   - Error rate exceeds 1%
```

### Benchmark Options

```bash
# Load testing with concurrency
python run_bench.py -n 1000 -c 10

# Custom prompts and output
python run_bench.py --prompts my_prompts.jsonl -o results.json

# Full options
python run_bench.py --url http://localhost:8000 -n 500 -c 5 --timeout 30
```

**Metrics collected:**
- Latency (p50, p95, p99)
- Throughput (requests/second)
- Error rate
- Tokens per second

See [bench/README.md](bench/README.md) for detailed documentation.

## CI/CD

Automated workflows with GitHub Actions.

### Workflows

- **Pull Request CI** - Lint, test, and build on every PR
- **Main Branch** - Test, build, push images, and run benchmarks
- **Nightly Benchmark** - Daily performance regression testing

### Status

All workflows run on `ubuntu-latest` and include:
- Code linting with `ruff`
- Unit tests with `pytest`
- Docker builds for gateway and backend
- Performance benchmarks with regression detection

### Regression Gates

Nightly benchmarks **fail if**:
- P95 latency regresses > 20%
- Error rate exceeds 1%

See [.github/workflows/README.md](.github/workflows/README.md) for detailed documentation.

## Configuration

Environment variables:
- `LOG_LEVEL`: Logging level (default: INFO)
- `PORT`: API port (default: 8000)

## Next Steps

- Deploy to Kubernetes (see [k8s/README.md](k8s/README.md))
- Run performance benchmarks (see [bench/README.md](bench/README.md))
- Set up CI/CD pipeline with regression gates (see [.github/workflows/README.md](.github/workflows/README.md))
- Enable auto-remediation monitoring

## License

MIT
