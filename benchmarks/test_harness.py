#!/usr/bin/env python3
"""
MCP Integration Benchmark Test Harness

Runs benchmark problems through Claude Code with different MCP configurations:
- baseline: Claude Code only (no MCP)
- mind: Claude Code + Mind MCP
- mind_muse: Claude Code + Mind MCP + Muse MCP
- spark: Claude Code + Full Spark Intelligence

Usage:
    python benchmarks/test_harness.py --config baseline --problems all
    python benchmarks/test_harness.py --config mind --problems ds_001,prog_002
    python benchmarks/test_harness.py --run-all
"""

import argparse
import json
import time
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.eval_metrics import (
    EvalResult, MetricScore, MetricCategory,
    score_correctness, score_completeness, score_code_quality,
    score_tool_usage, score_time_to_solution, score_error_recovery,
    score_context_utilization, aggregate_results, generate_report
)


BENCHMARKS_DIR = Path(__file__).parent
OUTPUT_DIR = BENCHMARKS_DIR / "out"
LOGS_DIR = BENCHMARKS_DIR / "logs"


@dataclass
class BenchmarkProblem:
    """A benchmark problem to evaluate."""
    id: str
    title: str
    difficulty: str
    description: str
    category: str
    test_cases: List[Dict] = field(default_factory=list)
    starter_code: Optional[str] = None
    expected_output: Optional[Dict] = None
    evaluation_criteria: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class TestRun:
    """A single test run with results."""
    problem: BenchmarkProblem
    configuration: str
    start_time: datetime
    end_time: Optional[datetime] = None
    solution: Optional[str] = None
    tool_calls: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    memory_ids: List[str] = field(default_factory=list)
    advisories: List[Dict] = field(default_factory=list)
    raw_output: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()


class BenchmarkHarness:
    """Main test harness for running benchmarks."""

    CONFIGURATIONS = ["baseline", "mind", "mind_muse", "spark"]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        self.problems: List[BenchmarkProblem] = []
        self.results: List[EvalResult] = []

    def load_problems(self, problem_files: Optional[List[str]] = None) -> int:
        """Load benchmark problems from JSON files."""
        if problem_files is None:
            problem_files = [
                str(BENCHMARKS_DIR / "data_science_problems.json"),
                str(BENCHMARKS_DIR / "programming_problems.json")
            ]

        for file_path in problem_files:
            path = Path(file_path)
            if not path.exists():
                print(f"Warning: Problem file not found: {file_path}")
                continue

            with open(path) as f:
                data = json.load(f)

            category = data.get("category", "general")
            for p in data.get("problems", []):
                problem = BenchmarkProblem(
                    id=p["id"],
                    title=p["title"],
                    difficulty=p["difficulty"],
                    description=p["description"],
                    category=category,
                    test_cases=p.get("test_cases", []),
                    starter_code=p.get("starter_code"),
                    expected_output=p.get("expected_output"),
                    evaluation_criteria=p.get("evaluation_criteria", {}),
                    tags=p.get("tags", [])
                )
                self.problems.append(problem)

        print(f"Loaded {len(self.problems)} problems")
        return len(self.problems)

    def filter_problems(self, problem_ids: Optional[List[str]] = None) -> List[BenchmarkProblem]:
        """Filter problems by ID list."""
        if problem_ids is None or "all" in problem_ids:
            return self.problems
        return [p for p in self.problems if p.id in problem_ids]

    def _build_prompt(self, problem: BenchmarkProblem, config: str) -> str:
        """Build the prompt for Claude Code."""
        prompt_parts = [
            f"# Benchmark Problem: {problem.title}",
            f"**Difficulty:** {problem.difficulty}",
            f"**Category:** {problem.category}",
            "",
            "## Problem Description",
            problem.description,
            ""
        ]

        if problem.starter_code:
            prompt_parts.extend([
                "## Starter Code",
                "```python",
                problem.starter_code,
                "```",
                ""
            ])

        if problem.test_cases:
            prompt_parts.extend([
                "## Test Cases",
                "```json",
                json.dumps(problem.test_cases[:2], indent=2),  # Show first 2
                "```",
                ""
            ])

        prompt_parts.extend([
            "## Instructions",
            "1. Implement a complete, working solution",
            "2. Include proper error handling",
            "3. Add type hints and docstrings",
            "4. Ensure all test cases pass",
            "",
            "Provide the solution code:"
        ])

        # Add MCP-specific instructions
        if config == "mind":
            prompt_parts.insert(0, "[Using Mind MCP - retrieve relevant context before solving]")
        elif config == "mind_muse":
            prompt_parts.insert(0, "[Using Mind+Muse MCP - retrieve context and explore creative solutions]")
        elif config == "spark":
            prompt_parts.insert(0, "[Using Spark Intelligence - full learning pipeline active]")

        return "\n".join(prompt_parts)

    def _simulate_claude_response(self, problem: BenchmarkProblem, config: str) -> TestRun:
        """
        Simulate a Claude Code response for testing the harness.

        In production, this would call the actual Claude Code CLI.
        """
        run = TestRun(
            problem=problem,
            configuration=config,
            start_time=datetime.now()
        )

        # Simulate processing time based on difficulty
        delay = {"easy": 0.5, "medium": 1.0, "hard": 1.5}.get(problem.difficulty, 1.0)
        time.sleep(delay)

        # Simulate solution (placeholder)
        if problem.starter_code:
            run.solution = problem.starter_code + "\n    # Implementation here\n    pass"
        else:
            run.solution = f"# Solution for {problem.id}\ndef solution():\n    pass"

        # Simulate tool calls based on config
        base_calls = 5
        if config == "mind":
            base_calls += 3
            run.memory_ids = ["mem_001", "mem_002"]
        elif config == "mind_muse":
            base_calls += 5
            run.memory_ids = ["mem_001", "mem_002", "mem_003"]
        elif config == "spark":
            base_calls += 4
            run.memory_ids = ["mem_001"]
            run.advisories = [{"type": "pre_tool", "content": "Consider edge cases"}]

        run.tool_calls = [{"name": f"tool_{i}", "args": {}} for i in range(base_calls)]
        run.end_time = datetime.now()

        return run

    def _run_claude_code(self, problem: BenchmarkProblem, config: str) -> TestRun:
        """
        Run Claude Code on a problem with specified configuration.

        This method interfaces with the actual Claude Code CLI.
        """
        run = TestRun(
            problem=problem,
            configuration=config,
            start_time=datetime.now()
        )

        prompt = self._build_prompt(problem, config)

        # Build Claude Code command based on configuration
        cmd = ["claude", "--print"]

        # Configuration-specific flags would go here
        # For now, we pass the prompt via stdin

        try:
            # In a real implementation, we'd capture the full interaction
            # For now, use simulation
            result = self._simulate_claude_response(problem, config)
            run.solution = result.solution
            run.tool_calls = result.tool_calls
            run.memory_ids = result.memory_ids
            run.advisories = result.advisories
            run.end_time = datetime.now()

        except subprocess.TimeoutExpired:
            run.errors.append("Timeout exceeded")
            run.end_time = datetime.now()
        except Exception as e:
            run.errors.append(str(e))
            run.end_time = datetime.now()

        return run

    def _evaluate_run(self, run: TestRun) -> EvalResult:
        """Evaluate a test run and produce scores."""
        result = EvalResult(
            problem_id=run.problem.id,
            configuration=run.configuration,
            raw_output=run.solution,
            tool_calls=run.tool_calls,
            errors=run.errors,
            wall_time_seconds=run.duration_seconds,
            memory_ids_used=run.memory_ids,
            advisories_received=run.advisories
        )

        # Score correctness (placeholder - would need actual execution)
        correctness = MetricScore(
            name="correctness",
            category=MetricCategory.CORRECTNESS,
            value=75.0 if run.solution else 0.0,
            max_value=100.0,
            weight=0.25,
            details="Simulated score"
        )
        result.scores.append(correctness)

        # Score completeness
        requirements = ["type hints", "error handling", "docstrings"]
        completeness = score_completeness(requirements, run.solution or "")
        result.scores.append(completeness)

        # Score code quality
        quality = score_code_quality(run.solution or "")
        result.scores.append(quality)

        # Score tool usage
        tool_score = score_tool_usage(run.tool_calls)
        result.scores.append(tool_score)

        # Score time
        time_score = score_time_to_solution(run.duration_seconds)
        result.scores.append(time_score)

        # Score error recovery
        recovered = [e for e in run.errors if "recovered" in e.lower()]
        error_score = score_error_recovery(run.errors, recovered)
        result.scores.append(error_score)

        # Score context utilization (for MCP configs)
        if run.configuration != "baseline":
            context_score = score_context_utilization(
                run.memory_ids,
                relevant_used=len(run.memory_ids),
                irrelevant_used=0
            )
            result.scores.append(context_score)

        return result

    def run_benchmark(
        self,
        config: str,
        problem_ids: Optional[List[str]] = None,
        verbose: bool = True
    ) -> List[EvalResult]:
        """Run benchmark for a specific configuration."""
        if config not in self.CONFIGURATIONS:
            raise ValueError(f"Invalid config: {config}. Must be one of {self.CONFIGURATIONS}")

        problems = self.filter_problems(problem_ids)

        if verbose:
            print(f"\n{'='*60}")
            print(f"Running benchmark: {config.upper()}")
            print(f"Problems: {len(problems)}")
            print(f"{'='*60}\n")

        results = []
        for i, problem in enumerate(problems, 1):
            if verbose:
                print(f"[{i}/{len(problems)}] {problem.id}: {problem.title}...")

            run = self._run_claude_code(problem, config)
            result = self._evaluate_run(run)
            results.append(result)

            if verbose:
                print(f"    Score: {result.total_score:.1f}/100")
                print(f"    Time: {result.wall_time_seconds:.1f}s")
                print(f"    Tools: {len(result.tool_calls)}")

        self.results.extend(results)
        return results

    def run_all_configurations(
        self,
        problem_ids: Optional[List[str]] = None,
        verbose: bool = True
    ) -> Dict[str, List[EvalResult]]:
        """Run benchmark across all configurations."""
        all_results = {}

        for config in self.CONFIGURATIONS:
            results = self.run_benchmark(config, problem_ids, verbose)
            all_results[config] = results

        return all_results

    def save_results(self, filename: Optional[str] = None) -> Path:
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        output_path = self.output_dir / filename

        data = {
            "timestamp": datetime.now().isoformat(),
            "total_problems": len(self.problems),
            "total_evaluations": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "aggregated": aggregate_results(self.results)
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nResults saved to: {output_path}")
        return output_path

    def print_summary(self):
        """Print summary report."""
        report = generate_report(self.results)
        print(report)


def main():
    parser = argparse.ArgumentParser(description="MCP Integration Benchmark Harness")
    parser.add_argument(
        "--config",
        choices=BenchmarkHarness.CONFIGURATIONS + ["all"],
        default="baseline",
        help="Configuration to test"
    )
    parser.add_argument(
        "--problems",
        type=str,
        default="all",
        help="Comma-separated problem IDs or 'all'"
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all configurations"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output filename for results"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()

    harness = BenchmarkHarness()
    harness.load_problems()

    problem_ids = None if args.problems == "all" else args.problems.split(",")
    verbose = not args.quiet

    if args.run_all or args.config == "all":
        harness.run_all_configurations(problem_ids, verbose)
    else:
        harness.run_benchmark(args.config, problem_ids, verbose)

    harness.save_results(args.output)
    harness.print_summary()


if __name__ == "__main__":
    main()
