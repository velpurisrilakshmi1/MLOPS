# GitHub Actions CI/CD

Automated workflows for testing, building, and benchmarking the LLM Inference Platform.

## Workflows

### 1. Pull Request CI (`.github/workflows/pr.yml`)

**Trigger**: On pull requests to `main` or `develop` branches

**Jobs**:
- **Lint** - Runs `ruff` for code quality checks
- **Test** - Executes pytest with coverage reporting
- **Build Gateway** - Builds and tests gateway Docker image
- **Build Backend** - Builds and tests backend Docker image
- **Smoke Test** - Runs end-to-end smoke tests with Docker containers
- **PR Summary** - Aggregates results and provides pass/fail status

**Duration**: ~5-8 minutes

**Usage**:
```bash
# Automatically runs on PR creation/update
# No manual intervention needed
```

### 2. Main Branch CI/CD (`.github/workflows/main.yml`)

**Trigger**: On push to `main` branch

**Jobs**:
- **Test** - Runs linting and tests with coverage
- **Build and Push** - Builds Docker images and pushes to GitHub Container Registry
- **Benchmark** - Runs performance benchmarks (100 requests)
- **Integration Test** - Tests gateway + backend interaction
- **Release Summary** - Generates deployment summary

**Artifacts**:
- Docker images pushed to `ghcr.io`
- Benchmark results uploaded (retained for 90 days)

**Duration**: ~10-15 minutes

**Registry Images**:
```
ghcr.io/<owner>/<repo>-gateway:main
ghcr.io/<owner>/<repo>-backend:main
```

### 3. Nightly Benchmark (`.github/workflows/nightly-bench.yml`)

**Trigger**: 
- Scheduled daily at 2 AM UTC
- Manual trigger via `workflow_dispatch`

**Jobs**:
- **Nightly Benchmark** - Comprehensive performance test (500 requests)
  - Downloads previous baseline
  - Runs benchmark against Docker container
  - Compares results to baseline
  - Uploads results and baseline
  - **Fails if**: P95 regression > 20% OR error rate > 1%
- **Report Failure** - Creates GitHub issue on regression
- **Report Success** - Closes open benchmark issues

**Artifacts**:
- Nightly benchmark results (retained for 90 days)
- Baseline results (retained for 365 days)

**Duration**: ~5-7 minutes

## Setup

### Required Secrets

1. **CODECOV_TOKEN** (optional)
   - For code coverage reporting
   - Get from https://codecov.io
   - Add to: Settings → Secrets → Actions

2. **GITHUB_TOKEN** (automatic)
   - Provided automatically by GitHub Actions
   - Used for pushing images to GitHub Container Registry

### Repository Settings

1. **Enable GitHub Packages**
   - Settings → Code and automation → Packages
   - Ensure packages can be created

2. **Enable Issues** (for nightly reports)
   - Settings → General → Features
   - Check "Issues"

3. **Branch Protection** (recommended)
   - Settings → Branches → Add rule for `main`
   - Require status checks to pass: ✓ Lint, ✓ Test, ✓ Build

## Local Testing

### Test Workflows Locally (with act)

```bash
# Install act
# https://github.com/nektos/act

# Test PR workflow
act pull_request -W .github/workflows/pr.yml

# Test main workflow
act push -W .github/workflows/main.yml

# Test nightly benchmark (manual trigger)
act workflow_dispatch -W .github/workflows/nightly-bench.yml
```

### Validate Workflow Syntax

```bash
# Install actionlint
# https://github.com/rhysd/actionlint

# Lint all workflows
actionlint .github/workflows/*.yml
```

## Workflow Details

### PR Workflow

```yaml
on:
  pull_request:
    branches: [main, develop]
```

**Status Checks**:
- ✅ Lint passes
- ✅ All tests pass
- ✅ Docker builds succeed
- ✅ Smoke tests pass

**Caching**:
- Python dependencies cached by pip
- Docker layers cached in GitHub Actions cache

### Main Workflow

```yaml
on:
  push:
    branches: [main]
```

**Features**:
- Automatic versioning using git SHA
- Multi-platform Docker builds (optional)
- Benchmark artifact retention
- GitHub Container Registry push

**Environment Variables**:
```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

### Nightly Benchmark

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:     # Manual trigger
```

**Regression Detection**:
- Downloads previous baseline
- Runs 500 requests for statistical significance
- Compares metrics:
  - P50, P95, P99 latency
  - Throughput (req/s)
  - Error rate
- **Fails** if criteria exceeded
- Creates GitHub issue on failure

**Metrics Tracked**:
```json
{
  "latency_stats": {
    "p50_ms": 45.2,
    "p95_ms": 78.5,
    "p99_ms": 95.3
  },
  "throughput_rps": 22.5,
  "error_rate": 0.0
}
```

## Badge Status

Add status badges to README.md:

```markdown
![PR CI](https://github.com/<owner>/<repo>/actions/workflows/pr.yml/badge.svg)
![Main CI/CD](https://github.com/<owner>/<repo>/actions/workflows/main.yml/badge.svg)
![Nightly Benchmark](https://github.com/<owner>/<repo>/actions/workflows/nightly-bench.yml/badge.svg)
```

## Monitoring

### View Workflow Runs

1. Go to **Actions** tab in GitHub
2. Select workflow from left sidebar
3. View run history and logs

### Benchmark Results

1. Go to workflow run
2. Scroll to **Artifacts** section
3. Download `nightly-benchmark-<number>.zip`
4. Extract and view `bench_results.json`

### Regression Issues

- Automatically created on benchmark failure
- Labeled: `benchmark-failure`, `performance`, `automated`
- Includes link to failed run
- Auto-closes on successful run

## Debugging Failed Workflows

### Lint Failures

```bash
# Run locally
ruff check .
ruff format --check .

# Fix issues
ruff check --fix .
ruff format .
```

### Test Failures

```bash
# Run tests locally
pytest tests/ -v

# Run with same coverage settings
pytest tests/ --cov=gateway_api --cov=llm_backend --cov-report=term
```

### Docker Build Failures

```bash
# Test builds locally
docker build -f Dockerfile.gateway -t test-gateway .
docker build -f Dockerfile.backend -t test-backend .

# Check for errors
docker run --rm test-gateway python -c "from gateway_api.main import app"
```

### Benchmark Failures

```bash
# Run benchmark locally
docker build -f Dockerfile.gateway -t llm-gateway:test .
docker run -d --name test-gateway -p 8000:8000 llm-gateway:test
sleep 5

# Run benchmark
python bench/run_bench.py -n 500

# Compare to baseline
python bench/compare.py

# Cleanup
docker stop test-gateway && docker rm test-gateway
```

## Best Practices

### For Contributors

1. **Run tests locally** before pushing
2. **Check lint errors** with `ruff check .`
3. **Ensure Docker builds** succeed locally
4. **Wait for PR checks** to pass before requesting review

### For Maintainers

1. **Monitor nightly benchmarks** for regressions
2. **Review benchmark issues** promptly
3. **Update baseline** after intentional performance changes
4. **Keep workflows updated** with security patches

### Performance Guidelines

- **P95 latency should remain < 100ms** for mock LLM
- **Error rate must stay < 1%** for passing
- **Throughput should be ≥ 20 req/s** sequential
- Investigate if metrics degrade > 10% without code changes

## Extending Workflows

### Add Custom Checks

Edit `.github/workflows/pr.yml`:

```yaml
custom-check:
  name: Custom Check
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run custom script
      run: ./scripts/my_check.sh
```

### Add Deployment Stage

Edit `.github/workflows/main.yml`:

```yaml
deploy:
  name: Deploy to Staging
  needs: [test, build-and-push]
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to K8s
      run: kubectl apply -f k8s/
```

### Modify Benchmark Parameters

Edit `.github/workflows/nightly-bench.yml`:

```yaml
- name: Run comprehensive benchmark
  run: |
    python bench/run_bench.py \
      --url http://localhost:8000 \
      -n 1000 \    # Increase request count
      -c 10 \      # Add concurrency
      -o bench/bench_results.json
```

## Troubleshooting

### "Resource not accessible by integration"

**Cause**: Missing permissions for GITHUB_TOKEN

**Fix**: Add to workflow:
```yaml
permissions:
  contents: read
  packages: write
  issues: write
```

### Artifact upload failures

**Cause**: File path incorrect or doesn't exist

**Fix**: 
```yaml
- name: Upload with error handling
  if: always()
  uses: actions/upload-artifact@v4
  with:
    if-no-files-found: warn  # or 'ignore'
```

### Docker build cache issues

**Fix**: Clear cache and rebuild:
```yaml
- name: Clear cache
  run: docker builder prune -af
```

## Cost Optimization

- **Use caching** for dependencies and Docker layers
- **Cancel in-progress runs** on new pushes
- **Limit artifact retention** (90 days for benchmarks)
- **Use `paths-ignore`** to skip unnecessary runs
- **Conditional job execution** with `if:` statements

## Security

- **Never commit secrets** to workflows
- **Use `secrets` context** for sensitive data
- **Pin action versions** (e.g., `@v4` not `@latest`)
- **Review third-party actions** before use
- **Enable Dependabot** for workflow updates

## Next Steps

1. Enable workflows by pushing to GitHub
2. Set up Codecov integration (optional)
3. Monitor first few nightly benchmark runs
4. Add status badges to README
5. Configure branch protection rules
6. Set up Slack/email notifications (optional)
