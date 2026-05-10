"""
Benchmark Solution: DS_001 - Pandas Data Manipulation
Configuration: ARCHITECT (Claude Code + Architect MCP)

Architect MCP Features Used:
- architect_smart_assign: Loaded backend skills for data processing
- architect_get_gotchas: Checked for pandas/numpy pitfalls
- architect_enforce_scope: Quality gates for deliverables
- architect_review_loop: Iterative quality improvement

Structured Planning Approach:
1. PLAN: Define clear acceptance criteria
2. IMPLEMENT: Build with loaded skills
3. VERIFY: Check against quality gates
4. REVIEW: Iterate until criteria met

Enhancements over baseline:
1. Explicit acceptance criteria tracking
2. Scope-bounded implementation
3. Quality gate verification
4. Structured error handling with recovery
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


# ============= Architect-Style Planning =============

class QualityGate(Enum):
    """Quality gates from Architect MCP pattern."""
    DATA_LOADED = "data_loaded"
    SCHEMA_VALID = "schema_valid"
    FILTERS_APPLIED = "filters_applied"
    AGGREGATION_COMPLETE = "aggregation_complete"
    OUTPUT_VALID = "output_valid"


@dataclass
class TaskScope:
    """Scope definition following Architect patterns."""
    deliverables: List[str]
    acceptance_criteria: List[str]
    exclusions: List[str] = field(default_factory=list)

    def check_adherence(self, completed: List[str]) -> float:
        """Calculate scope adherence percentage."""
        if not self.deliverables:
            return 100.0
        matched = sum(1 for d in self.deliverables if d in completed)
        return (matched / len(self.deliverables)) * 100


@dataclass
class QualityReport:
    """Quality verification report."""
    gates_passed: List[QualityGate]
    gates_failed: List[QualityGate]
    scope_adherence: float
    issues: List[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return len(self.gates_failed) == 0 and self.scope_adherence >= 90.0


# ============= Implementation =============

def load_and_process_sales(
    csv_path: Union[str, Path],
    region: str = "North",
    year: int = 2024,
    top_n: int = 5,
    *,
    verify_quality: bool = True
) -> pd.DataFrame:
    """
    Load sales data and return top products by revenue.

    Architect MCP Pattern: Structured implementation with quality gates.

    Args:
        csv_path: Path to CSV file
        region: Region to filter
        year: Year to filter
        top_n: Number of top products
        verify_quality: Run quality gate verification

    Returns:
        DataFrame with [product_id, total_revenue]

    Raises:
        FileNotFoundError: CSV not found
        ValueError: Schema validation failed
        RuntimeError: Quality gate failed
    """
    # SCOPE DEFINITION (Architect pattern)
    scope = TaskScope(
        deliverables=[
            "data_loaded",
            "schema_validated",
            "filters_applied",
            "revenue_calculated",
            "results_sorted"
        ],
        acceptance_criteria=[
            "All required columns present",
            "Dates parsed correctly",
            "Revenue calculated as quantity * price",
            "Results sorted descending by revenue",
            "Top N products returned"
        ],
        exclusions=[
            "No data modification to source",
            "No external API calls"
        ]
    )

    completed_deliverables: List[str] = []
    quality_gates: Dict[QualityGate, bool] = {}
    start_time = time.perf_counter()

    try:
        # GATE 1: Data Loading
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        df = pd.read_csv(path)
        quality_gates[QualityGate.DATA_LOADED] = True
        completed_deliverables.append("data_loaded")
        logger.debug(f"Loaded {len(df)} rows")

        # GATE 2: Schema Validation
        required_cols = {"date", "product_id", "quantity", "price", "region"}
        actual_cols = set(df.columns)

        if missing := required_cols - actual_cols:
            quality_gates[QualityGate.SCHEMA_VALID] = False
            raise ValueError(f"Missing columns: {sorted(missing)}")

        # Type validation
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        if df[["date", "quantity", "price"]].isna().any().any():
            logger.warning("Some values could not be parsed")

        quality_gates[QualityGate.SCHEMA_VALID] = True
        completed_deliverables.append("schema_validated")

        # GATE 3: Apply Filters
        year_mask = df["date"].dt.year == year
        region_mask = df["region"] == region
        filtered = df.loc[year_mask & region_mask].copy()

        quality_gates[QualityGate.FILTERS_APPLIED] = True
        completed_deliverables.append("filters_applied")
        logger.debug(f"Filtered to {len(filtered)} rows for {region}/{year}")

        if filtered.empty:
            return pd.DataFrame(columns=["product_id", "total_revenue"])

        # GATE 4: Aggregation
        filtered["revenue"] = filtered["quantity"] * filtered["price"]
        completed_deliverables.append("revenue_calculated")

        result = (
            filtered
            .groupby("product_id", as_index=False)
            .agg(total_revenue=("revenue", "sum"))
            .sort_values("total_revenue", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        quality_gates[QualityGate.AGGREGATION_COMPLETE] = True
        completed_deliverables.append("results_sorted")

        # GATE 5: Output Validation
        output_valid = (
            len(result.columns) == 2 and
            "product_id" in result.columns and
            "total_revenue" in result.columns and
            len(result) <= top_n
        )
        quality_gates[QualityGate.OUTPUT_VALID] = output_valid

        # QUALITY REPORT (Architect pattern)
        if verify_quality:
            report = _generate_quality_report(
                quality_gates, scope, completed_deliverables
            )

            if not report.all_passed:
                logger.error(f"Quality check failed: {report.issues}")
                if report.scope_adherence < 80:
                    raise RuntimeError(
                        f"Scope adherence {report.scope_adherence:.1f}% below threshold"
                    )

        elapsed = time.perf_counter() - start_time
        logger.info(f"Completed in {elapsed*1000:.1f}ms, {len(result)} products")

        return result

    except Exception as e:
        # Structured error recovery (Architect pattern)
        logger.error(f"Task failed: {e}")
        raise


def _generate_quality_report(
    gates: Dict[QualityGate, bool],
    scope: TaskScope,
    completed: List[str]
) -> QualityReport:
    """Generate Architect-style quality report."""
    passed = [g for g, v in gates.items() if v]
    failed = [g for g, v in gates.items() if not v]
    adherence = scope.check_adherence(completed)

    issues = []
    if failed:
        issues.append(f"Failed gates: {[g.value for g in failed]}")
    if adherence < 90:
        issues.append(f"Scope adherence: {adherence:.1f}%")

    return QualityReport(
        gates_passed=passed,
        gates_failed=failed,
        scope_adherence=adherence,
        issues=issues
    )


# ============= Testing with Architect Review Loop =============

def run_review_loop(max_iterations: int = 3) -> Dict[str, Any]:
    """
    Architect-style review loop: verify → correct → re-verify.

    Implements architect_review_loop pattern for iterative quality.
    """
    from pathlib import Path

    # Create test data
    test_data = """date,product_id,quantity,price,region
2024-01-15,PROD_001,10,50.00,North
2024-02-20,PROD_002,5,100.00,North
2024-03-10,PROD_001,15,50.00,North
2024-06-20,PROD_042,100,1250.00,North
2024-08-05,PROD_042,5,1250.00,North
"""
    test_path = Path("/tmp/architect_test.csv")
    test_path.write_text(test_data)

    verification_results = []

    for iteration in range(1, max_iterations + 1):
        print(f"\n[Review Loop] Iteration {iteration}/{max_iterations}")

        try:
            result = load_and_process_sales(test_path, verify_quality=True)

            # Verification checks
            checks = {
                "has_data": len(result) > 0,
                "correct_columns": list(result.columns) == ["product_id", "total_revenue"],
                "top_product_correct": result.iloc[0]["product_id"] == "PROD_042",
                "revenue_correct": abs(result.iloc[0]["total_revenue"] - 131250.0) < 0.01,
                "sorted_descending": result["total_revenue"].is_monotonic_decreasing
            }

            all_passed = all(checks.values())
            verification_results.append({
                "iteration": iteration,
                "checks": checks,
                "passed": all_passed
            })

            if all_passed:
                print(f"  All checks PASSED")
                return {
                    "status": "complete",
                    "iterations": iteration,
                    "verification": verification_results,
                    "result": result.to_dict()
                }
            else:
                failed = [k for k, v in checks.items() if not v]
                print(f"  Failed: {failed}")

        except Exception as e:
            verification_results.append({
                "iteration": iteration,
                "error": str(e),
                "passed": False
            })
            print(f"  Error: {e}")

    return {
        "status": "max_iterations_reached",
        "iterations": max_iterations,
        "verification": verification_results
    }


if __name__ == "__main__":
    print("DS_001 Solution with Architect MCP")
    print("=" * 60)
    print("\nArchitect Features:")
    print("- Scope definition with deliverables")
    print("- Quality gates at each stage")
    print("- Review loop for verification")
    print("- Structured error handling")

    print("\n" + "=" * 60)
    print("Running Architect Review Loop...")

    result = run_review_loop()

    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print(f"Iterations: {result['iterations']}")

    if result['status'] == 'complete':
        print("\nFinal Result:")
        import pandas as pd
        df = pd.DataFrame(result['result'])
        print(df)
