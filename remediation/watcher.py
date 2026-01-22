#!/usr/bin/env python3
"""
Auto-Remediation Watcher

Monitors benchmark results and generates remediation plans when performance
degrades beyond acceptable thresholds.

Remediation Actions:
  1. Scale gateway replicas (if high latency or error rate)
  2. Reduce max_tokens in ConfigMap (if backend overloaded)
  3. Rollback to previous image tag (if recent deployment caused issues)
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RemediationAction:
    """Represents a remediation action to be taken."""

    priority: int  # 1=critical, 2=high, 3=medium
    action_type: str
    description: str
    command: str
    rationale: str


class PerformanceThresholds:
    """Performance thresholds for triggering remediation."""

    # Latency thresholds (milliseconds)
    P95_LATENCY_WARNING = 100.0
    P95_LATENCY_CRITICAL = 150.0
    P99_LATENCY_CRITICAL = 200.0

    # Error rate thresholds (percentage)
    ERROR_RATE_WARNING = 0.01  # 1%
    ERROR_RATE_CRITICAL = 0.05  # 5%

    # Throughput thresholds (requests/second)
    THROUGHPUT_MIN_WARNING = 15.0
    THROUGHPUT_MIN_CRITICAL = 10.0


class RemediationWatcher:
    """Analyzes performance metrics and generates remediation plans."""

    def __init__(self, results_file: Path):
        self.results_file = results_file
        self.results: dict[str, Any] | None = None
        self.actions: list[RemediationAction] = []

    def load_results(self) -> bool:
        """Load benchmark results from JSON file."""
        if not self.results_file.exists():
            print(f"❌ Error: Benchmark results file not found: {self.results_file}")
            return False

        try:
            with open(self.results_file, encoding="utf-8-sig") as f:
                self.results = json.load(f)
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in results file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading results: {e}")
            return False

    def analyze_metrics(self) -> None:
        """Analyze metrics and determine if remediation is needed."""
        if not self.results:
            return

        latency_stats = self.results.get("latency_stats", {})
        p95_latency = latency_stats.get("p95_ms", 0)
        p99_latency = latency_stats.get("p99_ms", 0)
        error_rate = self.results.get("error_rate", 0)
        throughput = self.results.get("throughput_rps", 0)

        # Check P95 latency
        if p95_latency >= PerformanceThresholds.P95_LATENCY_CRITICAL:
            self.actions.append(
                RemediationAction(
                    priority=1,
                    action_type="scale",
                    description="Scale gateway replicas to handle increased load",
                    command="kubectl scale deployment llm-gateway --replicas=5",
                    rationale=f"P95 latency ({p95_latency:.2f}ms) exceeds critical threshold "
                    f"({PerformanceThresholds.P95_LATENCY_CRITICAL}ms)",
                )
            )
        elif p95_latency >= PerformanceThresholds.P95_LATENCY_WARNING:
            self.actions.append(
                RemediationAction(
                    priority=2,
                    action_type="scale",
                    description="Increase gateway replicas",
                    command="kubectl scale deployment llm-gateway --replicas=4",
                    rationale=f"P95 latency ({p95_latency:.2f}ms) exceeds warning threshold "
                    f"({PerformanceThresholds.P95_LATENCY_WARNING}ms)",
                )
            )

        # Check P99 latency for worst-case scenarios
        if p99_latency >= PerformanceThresholds.P99_LATENCY_CRITICAL:
            self.actions.append(
                RemediationAction(
                    priority=1,
                    action_type="scale",
                    description="Scale backend replicas for tail latency",
                    command="kubectl scale deployment llm-backend --replicas=5",
                    rationale=f"P99 latency ({p99_latency:.2f}ms) indicates backend bottleneck",
                )
            )

        # Check error rate
        if error_rate >= PerformanceThresholds.ERROR_RATE_CRITICAL:
            self.actions.append(
                RemediationAction(
                    priority=1,
                    action_type="rollback",
                    description="Rollback to previous stable version",
                    command="kubectl rollout undo deployment llm-gateway && "
                    "kubectl rollout undo deployment llm-backend",
                    rationale=f"Error rate ({error_rate * 100:.2f}%) exceeds critical threshold "
                    f"({PerformanceThresholds.ERROR_RATE_CRITICAL * 100:.0f}%)",
                )
            )
        elif error_rate >= PerformanceThresholds.ERROR_RATE_WARNING:
            self.actions.append(
                RemediationAction(
                    priority=2,
                    action_type="config",
                    description="Reduce load by lowering max_tokens",
                    command="kubectl patch configmap llm-config -p "
                    '\'{"data":{"MAX_TOKENS":"50"}}\'',
                    rationale=f"Error rate ({error_rate * 100:.2f}%) indicates system overload",
                )
            )

        # Check throughput degradation
        if throughput <= PerformanceThresholds.THROUGHPUT_MIN_CRITICAL:
            self.actions.append(
                RemediationAction(
                    priority=1,
                    action_type="scale",
                    description="Emergency scaling - throughput critically low",
                    command="kubectl scale deployment llm-gateway --replicas=10",
                    rationale=f"Throughput ({throughput:.2f} req/s) critically low",
                )
            )
        elif throughput <= PerformanceThresholds.THROUGHPUT_MIN_WARNING:
            self.actions.append(
                RemediationAction(
                    priority=3,
                    action_type="investigate",
                    description="Investigate throughput degradation",
                    command="kubectl logs -l app=gateway --tail=100",
                    rationale=f"Throughput ({throughput:.2f} req/s) below expected baseline",
                )
            )

        # Check for combined issues (high latency + errors)
        if (
            p95_latency >= PerformanceThresholds.P95_LATENCY_WARNING
            and error_rate >= PerformanceThresholds.ERROR_RATE_WARNING
        ):
            self.actions.append(
                RemediationAction(
                    priority=1,
                    action_type="combined",
                    description="Combined remediation: scale and rollback",
                    command="kubectl scale deployment llm-gateway --replicas=6 && "
                    "kubectl rollout undo deployment llm-gateway",
                    rationale="Multiple degraded metrics detected - combined approach needed",
                )
            )

    def print_report(self) -> None:
        """Print remediation report."""
        print("\n" + "=" * 70)
        print("AUTO-REMEDIATION WATCHER REPORT")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Results File: {self.results_file}")

        if not self.results:
            print("\n❌ No results loaded")
            return

        # Print current metrics
        print("\n📊 Current Metrics:")
        latency_stats = self.results.get("latency_stats", {})
        print(f"  P50 Latency:     {latency_stats.get('p50_ms', 0):.2f} ms")
        print(f"  P95 Latency:     {latency_stats.get('p95_ms', 0):.2f} ms")
        print(f"  P99 Latency:     {latency_stats.get('p99_ms', 0):.2f} ms")
        print(f"  Throughput:      {self.results.get('throughput_rps', 0):.2f} req/s")
        print(f"  Error Rate:      {self.results.get('error_rate', 0) * 100:.2f}%")
        print(f"  Success Rate:    {(1 - self.results.get('error_rate', 0)) * 100:.2f}%")

        # Print threshold status
        print("\n🎯 Threshold Status:")
        p95 = latency_stats.get("p95_ms", 0)
        error_rate = self.results.get("error_rate", 0)
        throughput = self.results.get("throughput_rps", 0)

        p95_status = (
            "✅ OK"
            if p95 < PerformanceThresholds.P95_LATENCY_WARNING
            else "⚠️  WARNING"
            if p95 < PerformanceThresholds.P95_LATENCY_CRITICAL
            else "❌ CRITICAL"
        )
        print(
            f"  P95 Latency:     {p95_status} "
            f"(threshold: {PerformanceThresholds.P95_LATENCY_WARNING}ms warning, "
            f"{PerformanceThresholds.P95_LATENCY_CRITICAL}ms critical)"
        )

        error_status = (
            "✅ OK"
            if error_rate < PerformanceThresholds.ERROR_RATE_WARNING
            else "⚠️  WARNING"
            if error_rate < PerformanceThresholds.ERROR_RATE_CRITICAL
            else "❌ CRITICAL"
        )
        print(
            f"  Error Rate:      {error_status} "
            f"(threshold: {PerformanceThresholds.ERROR_RATE_WARNING * 100:.0f}% warning, "
            f"{PerformanceThresholds.ERROR_RATE_CRITICAL * 100:.0f}% critical)"
        )

        throughput_status = (
            "✅ OK"
            if throughput >= PerformanceThresholds.THROUGHPUT_MIN_WARNING
            else "⚠️  WARNING"
            if throughput >= PerformanceThresholds.THROUGHPUT_MIN_CRITICAL
            else "❌ CRITICAL"
        )
        print(
            f"  Throughput:      {throughput_status} "
            f"(minimum: {PerformanceThresholds.THROUGHPUT_MIN_WARNING} req/s warning)"
        )

        # Print remediation actions
        if not self.actions:
            print("\n✅ No remediation actions needed - all metrics within acceptable ranges")
        else:
            print(f"\n⚠️  {len(self.actions)} Remediation Action(s) Recommended:")
            print("-" * 70)

            # Sort by priority
            sorted_actions = sorted(self.actions, key=lambda x: x.priority)

            for i, action in enumerate(sorted_actions, 1):
                priority_label = {1: "🔴 CRITICAL", 2: "🟡 HIGH", 3: "🟢 MEDIUM"}
                print(f"\n{i}. [{priority_label[action.priority]}] {action.description}")
                print(f"   Type: {action.action_type}")
                print(f"   Rationale: {action.rationale}")
                print(f"   Command: {action.command}")

        print("\n" + "=" * 70)

    def generate_script(self, output_file: Path) -> None:
        """Generate a shell script to execute remediation actions."""
        if not self.actions:
            return

        script_content = "#!/bin/bash\n"
        script_content += "# Auto-generated remediation script\n"
        script_content += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        script_content += "set -e\n\n"

        script_content += "echo 'Starting auto-remediation...'\n\n"

        sorted_actions = sorted(self.actions, key=lambda x: x.priority)
        for i, action in enumerate(sorted_actions, 1):
            script_content += f"# Action {i}: {action.description}\n"
            script_content += f"echo 'Executing: {action.description}'\n"
            script_content += f"{action.command}\n"
            script_content += "sleep 2\n\n"

        script_content += "echo 'Remediation complete'\n"
        script_content += "kubectl get pods\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make executable on Unix-like systems
        try:
            os.chmod(output_file, 0o755)
        except:
            pass

        print(f"\n📝 Remediation script saved to: {output_file}")

    def should_remediate(self) -> bool:
        """Return True if any critical actions are needed."""
        return any(action.priority == 1 for action in self.actions)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-Remediation Watcher - Monitor and remediate performance issues"
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path(__file__).parent.parent / "bench" / "bench_results.json",
        help="Path to benchmark results JSON file",
    )
    parser.add_argument("--generate-script", type=Path, help="Generate remediation script to file")
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        help="Automatically execute critical remediation actions (use with caution!)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    # Create watcher instance
    watcher = RemediationWatcher(args.results)

    # Load and analyze results
    if not watcher.load_results():
        sys.exit(1)

    watcher.analyze_metrics()
    watcher.print_report()

    # Generate script if requested
    if args.generate_script:
        watcher.generate_script(args.generate_script)

    # Auto-execute critical actions if enabled
    if args.auto_execute and not args.dry_run:
        if watcher.should_remediate():
            print("\n⚠️  Auto-execution enabled - executing CRITICAL remediation actions...")
            script_file = Path("/tmp/auto_remediation.sh")
            watcher.generate_script(script_file)

            import subprocess

            try:
                result = subprocess.run(
                    ["bash", str(script_file)], capture_output=True, text=True, timeout=300
                )
                print(result.stdout)
                if result.returncode != 0:
                    print(f"❌ Remediation failed: {result.stderr}")
                    sys.exit(1)
            except subprocess.TimeoutExpired:
                print("❌ Remediation timed out")
                sys.exit(1)
            except Exception as e:
                print(f"❌ Error executing remediation: {e}")
                sys.exit(1)

    # Exit with error code if critical issues detected
    if watcher.should_remediate():
        print("\n❌ Critical performance issues detected - remediation required")
        sys.exit(1)
    else:
        print("\n✅ System performance within acceptable ranges")
        sys.exit(0)


if __name__ == "__main__":
    main()
