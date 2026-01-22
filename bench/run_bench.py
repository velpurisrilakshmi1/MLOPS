#!/usr/bin/env python3
"""
Benchmark harness for LLM inference platform.

Sends N requests to the API, measures latency, computes statistics,
and saves results to bench_results.json.
"""

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


def load_prompts(prompts_file: Path) -> list[dict[str, Any]]:
    """Load prompts from JSONL file."""
    prompts = []
    with open(prompts_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                prompts.append(json.loads(line))
    return prompts


def send_request(
    base_url: str, prompt_data: dict[str, Any], request_id: int, timeout: int = 30
) -> dict[str, Any]:
    """Send a single inference request and measure latency."""
    url = f"{base_url}/generate"

    payload = {
        "prompt": prompt_data["prompt"],
        "max_tokens": prompt_data.get("max_tokens", 100),
        "temperature": prompt_data.get("temperature", 0.7),
    }

    start_time = time.time()

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            result = response.json()
            return {
                "request_id": request_id,
                "success": True,
                "latency_ms": latency_ms,
                "status_code": response.status_code,
                "tokens_per_sec": result.get("tokens_per_sec", 0),
                "error": None,
            }
        else:
            return {
                "request_id": request_id,
                "success": False,
                "latency_ms": latency_ms,
                "status_code": response.status_code,
                "tokens_per_sec": 0,
                "error": f"HTTP {response.status_code}: {response.text[:100]}",
            }

    except requests.exceptions.Timeout:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "request_id": request_id,
            "success": False,
            "latency_ms": latency_ms,
            "status_code": 0,
            "tokens_per_sec": 0,
            "error": "Request timeout",
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "request_id": request_id,
            "success": False,
            "latency_ms": latency_ms,
            "status_code": 0,
            "tokens_per_sec": 0,
            "error": str(e),
        }


def run_benchmark(
    base_url: str,
    prompts: list[dict[str, Any]],
    num_requests: int,
    concurrency: int = 1,
    timeout: int = 30,
) -> dict[str, Any]:
    """Run benchmark with specified parameters."""
    print("Running benchmark:")
    print(f"  URL: {base_url}")
    print(f"  Total requests: {num_requests}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Unique prompts: {len(prompts)}")
    print()

    # Generate request list by cycling through prompts
    requests_to_send = []
    for i in range(num_requests):
        prompt_data = prompts[i % len(prompts)]
        requests_to_send.append((i + 1, prompt_data))

    # Execute requests
    results = []
    total_start_time = time.time()

    if concurrency == 1:
        # Sequential execution
        for request_id, prompt_data in requests_to_send:
            result = send_request(base_url, prompt_data, request_id, timeout)
            results.append(result)

            # Progress indicator
            if request_id % 10 == 0 or request_id == num_requests:
                success_count = sum(1 for r in results if r["success"])
                print(f"Progress: {request_id}/{num_requests} | Success: {success_count}", end="\r")
    else:
        # Concurrent execution
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(
                    send_request, base_url, prompt_data, request_id, timeout
                ): request_id
                for request_id, prompt_data in requests_to_send
            }

            completed = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1

                # Progress indicator
                if completed % 10 == 0 or completed == num_requests:
                    success_count = sum(1 for r in results if r["success"])
                    print(
                        f"Progress: {completed}/{num_requests} | Success: {success_count}", end="\r"
                    )

    print()  # New line after progress

    total_duration_s = time.time() - total_start_time

    # Compute statistics
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]

    if not successful_results:
        print("ERROR: All requests failed!")
        return {
            "error": "All requests failed",
            "total_requests": num_requests,
            "successful_requests": 0,
            "failed_requests": len(failed_results),
            "error_rate": 1.0,
        }

    latencies = [r["latency_ms"] for r in successful_results]
    latencies.sort()

    # Calculate percentiles
    p50_latency = statistics.median(latencies)
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
    p99_idx = int(len(latencies) * 0.99)
    p99_latency = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]

    # Calculate throughput
    throughput_rps = len(successful_results) / total_duration_s if total_duration_s > 0 else 0

    # Error rate
    error_rate = len(failed_results) / num_requests

    # Average tokens per second
    avg_tokens_per_sec = statistics.mean([r["tokens_per_sec"] for r in successful_results])

    benchmark_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "total_requests": num_requests,
        "successful_requests": len(successful_results),
        "failed_requests": len(failed_results),
        "concurrency": concurrency,
        "total_duration_s": round(total_duration_s, 2),
        "throughput_rps": round(throughput_rps, 2),
        "error_rate": round(error_rate, 4),
        "latency_stats": {
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "mean_ms": round(statistics.mean(latencies), 2),
            "median_ms": round(p50_latency, 2),
            "p50_ms": round(p50_latency, 2),
            "p95_ms": round(p95_latency, 2),
            "p99_ms": round(p99_latency, 2),
            "stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
        },
        "avg_tokens_per_sec": round(avg_tokens_per_sec, 2),
        "errors": [{"request_id": r["request_id"], "error": r["error"]} for r in failed_results],
    }

    return benchmark_results


def print_results(results: dict[str, Any]) -> None:
    """Pretty print benchmark results."""
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Timestamp:           {results['timestamp']}")
    print(f"Base URL:            {results['base_url']}")
    print(f"Total Requests:      {results['total_requests']}")
    print(f"Successful:          {results['successful_requests']}")
    print(f"Failed:              {results['failed_requests']}")
    print(f"Concurrency:         {results['concurrency']}")
    print(f"Duration:            {results['total_duration_s']} seconds")
    print(f"Throughput:          {results['throughput_rps']} req/s")
    print(f"Error Rate:          {results['error_rate'] * 100:.2f}%")
    print()
    print("Latency Statistics:")
    print(f"  Min:               {results['latency_stats']['min_ms']} ms")
    print(f"  Mean:              {results['latency_stats']['mean_ms']} ms")
    print(f"  Median (p50):      {results['latency_stats']['p50_ms']} ms")
    print(f"  p95:               {results['latency_stats']['p95_ms']} ms")
    print(f"  p99:               {results['latency_stats']['p99_ms']} ms")
    print(f"  Max:               {results['latency_stats']['max_ms']} ms")
    print(f"  Std Dev:           {results['latency_stats']['stdev_ms']} ms")
    print()
    print(f"Avg Tokens/sec:      {results['avg_tokens_per_sec']}")

    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])}):")
        for err in results["errors"][:5]:  # Show first 5 errors
            print(f"  Request {err['request_id']}: {err['error']}")
        if len(results["errors"]) > 5:
            print(f"  ... and {len(results['errors']) - 5} more errors")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run benchmark against LLM inference API")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "-n",
        "--num-requests",
        type=int,
        default=100,
        help="Number of requests to send (default: 100)",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent requests (default: 1)",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=Path(__file__).parent / "prompts.jsonl",
        help="Path to prompts JSONL file (default: prompts.jsonl)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).parent / "bench_results.json",
        help="Output file for results (default: bench_results.json)",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    # Check if API is reachable
    try:
        response = requests.get(f"{args.url}/healthz", timeout=5)
        if response.status_code != 200:
            print(f"Warning: Health check failed with status {response.status_code}")
    except Exception as e:
        print(f"Error: Cannot reach API at {args.url}: {e}")
        sys.exit(1)

    # Load prompts
    if not args.prompts.exists():
        print(f"Error: Prompts file not found: {args.prompts}")
        sys.exit(1)

    prompts = load_prompts(args.prompts)
    print(f"Loaded {len(prompts)} prompts from {args.prompts}")

    # Run benchmark
    results = run_benchmark(
        base_url=args.url,
        prompts=prompts,
        num_requests=args.num_requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
    )

    # Print results
    print_results(results)

    # Save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {args.output}")

    # Exit with error if error rate is too high
    if results.get("error_rate", 0) > 0.05:  # > 5% error rate
        print(f"\n⚠️  WARNING: High error rate ({results['error_rate'] * 100:.2f}%)")
        sys.exit(1)


if __name__ == "__main__":
    main()
