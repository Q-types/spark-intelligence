#!/usr/bin/env python3
"""
Unified Benchmark Runner
========================

Runs all benchmark categories and generates comprehensive reports.
Supports selective category execution and parallel running.

Usage:
    python unified_runner.py                    # Run all benchmarks
    python unified_runner.py --categories database systems  # Run specific categories
    python unified_runner.py --parallel         # Run categories in parallel
    python unified_runner.py --report           # Generate markdown report
"""

import argparse
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback


# =============================================================================
# Configuration
# =============================================================================

BENCHMARK_CATEGORIES = {
    "systems": {
        "module": "systems_benchmark",
        "title": "Systems Programming",
        "description": "Thread pools, mmap, process supervision, lock-free data structures"
    },
    "web_api": {
        "module": "web_api_benchmark",
        "title": "Web & API Development",
        "description": "JWT auth, rate limiting, GraphQL, webhooks"
    },
    "security": {
        "module": "security_benchmark",
        "title": "Security Engineering",
        "description": "Input validation, encryption, secure coding practices"
    },
    "algorithms": {
        "module": "algorithms_benchmark",
        "title": "Algorithms & Data Structures",
        "description": "Sorting, searching, graph algorithms, dynamic programming"
    },
    "debugging": {
        "module": "debugging_benchmark",
        "title": "Debugging & Troubleshooting",
        "description": "Error analysis, root cause identification, fix strategies"
    },
    "code_review": {
        "module": "code_review_benchmark",
        "title": "Code Review",
        "description": "Code quality, best practices, refactoring suggestions"
    },
    "testing": {
        "module": "testing_benchmark",
        "title": "Testing & QA",
        "description": "Unit tests, integration tests, property-based testing"
    },
    "devops": {
        "module": "devops_benchmark",
        "title": "DevOps & Infrastructure",
        "description": "Docker, CI/CD, Kubernetes, monitoring, IaC"
    },
    "database": {
        "module": "database_benchmark",
        "title": "Database Engineering",
        "description": "Schema design, queries, transactions, optimization"
    },
    "mcp": {
        "module": "mcp_benchmark",
        "title": "MCP Servers",
        "description": "Mind, Muse, Architect, Spawner, and unified MCP coordination"
    }
}


@dataclass
class BenchmarkResult:
    """Result from running a single benchmark category."""
    category: str
    title: str
    status: str  # "passed", "failed", "error"
    total_score: float = 0.0
    max_score: float = 0.0
    percentage: float = 0.0
    tests_passed: int = 0
    tests_total: int = 0
    problems: List[Dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


@dataclass
class UnifiedReport:
    """Aggregated results from all benchmark categories."""
    timestamp: str
    categories: List[BenchmarkResult] = field(default_factory=list)
    total_score: float = 0.0
    max_score: float = 0.0
    total_percentage: float = 0.0
    total_tests_passed: int = 0
    total_tests: int = 0
    total_duration: float = 0.0
    status: str = "pending"


# =============================================================================
# Benchmark Runner
# =============================================================================

def load_benchmark_module(module_name: str):
    """Dynamically load a benchmark module."""
    solutions_dir = Path(__file__).parent / "solutions"
    module_path = solutions_dir / f"{module_name}.py"

    if not module_path.exists():
        raise FileNotFoundError(f"Benchmark module not found: {module_path}")

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


def run_single_benchmark(category: str) -> BenchmarkResult:
    """Run a single benchmark category and return results."""
    config = BENCHMARK_CATEGORIES.get(category)
    if not config:
        return BenchmarkResult(
            category=category,
            title=category,
            status="error",
            error_message=f"Unknown category: {category}"
        )

    result = BenchmarkResult(
        category=category,
        title=config["title"],
        status="pending"
    )

    start_time = time.time()

    try:
        # Load and run the benchmark module
        module = load_benchmark_module(config["module"])

        # Most benchmarks have a run_tests() function
        if hasattr(module, "run_tests"):
            benchmark_results = module.run_tests()
        else:
            raise AttributeError(f"Module {config['module']} has no run_tests() function")

        # Extract results
        summary = benchmark_results.get("summary", {})
        result.total_score = summary.get("total_score", 0)
        result.max_score = summary.get("max_score", 0)
        result.percentage = summary.get("overall_percentage", 0)
        result.tests_passed = summary.get("tests_passed", 0)
        result.tests_total = summary.get("tests_total", 0)
        result.problems = benchmark_results.get("problems", [])

        # Determine status
        if result.tests_passed == result.tests_total:
            result.status = "passed"
        else:
            result.status = "failed"

    except Exception as e:
        result.status = "error"
        result.error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

    result.duration_seconds = time.time() - start_time
    return result


def run_all_benchmarks(
    categories: Optional[List[str]] = None,
    parallel: bool = False,
    max_workers: int = 4
) -> UnifiedReport:
    """Run all or selected benchmark categories."""

    if categories is None:
        categories = list(BENCHMARK_CATEGORIES.keys())

    # Validate categories
    invalid = [c for c in categories if c not in BENCHMARK_CATEGORIES]
    if invalid:
        print(f"Warning: Unknown categories will be skipped: {invalid}")
        categories = [c for c in categories if c in BENCHMARK_CATEGORIES]

    report = UnifiedReport(
        timestamp=datetime.now().isoformat()
    )

    start_time = time.time()

    if parallel and len(categories) > 1:
        # Run benchmarks in parallel
        print(f"\nRunning {len(categories)} benchmarks in parallel...")
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_single_benchmark, cat): cat for cat in categories}

            for future in as_completed(futures):
                result = future.result()
                report.categories.append(result)
                _print_category_result(result)
    else:
        # Run sequentially
        for category in categories:
            print(f"\n{'='*60}")
            print(f"Running: {BENCHMARK_CATEGORIES[category]['title']}")
            print(f"{'='*60}")

            result = run_single_benchmark(category)
            report.categories.append(result)
            _print_category_result(result)

    # Calculate totals
    report.total_duration = time.time() - start_time
    report.total_score = sum(r.total_score for r in report.categories)
    report.max_score = sum(r.max_score for r in report.categories)
    report.total_tests_passed = sum(r.tests_passed for r in report.categories)
    report.total_tests = sum(r.tests_total for r in report.categories)

    if report.max_score > 0:
        report.total_percentage = (report.total_score / report.max_score) * 100

    # Determine overall status
    if all(r.status == "passed" for r in report.categories):
        report.status = "passed"
    elif any(r.status == "error" for r in report.categories):
        report.status = "error"
    else:
        report.status = "failed"

    return report


def _print_category_result(result: BenchmarkResult):
    """Print a single category result."""
    status_icon = {"passed": "✓", "failed": "✗", "error": "!"}.get(result.status, "?")
    print(f"  [{status_icon}] {result.title}: {result.percentage:.1f}% "
          f"({result.tests_passed}/{result.tests_total} tests) in {result.duration_seconds:.2f}s")
    if result.error_message:
        print(f"      Error: {result.error_message.split(chr(10))[0]}")


# =============================================================================
# Report Generation
# =============================================================================

def generate_markdown_report(report: UnifiedReport) -> str:
    """Generate a markdown report from benchmark results."""
    lines = [
        "# Unified Benchmark Report",
        "",
        f"**Generated:** {report.timestamp}",
        f"**Status:** {report.status.upper()}",
        f"**Duration:** {report.total_duration:.2f} seconds",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Score | {report.total_score:.1f} / {report.max_score:.1f} |",
        f"| Percentage | {report.total_percentage:.1f}% |",
        f"| Tests Passed | {report.total_tests_passed} / {report.total_tests} |",
        f"| Categories | {len(report.categories)} |",
        "",
        "## Category Results",
        "",
        "| Category | Score | Percentage | Tests | Duration | Status |",
        "|----------|-------|------------|-------|----------|--------|",
    ]

    # Sort categories by percentage descending
    sorted_cats = sorted(report.categories, key=lambda r: r.percentage, reverse=True)

    for r in sorted_cats:
        status_emoji = {"passed": "✅", "failed": "❌", "error": "⚠️"}.get(r.status, "❓")
        lines.append(
            f"| {r.title} | {r.total_score:.1f}/{r.max_score:.1f} | "
            f"{r.percentage:.1f}% | {r.tests_passed}/{r.tests_total} | "
            f"{r.duration_seconds:.2f}s | {status_emoji} |"
        )

    lines.extend([
        "",
        "## Detailed Results",
        ""
    ])

    for r in sorted_cats:
        lines.extend([
            f"### {r.title}",
            "",
            f"**Category:** `{r.category}`",
            f"**Score:** {r.total_score:.1f} / {r.max_score:.1f} ({r.percentage:.1f}%)",
            f"**Tests:** {r.tests_passed} / {r.tests_total}",
            f"**Duration:** {r.duration_seconds:.2f}s",
            ""
        ])

        if r.error_message:
            lines.extend([
                "**Error:**",
                "```",
                r.error_message[:500],
                "```",
                ""
            ])

        if r.problems:
            lines.append("| Problem | Difficulty | Pass Rate | Score |")
            lines.append("|---------|------------|-----------|-------|")
            for p in r.problems:
                lines.append(
                    f"| {p.get('title', p.get('id', 'Unknown'))} | "
                    f"{p.get('difficulty', 'N/A')} | "
                    f"{p.get('pass_rate', 0)*100:.0f}% | "
                    f"{p.get('score', 0):.1f} |"
                )
            lines.append("")

    return "\n".join(lines)


def generate_json_report(report: UnifiedReport) -> dict:
    """Generate a JSON-serializable report."""
    return {
        "timestamp": report.timestamp,
        "status": report.status,
        "total_duration_seconds": report.total_duration,
        "summary": {
            "total_score": report.total_score,
            "max_score": report.max_score,
            "percentage": report.total_percentage,
            "tests_passed": report.total_tests_passed,
            "tests_total": report.total_tests,
            "categories_count": len(report.categories)
        },
        "categories": [
            {
                "category": r.category,
                "title": r.title,
                "status": r.status,
                "total_score": r.total_score,
                "max_score": r.max_score,
                "percentage": r.percentage,
                "tests_passed": r.tests_passed,
                "tests_total": r.tests_total,
                "duration_seconds": r.duration_seconds,
                "problems": r.problems,
                "error_message": r.error_message
            }
            for r in report.categories
        ]
    }


# =============================================================================
# CLI
# =============================================================================

def print_summary(report: UnifiedReport):
    """Print a summary of the benchmark results."""
    print("\n" + "=" * 60)
    print("UNIFIED BENCHMARK SUMMARY")
    print("=" * 60)

    print(f"\n{'Category':<30} {'Score':>12} {'Tests':>12} {'Status':>10}")
    print("-" * 64)

    for r in sorted(report.categories, key=lambda x: x.category):
        status_icon = {"passed": "✓", "failed": "✗", "error": "!"}.get(r.status, "?")
        print(f"{r.title:<30} {r.total_score:>5.0f}/{r.max_score:<5.0f} "
              f"{r.tests_passed:>5}/{r.tests_total:<5} [{status_icon}] {r.status}")

    print("-" * 64)
    print(f"{'TOTAL':<30} {report.total_score:>5.0f}/{report.max_score:<5.0f} "
          f"{report.total_tests_passed:>5}/{report.total_tests:<5} [{report.status.upper()}]")

    print(f"\n**Overall: {report.total_percentage:.1f}% in {report.total_duration:.2f}s**\n")


def main():
    parser = argparse.ArgumentParser(
        description="Unified Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available categories:
  systems      - Systems Programming (threads, mmap, processes)
  web_api      - Web & API (JWT, rate limiting, GraphQL)
  security     - Security Engineering
  algorithms   - Algorithms & Data Structures
  debugging    - Debugging & Troubleshooting
  code_review  - Code Review
  testing      - Testing & QA
  devops       - DevOps & Infrastructure
  database     - Database Engineering
  mcp          - MCP Servers (Mind, Muse, Architect, Spawner, Unified)

Examples:
  python unified_runner.py                           # Run all
  python unified_runner.py -c database systems       # Run specific
  python unified_runner.py --parallel                # Run in parallel
  python unified_runner.py --report --output report  # Generate report files
        """
    )

    parser.add_argument(
        "-c", "--categories",
        nargs="+",
        help="Specific categories to run (default: all)"
    )
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run benchmarks in parallel"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "-r", "--report",
        action="store_true",
        help="Generate markdown and JSON reports"
    )
    parser.add_argument(
        "-o", "--output",
        default="benchmark_report",
        help="Output filename prefix for reports"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available categories and exit"
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Benchmark Categories:\n")
        for cat, config in BENCHMARK_CATEGORIES.items():
            print(f"  {cat:<15} - {config['title']}")
            print(f"                  {config['description']}")
        return 0

    # Run benchmarks
    print("=" * 60)
    print("UNIFIED BENCHMARK RUNNER")
    print("=" * 60)

    report = run_all_benchmarks(
        categories=args.categories,
        parallel=args.parallel,
        max_workers=args.workers
    )

    print_summary(report)

    # Generate reports if requested
    if args.report:
        out_dir = Path(__file__).parent / "out"
        out_dir.mkdir(exist_ok=True)

        # Markdown report
        md_path = out_dir / f"{args.output}.md"
        md_path.write_text(generate_markdown_report(report))
        print(f"Markdown report: {md_path}")

        # JSON report
        json_path = out_dir / f"{args.output}.json"
        json_path.write_text(json.dumps(generate_json_report(report), indent=2))
        print(f"JSON report: {json_path}")

    # Return exit code based on status
    return 0 if report.status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
