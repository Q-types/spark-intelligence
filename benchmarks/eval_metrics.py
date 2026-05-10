"""
Evaluation Metrics for MCP Integration Benchmark Suite

This module defines comprehensive metrics for evaluating Claude Code performance
across different MCP configurations (baseline, Mind, Mind+Muse, Spark).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import statistics


class MetricCategory(Enum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CODE_QUALITY = "code_quality"
    EFFICIENCY = "efficiency"
    TOOL_USAGE = "tool_usage"
    TIME = "time"
    ERROR_RECOVERY = "error_recovery"
    CONTEXT_UTILIZATION = "context_utilization"


@dataclass
class MetricScore:
    """Individual metric score with metadata."""
    name: str
    category: MetricCategory
    value: float
    max_value: float
    weight: float
    details: Optional[str] = None

    @property
    def normalized(self) -> float:
        """Return score normalized to 0-1 range."""
        if self.max_value == 0:
            return 0.0
        return min(1.0, max(0.0, self.value / self.max_value))

    @property
    def weighted(self) -> float:
        """Return weighted score."""
        return self.normalized * self.weight


@dataclass
class EvalResult:
    """Complete evaluation result for a single problem attempt."""
    problem_id: str
    configuration: str  # baseline, mind, mind_muse, spark
    scores: List[MetricScore] = field(default_factory=list)
    raw_output: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    wall_time_seconds: float = 0.0
    memory_ids_used: List[str] = field(default_factory=list)
    advisories_received: List[Dict] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        """Calculate weighted total score (0-100)."""
        if not self.scores:
            return 0.0
        return sum(s.weighted for s in self.scores) * 100

    @property
    def scores_by_category(self) -> Dict[str, float]:
        """Get average score per category."""
        categories: Dict[str, List[float]] = {}
        for score in self.scores:
            cat = score.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(score.normalized)
        return {k: statistics.mean(v) for k, v in categories.items()}

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "problem_id": self.problem_id,
            "configuration": self.configuration,
            "total_score": round(self.total_score, 2),
            "scores": [
                {
                    "name": s.name,
                    "category": s.category.value,
                    "value": s.value,
                    "max_value": s.max_value,
                    "normalized": round(s.normalized, 3),
                    "weight": s.weight,
                    "details": s.details
                }
                for s in self.scores
            ],
            "scores_by_category": {k: round(v, 3) for k, v in self.scores_by_category.items()},
            "tool_calls_count": len(self.tool_calls),
            "errors_count": len(self.errors),
            "wall_time_seconds": round(self.wall_time_seconds, 2),
            "memory_ids_used": self.memory_ids_used,
            "advisories_count": len(self.advisories_received)
        }


# ============= Metric Scoring Functions =============

def score_correctness(expected: Any, actual: Any, problem_type: str = "general") -> MetricScore:
    """
    Score correctness of output against expected result.

    For different problem types:
    - code: Run test cases, calculate pass rate
    - numeric: Check within tolerance
    - text: Semantic similarity or exact match
    - dataframe: Column match, value match, shape match
    """
    if actual is None:
        return MetricScore(
            name="correctness",
            category=MetricCategory.CORRECTNESS,
            value=0.0,
            max_value=100.0,
            weight=0.25,
            details="No output produced"
        )

    # Simple equality check for basic types
    if expected == actual:
        score = 100.0
        details = "Exact match"
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        # Numeric tolerance
        tolerance = abs(expected) * 0.01 if expected != 0 else 0.01
        if abs(expected - actual) <= tolerance:
            score = 100.0
            details = f"Within 1% tolerance"
        else:
            score = max(0, 100 - abs(expected - actual) / max(abs(expected), 1) * 100)
            details = f"Off by {abs(expected - actual):.4f}"
    elif isinstance(expected, dict) and isinstance(actual, dict):
        # Dictionary comparison
        matching_keys = set(expected.keys()) & set(actual.keys())
        total_keys = set(expected.keys()) | set(actual.keys())
        key_score = len(matching_keys) / len(total_keys) if total_keys else 0

        value_matches = sum(1 for k in matching_keys if expected[k] == actual.get(k))
        value_score = value_matches / len(matching_keys) if matching_keys else 0

        score = (key_score * 50) + (value_score * 50)
        details = f"Keys: {len(matching_keys)}/{len(total_keys)}, Values: {value_matches}/{len(matching_keys)}"
    elif isinstance(expected, list) and isinstance(actual, list):
        # List comparison
        if len(expected) == 0 and len(actual) == 0:
            score = 100.0
            details = "Both empty lists"
        elif len(expected) == 0 or len(actual) == 0:
            score = 0.0
            details = "Length mismatch (one empty)"
        else:
            matches = sum(1 for e, a in zip(expected, actual) if e == a)
            score = (matches / max(len(expected), len(actual))) * 100
            details = f"Matched {matches}/{max(len(expected), len(actual))} elements"
    else:
        # String/other comparison
        score = 100.0 if str(expected) == str(actual) else 0.0
        details = "String comparison"

    return MetricScore(
        name="correctness",
        category=MetricCategory.CORRECTNESS,
        value=score,
        max_value=100.0,
        weight=0.25,
        details=details
    )


def score_completeness(requirements: List[str], solution: str) -> MetricScore:
    """
    Score how many requirements were addressed.

    Args:
        requirements: List of requirement descriptions
        solution: The solution code/text to check
    """
    if not requirements:
        return MetricScore(
            name="completeness",
            category=MetricCategory.COMPLETENESS,
            value=100.0,
            max_value=100.0,
            weight=0.15,
            details="No requirements specified"
        )

    # Simple keyword-based check (in practice, use LLM for semantic matching)
    addressed = 0
    solution_lower = solution.lower()

    keyword_map = {
        "type hints": ["def ", ": ", "->", "typing", "Optional", "List", "Dict"],
        "error handling": ["try:", "except", "raise", "Error"],
        "docstring": ['"""', "'''", "docstring"],
        "test": ["test_", "assert", "pytest"],
        "logging": ["logging", "logger", "log."],
        "async": ["async ", "await ", "asyncio"],
        "retry": ["retry", "backoff", "attempt"],
    }

    for req in requirements:
        req_lower = req.lower()
        found = False

        # Check specific keywords
        for key, patterns in keyword_map.items():
            if key in req_lower:
                if any(p.lower() in solution_lower for p in patterns):
                    found = True
                    break

        # Fallback: check if requirement words appear in solution
        if not found:
            req_words = [w for w in req_lower.split() if len(w) > 3]
            if any(w in solution_lower for w in req_words):
                found = True

        if found:
            addressed += 1

    score = (addressed / len(requirements)) * 100

    return MetricScore(
        name="completeness",
        category=MetricCategory.COMPLETENESS,
        value=score,
        max_value=100.0,
        weight=0.15,
        details=f"Addressed {addressed}/{len(requirements)} requirements"
    )


def score_code_quality(code: str) -> MetricScore:
    """
    Score code quality based on static analysis.

    Checks:
    - Has docstrings
    - Has type hints
    - Reasonable line length
    - No obvious anti-patterns
    - Proper naming conventions
    """
    if not code or not code.strip():
        return MetricScore(
            name="code_quality",
            category=MetricCategory.CODE_QUALITY,
            value=0.0,
            max_value=10.0,
            weight=0.15,
            details="No code provided"
        )

    score = 10.0
    issues = []

    # Check for docstrings
    if '"""' not in code and "'''" not in code:
        score -= 1.0
        issues.append("Missing docstrings")

    # Check for type hints
    if "def " in code and ": " not in code.split("def ")[1].split(")")[0]:
        score -= 1.0
        issues.append("Missing type hints")

    # Check line length
    long_lines = sum(1 for line in code.split("\n") if len(line) > 100)
    if long_lines > 3:
        score -= 0.5
        issues.append(f"{long_lines} lines > 100 chars")

    # Check for magic numbers
    import re
    magic_numbers = re.findall(r'[^0-9][2-9]\d{2,}[^0-9]', code)
    if len(magic_numbers) > 2:
        score -= 0.5
        issues.append("Magic numbers detected")

    # Check for proper exception handling
    if "except:" in code or "except Exception:" in code:
        bare_excepts = code.count("except:") + code.count("except Exception:")
        if bare_excepts > 1:
            score -= 0.5
            issues.append("Bare except clauses")

    # Bonus for good practices
    if "logging" in code or "logger" in code:
        score += 0.5
    if "@dataclass" in code or "NamedTuple" in code:
        score += 0.5

    score = max(0.0, min(10.0, score))

    return MetricScore(
        name="code_quality",
        category=MetricCategory.CODE_QUALITY,
        value=score,
        max_value=10.0,
        weight=0.15,
        details="; ".join(issues) if issues else "Good quality"
    )


def score_efficiency(time_complexity: str, space_complexity: str,
                     expected_time: str, expected_space: str) -> MetricScore:
    """
    Score algorithmic efficiency.

    Args:
        time_complexity: Actual time complexity (e.g., "O(n)", "O(n^2)")
        space_complexity: Actual space complexity
        expected_time: Expected time complexity
        expected_space: Expected space complexity
    """
    complexity_rank = {
        "O(1)": 1, "O(log n)": 2, "O(n)": 3, "O(n log n)": 4,
        "O(n^2)": 5, "O(n^3)": 6, "O(2^n)": 7, "O(n!)": 8
    }

    def get_rank(c: str) -> int:
        c = c.strip().replace(" ", "")
        return complexity_rank.get(c, 5)

    time_actual = get_rank(time_complexity)
    time_expected = get_rank(expected_time)
    space_actual = get_rank(space_complexity)
    space_expected = get_rank(expected_space)

    # Score: 10 if meets or beats expected, deduct for each rank worse
    time_score = 5.0 - max(0, time_actual - time_expected)
    space_score = 5.0 - max(0, space_actual - space_expected)

    total_score = max(0, time_score + space_score)

    return MetricScore(
        name="efficiency",
        category=MetricCategory.EFFICIENCY,
        value=total_score,
        max_value=10.0,
        weight=0.10,
        details=f"Time: {time_complexity} (expected {expected_time}), Space: {space_complexity} (expected {expected_space})"
    )


def score_tool_usage(tool_calls: List[Dict], optimal_range: tuple = (3, 15)) -> MetricScore:
    """
    Score tool usage efficiency.

    Too few calls might indicate incomplete exploration.
    Too many calls might indicate inefficiency.
    """
    count = len(tool_calls)
    min_optimal, max_optimal = optimal_range

    if min_optimal <= count <= max_optimal:
        score = 10.0
        details = f"{count} calls (optimal range)"
    elif count < min_optimal:
        score = (count / min_optimal) * 10
        details = f"{count} calls (below optimal {min_optimal})"
    else:
        # Gradually decrease score for excessive calls
        excess = count - max_optimal
        score = max(0, 10 - (excess / max_optimal) * 5)
        details = f"{count} calls (above optimal {max_optimal})"

    return MetricScore(
        name="tool_usage",
        category=MetricCategory.TOOL_USAGE,
        value=score,
        max_value=10.0,
        weight=0.05,
        details=details
    )


def score_time_to_solution(seconds: float, expected_max: float = 120.0) -> MetricScore:
    """
    Score time to solution.

    Faster is better, but quality shouldn't be sacrificed.
    """
    if seconds <= expected_max * 0.5:
        score = 10.0
        details = f"{seconds:.1f}s (excellent)"
    elif seconds <= expected_max:
        score = 10.0 - ((seconds - expected_max * 0.5) / (expected_max * 0.5)) * 3
        details = f"{seconds:.1f}s (good)"
    else:
        excess_ratio = seconds / expected_max
        score = max(0, 7 - (excess_ratio - 1) * 3)
        details = f"{seconds:.1f}s (slow, expected <{expected_max}s)"

    return MetricScore(
        name="time_to_solution",
        category=MetricCategory.TIME,
        value=score,
        max_value=10.0,
        weight=0.05,
        details=details
    )


def score_error_recovery(errors: List[str], recovered: List[str]) -> MetricScore:
    """
    Score ability to recover from errors.
    """
    if not errors:
        return MetricScore(
            name="error_recovery",
            category=MetricCategory.ERROR_RECOVERY,
            value=10.0,
            max_value=10.0,
            weight=0.05,
            details="No errors encountered"
        )

    recovery_rate = len(recovered) / len(errors) if errors else 1.0
    score = recovery_rate * 10

    return MetricScore(
        name="error_recovery",
        category=MetricCategory.ERROR_RECOVERY,
        value=score,
        max_value=10.0,
        weight=0.05,
        details=f"Recovered from {len(recovered)}/{len(errors)} errors"
    )


def score_context_utilization(memory_ids: List[str], relevant_used: int,
                               irrelevant_used: int = 0) -> MetricScore:
    """
    Score effective use of retrieved context/memories.

    For configurations with Mind/Muse/Spark integration.
    """
    if not memory_ids:
        return MetricScore(
            name="context_utilization",
            category=MetricCategory.CONTEXT_UTILIZATION,
            value=5.0,  # Neutral score if no context available
            max_value=10.0,
            weight=0.05,
            details="No context retrieved"
        )

    total_used = len(memory_ids)
    if total_used == 0:
        score = 0.0
        details = "Context available but not used"
    else:
        relevance_ratio = relevant_used / total_used
        score = relevance_ratio * 10 - (irrelevant_used * 0.5)
        score = max(0, min(10, score))
        details = f"Used {relevant_used} relevant, {irrelevant_used} irrelevant of {total_used} total"

    return MetricScore(
        name="context_utilization",
        category=MetricCategory.CONTEXT_UTILIZATION,
        value=score,
        max_value=10.0,
        weight=0.05,
        details=details
    )


# ============= Aggregation =============

def aggregate_results(results: List[EvalResult]) -> Dict:
    """
    Aggregate results across multiple problems and configurations.
    """
    by_config: Dict[str, List[EvalResult]] = {}
    by_problem: Dict[str, List[EvalResult]] = {}

    for r in results:
        if r.configuration not in by_config:
            by_config[r.configuration] = []
        by_config[r.configuration].append(r)

        if r.problem_id not in by_problem:
            by_problem[r.problem_id] = []
        by_problem[r.problem_id].append(r)

    # Calculate averages per configuration
    config_summary = {}
    for config, config_results in by_config.items():
        scores = [r.total_score for r in config_results]
        times = [r.wall_time_seconds for r in config_results]
        tool_counts = [len(r.tool_calls) for r in config_results]

        config_summary[config] = {
            "avg_score": round(statistics.mean(scores), 2),
            "std_score": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2),
            "avg_time": round(statistics.mean(times), 2),
            "avg_tool_calls": round(statistics.mean(tool_counts), 1),
            "problems_completed": len(config_results),
            "category_scores": {}
        }

        # Aggregate category scores
        all_categories: Dict[str, List[float]] = {}
        for r in config_results:
            for cat, score in r.scores_by_category.items():
                if cat not in all_categories:
                    all_categories[cat] = []
                all_categories[cat].append(score)

        config_summary[config]["category_scores"] = {
            k: round(statistics.mean(v), 3) for k, v in all_categories.items()
        }

    # Calculate improvement over baseline
    if "baseline" in config_summary:
        baseline_score = config_summary["baseline"]["avg_score"]
        for config in config_summary:
            if config != "baseline":
                improvement = config_summary[config]["avg_score"] - baseline_score
                config_summary[config]["improvement_over_baseline"] = round(improvement, 2)
                config_summary[config]["improvement_pct"] = round(
                    (improvement / baseline_score) * 100 if baseline_score > 0 else 0, 1
                )

    return {
        "summary_by_configuration": config_summary,
        "total_problems": len(by_problem),
        "total_evaluations": len(results),
        "configurations_tested": list(by_config.keys())
    }


def generate_report(results: List[EvalResult], output_path: Optional[str] = None) -> str:
    """Generate a human-readable report."""
    agg = aggregate_results(results)

    lines = [
        "=" * 60,
        "MCP INTEGRATION BENCHMARK REPORT",
        "=" * 60,
        "",
        f"Total Problems: {agg['total_problems']}",
        f"Total Evaluations: {agg['total_evaluations']}",
        f"Configurations: {', '.join(agg['configurations_tested'])}",
        "",
        "-" * 60,
        "SUMMARY BY CONFIGURATION",
        "-" * 60,
    ]

    for config, summary in agg["summary_by_configuration"].items():
        lines.append(f"\n{config.upper()}")
        lines.append(f"  Average Score: {summary['avg_score']:.1f}/100")
        lines.append(f"  Std Dev: {summary['std_score']:.1f}")
        lines.append(f"  Range: {summary['min_score']:.1f} - {summary['max_score']:.1f}")
        lines.append(f"  Avg Time: {summary['avg_time']:.1f}s")
        lines.append(f"  Avg Tool Calls: {summary['avg_tool_calls']:.0f}")

        if "improvement_over_baseline" in summary:
            sign = "+" if summary["improvement_over_baseline"] > 0 else ""
            lines.append(f"  vs Baseline: {sign}{summary['improvement_over_baseline']:.1f} ({sign}{summary['improvement_pct']:.1f}%)")

        lines.append("  Category Scores:")
        for cat, score in summary.get("category_scores", {}).items():
            lines.append(f"    - {cat}: {score:.1%}")

    lines.extend(["", "=" * 60])

    report = "\n".join(lines)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)

    return report
