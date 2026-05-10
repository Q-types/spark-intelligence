"""
Benchmark Solution: PROG_001 - Implement LRU Cache
Configuration: ARCHITECT (Claude Code + Architect MCP)

Architect MCP Features Used:
- Task decomposition into sub-tasks
- Quality gates for each component
- architect_check_quality_gates: Test pass rate, lint errors
- architect_review_loop: Iterative verification
- architect_enforce_scope: Prevent scope creep

Implementation Pattern:
1. DECOMPOSE: Break into testable components
2. IMPLEMENT: Build each component
3. INTEGRATE: Combine components
4. VERIFY: Run quality gates
5. REVIEW: Fix issues, re-verify

Enhancements over baseline:
1. Component-based architecture
2. Contract-based interfaces
3. Comprehensive test coverage
4. Quality gate automation
"""

from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from collections import OrderedDict
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import time


# ============= Architect: Quality Gate Definitions =============

class QualityGateStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class QualityGateResult:
    """Result of a quality gate check."""
    name: str
    status: QualityGateStatus
    details: str = ""
    blocking: bool = True


@dataclass
class QualityReport:
    """Aggregated quality report."""
    gates: List[QualityGateResult] = field(default_factory=list)
    test_pass_rate: float = 0.0
    scope_coverage: float = 0.0

    @property
    def all_blocking_passed(self) -> bool:
        return all(
            g.status == QualityGateStatus.PASSED
            for g in self.gates if g.blocking
        )

    def add_gate(self, name: str, passed: bool, details: str = "", blocking: bool = True):
        self.gates.append(QualityGateResult(
            name=name,
            status=QualityGateStatus.PASSED if passed else QualityGateStatus.FAILED,
            details=details,
            blocking=blocking
        ))


# ============= Architect: Interface Contract =============

@runtime_checkable
class CacheProtocol(Protocol):
    """Contract for cache implementations (Architect: interface-first design)."""

    def get(self, key: int) -> int:
        """Get value or -1 if not found."""
        ...

    def put(self, key: int, value: int) -> None:
        """Insert or update key-value pair."""
        ...


# ============= Architect: Component Implementation =============

class LRUCache:
    """
    LRU Cache with Architect-style quality gates.

    Components (Architect decomposition):
    1. Storage: OrderedDict for O(1) operations
    2. Eviction: LRU policy via move_to_end/popitem
    3. Validation: Input/output contracts
    4. Metrics: Operation tracking

    Quality Gates:
    - test_pass_rate: 100% (blocking)
    - complexity_check: O(1) operations (blocking)
    - contract_adherence: Implements CacheProtocol (blocking)
    """

    def __init__(self, capacity: int) -> None:
        """
        Initialize LRU cache.

        Quality Gate: Input validation.
        """
        # Input validation (Architect: boundary check)
        if not isinstance(capacity, int):
            raise TypeError(f"Capacity must be int, got {type(capacity)}")
        if capacity < 1:
            raise ValueError(f"Capacity must be >= 1, got {capacity}")

        self._capacity = capacity
        self._cache: OrderedDict[int, int] = OrderedDict()

        # Metrics for quality reporting
        self._metrics = {
            "gets": 0,
            "puts": 0,
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def metrics(self) -> Dict[str, int]:
        return self._metrics.copy()

    def get(self, key: int) -> int:
        """
        Get value for key, -1 if not found.

        Complexity: O(1)
        Contract: Returns int, marks as recently used.
        """
        self._metrics["gets"] += 1

        if key not in self._cache:
            self._metrics["misses"] += 1
            return -1

        # Move to end (most recently used) - O(1)
        self._cache.move_to_end(key)
        self._metrics["hits"] += 1
        return self._cache[key]

    def put(self, key: int, value: int) -> None:
        """
        Insert or update key-value pair.

        Complexity: O(1)
        Contract: Evicts LRU if at capacity.
        """
        self._metrics["puts"] += 1

        if key in self._cache:
            # Update existing - O(1)
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            # Check capacity before insert
            if len(self._cache) >= self._capacity:
                # Evict LRU (first item) - O(1)
                self._cache.popitem(last=False)
                self._metrics["evictions"] += 1
            self._cache[key] = value

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return f"LRUCache(capacity={self._capacity}, size={len(self)})"


# ============= Architect: Quality Gate Verification =============

def check_quality_gates(cache_class: type) -> QualityReport:
    """
    Run Architect-style quality gates.

    Gates:
    1. test_pass_rate: All test cases pass
    2. contract_check: Implements CacheProtocol
    3. complexity_check: O(1) operations verified
    4. scope_coverage: All requirements implemented
    """
    report = QualityReport()

    # Gate 1: Contract adherence
    try:
        instance = cache_class(10)
        is_protocol = isinstance(instance, CacheProtocol)
        report.add_gate(
            "contract_adherence",
            is_protocol,
            "Implements CacheProtocol" if is_protocol else "Missing protocol methods"
        )
    except Exception as e:
        report.add_gate("contract_adherence", False, str(e))

    # Gate 2: Test pass rate
    test_results = run_test_suite(cache_class)
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["passed"])
    pass_rate = passed_tests / total_tests if total_tests > 0 else 0

    report.test_pass_rate = pass_rate
    report.add_gate(
        "test_pass_rate",
        pass_rate == 1.0,
        f"{passed_tests}/{total_tests} tests passed ({pass_rate:.0%})"
    )

    # Gate 3: Complexity check (O(1) verification)
    complexity_ok = verify_complexity(cache_class)
    report.add_gate(
        "complexity_check",
        complexity_ok,
        "O(1) operations verified" if complexity_ok else "Performance degradation detected"
    )

    # Gate 4: Scope coverage
    required_features = [
        "get_operation",
        "put_operation",
        "capacity_limit",
        "lru_eviction",
        "type_hints"
    ]
    implemented = check_feature_coverage(cache_class)
    coverage = len(implemented) / len(required_features)
    report.scope_coverage = coverage

    report.add_gate(
        "scope_coverage",
        coverage >= 0.9,
        f"{len(implemented)}/{len(required_features)} features ({coverage:.0%})",
        blocking=False  # Non-blocking
    )

    return report


def run_test_suite(cache_class: type) -> List[Dict[str, Any]]:
    """Run comprehensive test suite."""
    results = []

    # Test 1: Basic operations
    try:
        cache = cache_class(2)
        cache.put(1, 1)
        cache.put(2, 2)
        assert cache.get(1) == 1
        cache.put(3, 3)  # Evicts key 2
        assert cache.get(2) == -1
        cache.put(4, 4)  # Evicts key 1
        assert cache.get(1) == -1
        assert cache.get(3) == 3
        assert cache.get(4) == 4
        results.append({"name": "basic_operations", "passed": True})
    except Exception as e:
        results.append({"name": "basic_operations", "passed": False, "error": str(e)})

    # Test 2: Capacity 1
    try:
        cache = cache_class(1)
        cache.put(2, 1)
        assert cache.get(2) == 1
        cache.put(3, 2)
        assert cache.get(2) == -1
        assert cache.get(3) == 2
        results.append({"name": "capacity_one", "passed": True})
    except Exception as e:
        results.append({"name": "capacity_one", "passed": False, "error": str(e)})

    # Test 3: Update existing key
    try:
        cache = cache_class(2)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.put(1, 10)  # Update, should move to end
        cache.put(3, 3)  # Should evict 2, not 1
        assert cache.get(2) == -1
        assert cache.get(1) == 10
        results.append({"name": "update_existing", "passed": True})
    except Exception as e:
        results.append({"name": "update_existing", "passed": False, "error": str(e)})

    # Test 4: Edge cases
    try:
        cache = cache_class(1)
        assert cache.get(999) == -1  # Miss on empty
        cache.put(1, 100)
        assert cache.get(1) == 100
        results.append({"name": "edge_cases", "passed": True})
    except Exception as e:
        results.append({"name": "edge_cases", "passed": False, "error": str(e)})

    # Test 5: Invalid capacity
    try:
        try:
            cache_class(0)
            results.append({"name": "invalid_capacity", "passed": False, "error": "Should raise"})
        except ValueError:
            results.append({"name": "invalid_capacity", "passed": True})
    except Exception as e:
        results.append({"name": "invalid_capacity", "passed": False, "error": str(e)})

    return results


def verify_complexity(cache_class: type) -> bool:
    """Verify O(1) complexity by timing operations at scale."""
    import time

    sizes = [100, 1000, 10000]
    times = []

    for size in sizes:
        cache = cache_class(size)

        # Warm up
        for i in range(size):
            cache.put(i, i)

        # Time operations
        start = time.perf_counter()
        for i in range(1000):
            cache.get(i % size)
            cache.put(size + i, i)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    # O(1) means time should be roughly constant regardless of size
    # Allow 3x variance for noise
    if len(times) >= 2:
        ratio = times[-1] / times[0] if times[0] > 0 else float('inf')
        return ratio < 3.0

    return True


def check_feature_coverage(cache_class: type) -> List[str]:
    """Check which features are implemented."""
    implemented = []

    instance = cache_class(10)

    if hasattr(instance, 'get') and callable(instance.get):
        implemented.append("get_operation")

    if hasattr(instance, 'put') and callable(instance.put):
        implemented.append("put_operation")

    if hasattr(instance, 'capacity') or hasattr(instance, '_capacity'):
        implemented.append("capacity_limit")

    # Check for LRU eviction behavior
    cache = cache_class(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)  # Access 1
    cache.put(3, 3)  # Should evict 2
    if cache.get(2) == -1 and cache.get(1) == 1:
        implemented.append("lru_eviction")

    # Check for type hints
    import inspect
    sig = inspect.signature(cache_class.get)
    if sig.return_annotation != inspect.Parameter.empty:
        implemented.append("type_hints")

    return implemented


# ============= Architect: Review Loop =============

def run_review_loop(max_iterations: int = 3) -> Dict[str, Any]:
    """
    Architect review loop: verify → identify issues → re-verify.
    """
    results = []

    for iteration in range(1, max_iterations + 1):
        print(f"\n[Review Loop] Iteration {iteration}/{max_iterations}")

        report = check_quality_gates(LRUCache)

        iteration_result = {
            "iteration": iteration,
            "gates": [
                {"name": g.name, "status": g.status.value, "details": g.details}
                for g in report.gates
            ],
            "test_pass_rate": report.test_pass_rate,
            "scope_coverage": report.scope_coverage,
            "all_blocking_passed": report.all_blocking_passed
        }
        results.append(iteration_result)

        print(f"  Test Pass Rate: {report.test_pass_rate:.0%}")
        print(f"  Scope Coverage: {report.scope_coverage:.0%}")

        for gate in report.gates:
            status_icon = "✓" if gate.status == QualityGateStatus.PASSED else "✗"
            print(f"  {status_icon} {gate.name}: {gate.details}")

        if report.all_blocking_passed:
            return {
                "status": "complete",
                "iterations": iteration,
                "results": results,
                "action": "complete"
            }

    return {
        "status": "max_iterations_reached",
        "iterations": max_iterations,
        "results": results,
        "action": "continue" if results[-1]["test_pass_rate"] >= 0.8 else "correct"
    }


if __name__ == "__main__":
    print("PROG_001 Solution with Architect MCP")
    print("=" * 60)
    print("\nArchitect Features:")
    print("- Component decomposition")
    print("- Interface contracts (Protocol)")
    print("- Quality gate verification")
    print("- Review loop for compliance")

    print("\n" + "=" * 60)
    print("Running Architect Review Loop...")

    result = run_review_loop()

    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Action: {result['action']}")
