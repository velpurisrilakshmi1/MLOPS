#!/usr/bin/env python3
"""
Compare benchmark results to baseline and detect regressions.

Exits with code 1 if:
  - p95 latency regresses by more than 20%
  - Error rate exceeds 1%
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_results(filepath: Path) -> Dict[str, Any]:
    """Load benchmark results from JSON file."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_results(
    current: Dict[str, Any],
    baseline: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Compare current results to baseline.
    
    Returns:
        (passed, issues) - passed is False if regressions detected
    """
    issues = []
    passed = True
    
    # Check error rate
    current_error_rate = current.get("error_rate", 0)
    baseline_error_rate = baseline.get("error_rate", 0)
    
    if current_error_rate > 0.01:  # > 1%
        issues.append(
            f"❌ ERROR RATE EXCEEDS 1%: {current_error_rate * 100:.2f}% "
            f"(baseline: {baseline_error_rate * 100:.2f}%)"
        )
        passed = False
    elif current_error_rate > baseline_error_rate * 1.5:
        issues.append(
            f"⚠️  Error rate increased significantly: {current_error_rate * 100:.2f}% "
            f"(baseline: {baseline_error_rate * 100:.2f}%)"
        )
    
    # Check p95 latency regression
    current_p95 = current.get("latency_stats", {}).get("p95_ms", 0)
    baseline_p95 = baseline.get("latency_stats", {}).get("p95_ms", 0)
    
    if baseline_p95 > 0:
        p95_regression = (current_p95 - baseline_p95) / baseline_p95
        
        if p95_regression > 0.20:  # > 20% regression
            issues.append(
                f"❌ P95 LATENCY REGRESSED BY {p95_regression * 100:.1f}%: "
                f"{current_p95:.2f}ms vs {baseline_p95:.2f}ms baseline "
                f"(threshold: 20%)"
            )
            passed = False
        elif p95_regression > 0.10:  # > 10% regression (warning)
            issues.append(
                f"⚠️  P95 latency increased by {p95_regression * 100:.1f}%: "
                f"{current_p95:.2f}ms vs {baseline_p95:.2f}ms baseline"
            )
    
    # Check p50 latency (info only)
    current_p50 = current.get("latency_stats", {}).get("p50_ms", 0)
    baseline_p50 = baseline.get("latency_stats", {}).get("p50_ms", 0)
    
    if baseline_p50 > 0:
        p50_change = (current_p50 - baseline_p50) / baseline_p50
        if abs(p50_change) > 0.15:  # > 15% change
            symbol = "📈" if p50_change > 0 else "📉"
            issues.append(
                f"{symbol} P50 latency changed by {p50_change * 100:.1f}%: "
                f"{current_p50:.2f}ms vs {baseline_p50:.2f}ms baseline"
            )
    
    # Check throughput (info only)
    current_throughput = current.get("throughput_rps", 0)
    baseline_throughput = baseline.get("throughput_rps", 0)
    
    if baseline_throughput > 0:
        throughput_change = (current_throughput - baseline_throughput) / baseline_throughput
        if abs(throughput_change) > 0.15:  # > 15% change
            symbol = "📈" if throughput_change > 0 else "📉"
            issues.append(
                f"{symbol} Throughput changed by {throughput_change * 100:.1f}%: "
                f"{current_throughput:.2f} req/s vs {baseline_throughput:.2f} req/s baseline"
            )
    
    # Check for failed requests
    current_failed = current.get("failed_requests", 0)
    baseline_failed = baseline.get("failed_requests", 0)
    
    if current_failed > baseline_failed + 5:  # More than 5 additional failures
        issues.append(
            f"⚠️  Failed requests increased: {current_failed} vs {baseline_failed} baseline"
        )
    
    return passed, issues


def print_comparison(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
    issues: List[str]
) -> None:
    """Pretty print comparison results."""
    print("\n" + "=" * 70)
    print("BENCHMARK COMPARISON")
    print("=" * 70)
    
    print("\nCurrent Results:")
    print(f"  Timestamp:         {current.get('timestamp', 'N/A')}")
    print(f"  Total Requests:    {current.get('total_requests', 0)}")
    print(f"  Error Rate:        {current.get('error_rate', 0) * 100:.2f}%")
    print(f"  Throughput:        {current.get('throughput_rps', 0):.2f} req/s")
    print(f"  P50 Latency:       {current.get('latency_stats', {}).get('p50_ms', 0):.2f} ms")
    print(f"  P95 Latency:       {current.get('latency_stats', {}).get('p95_ms', 0):.2f} ms")
    print(f"  P99 Latency:       {current.get('latency_stats', {}).get('p99_ms', 0):.2f} ms")
    
    print("\nBaseline Results:")
    print(f"  Timestamp:         {baseline.get('timestamp', 'N/A')}")
    print(f"  Total Requests:    {baseline.get('total_requests', 0)}")
    print(f"  Error Rate:        {baseline.get('error_rate', 0) * 100:.2f}%")
    print(f"  Throughput:        {baseline.get('throughput_rps', 0):.2f} req/s")
    print(f"  P50 Latency:       {baseline.get('latency_stats', {}).get('p50_ms', 0):.2f} ms")
    print(f"  P95 Latency:       {baseline.get('latency_stats', {}).get('p95_ms', 0):.2f} ms")
    print(f"  P99 Latency:       {baseline.get('latency_stats', {}).get('p99_ms', 0):.2f} ms")
    
    if issues:
        print("\n" + "-" * 70)
        print("DETECTED ISSUES:")
        print("-" * 70)
        for issue in issues:
            print(f"  {issue}")
    
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Compare benchmark results to baseline and detect regressions"
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=Path(__file__).parent / "bench_results.json",
        help="Path to current benchmark results (default: bench_results.json)"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).parent / "baseline.json",
        help="Path to baseline results (default: baseline.json)"
    )
    parser.add_argument(
        "--set-baseline",
        action="store_true",
        help="Copy current results to baseline"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print if regressions are detected"
    )
    
    args = parser.parse_args()
    
    # Handle set-baseline mode
    if args.set_baseline:
        if not args.current.exists():
            print(f"Error: Current results file not found: {args.current}")
            sys.exit(1)
        
        current = load_results(args.current)
        
        with open(args.baseline, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=2)
        
        print(f"✅ Baseline set from {args.current} to {args.baseline}")
        print(f"   P95 latency: {current.get('latency_stats', {}).get('p95_ms', 0):.2f} ms")
        print(f"   Error rate:  {current.get('error_rate', 0) * 100:.2f}%")
        sys.exit(0)
    
    # Load results
    current = load_results(args.current)
    
    if not args.baseline.exists():
        print(f"Warning: Baseline file not found: {args.baseline}")
        print("Run with --set-baseline to create baseline from current results")
        sys.exit(0)
    
    baseline = load_results(args.baseline)
    
    # Compare results
    passed, issues = compare_results(current, baseline)
    
    # Print comparison
    if not args.quiet or not passed:
        print_comparison(current, baseline, issues)
    
    # Exit status
    if passed:
        if not issues:
            print("\n✅ All checks passed! No regressions detected.")
        else:
            print("\n✅ No critical regressions (warnings only)")
        sys.exit(0)
    else:
        print("\n❌ REGRESSION DETECTED - Benchmark failed!")
        print("\nFailure criteria:")
        print("  - P95 latency regression > 20%")
        print("  - Error rate > 1%")
        sys.exit(1)


if __name__ == "__main__":
    main()
