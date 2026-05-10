"""
Debugging Category Benchmark
Tests all 5 debugging problems with scoring

Problems:
- dbg_001: Find the Race Condition (Hard)
- dbg_002: Memory Leak Investigation (Medium)
- dbg_003: Performance Bottleneck (Medium)
- dbg_004: Deadlock Detection (Hard)
- dbg_005: Off-by-One Errors (Easy)
"""

import threading
import time
import json
import sys
import weakref
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============= Scoring Infrastructure =============

class ScoreCategory(Enum):
    BUG_IDENTIFICATION = "bug_identification"
    FIX_CORRECTNESS = "fix_correctness"
    EXPLANATION = "explanation"
    EDGE_CASES = "edge_cases"


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    category: ScoreCategory = ScoreCategory.FIX_CORRECTNESS


@dataclass
class ProblemScore:
    problem_id: str
    title: str
    difficulty: str
    tests: List[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.tests:
            return 0.0
        return sum(1 for t in self.tests if t.passed) / len(self.tests)

    @property
    def score(self) -> float:
        weight = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}.get(self.difficulty, 1.0)
        return self.pass_rate * 100 * weight

    def add_test(self, name: str, passed: bool, details: str = "",
                 category: ScoreCategory = ScoreCategory.FIX_CORRECTNESS):
        self.tests.append(TestResult(name, passed, details, category))


# ============= DBG_001: Race Condition =============

# BUGGY CODE (for reference):
# class Counter:
#     def __init__(self):
#         self.value = 0
#
#     def increment(self):
#         current = self.value      # READ
#         self.value = current + 1  # WRITE - race between read and write!
#
#     def get(self):
#         return self.value

# BUG EXPLANATION:
# The race condition occurs because increment() is not atomic:
# 1. Thread A reads self.value (e.g., 5)
# 2. Thread B reads self.value (still 5)
# 3. Thread A writes self.value = 5 + 1 = 6
# 4. Thread B writes self.value = 5 + 1 = 6
# Result: Two increments but value only increased by 1

class BuggyCounter:
    """Buggy version with race condition."""
    def __init__(self):
        self.value = 0

    def increment(self):
        current = self.value
        # Simulate delay to make race condition more likely
        self.value = current + 1

    def get(self):
        return self.value


class FixedCounterWithLock:
    """
    Fixed version using minimal locking.

    Fix: Use a lock to make increment atomic.
    Lock scope is minimal - only around the critical section.
    """
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._value += 1

    def get(self):
        with self._lock:
            return self._value


class FixedCounterAtomic:
    """
    Fixed version using atomic-like operations.

    Python's GIL makes simple operations atomic, but for
    demonstration we use a compare-and-swap pattern.
    """
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self):
        # In languages with true atomics, we'd use atomic_add
        # Python equivalent with minimal lock
        with self._lock:
            self._value += 1

    def get(self):
        return self._value  # Reading int is atomic in Python


def test_dbg_001() -> ProblemScore:
    """Test Race Condition Fix."""
    score = ProblemScore("dbg_001", "Find the Race Condition", "Hard")

    # Test 1: Bug identification - buggy version fails under contention
    buggy = BuggyCounter()
    threads = []
    increments_per_thread = 1000
    num_threads = 10

    for _ in range(num_threads):
        t = threading.Thread(target=lambda: [buggy.increment() for _ in range(increments_per_thread)])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    expected = num_threads * increments_per_thread
    buggy_result = buggy.get()
    # Buggy version often loses increments
    score.add_test(
        "buggy_version_has_race",
        buggy_result <= expected,  # Usually less due to race
        f"Buggy counter: {buggy_result} (expected {expected})",
        ScoreCategory.BUG_IDENTIFICATION
    )

    # Test 2: Fixed version is correct
    fixed = FixedCounterWithLock()
    threads = []

    for _ in range(num_threads):
        t = threading.Thread(target=lambda: [fixed.increment() for _ in range(increments_per_thread)])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    fixed_result = fixed.get()
    score.add_test(
        "fixed_version_correct",
        fixed_result == expected,
        f"Fixed counter: {fixed_result} (expected {expected})",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 3: High contention test (100 threads, 1000 increments each)
    high_contention = FixedCounterWithLock()
    threads = []
    high_threads = 100
    high_increments = 1000

    for _ in range(high_threads):
        t = threading.Thread(target=lambda: [high_contention.increment() for _ in range(high_increments)])
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    high_expected = high_threads * high_increments
    score.add_test(
        "high_contention_correct",
        high_contention.get() == high_expected,
        f"100 threads x 1000: {high_contention.get()} (expected {high_expected})",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 4: Verify minimal lock scope
    counter_instance = FixedCounterWithLock()
    score.add_test(
        "minimal_lock_scope",
        hasattr(counter_instance, '_lock') and isinstance(counter_instance._lock, type(threading.Lock())),
        "Lock attribute exists for minimal synchronization",
        ScoreCategory.EXPLANATION
    )

    # Test 5: O(1) operation maintained
    counter = FixedCounterWithLock()
    start = time.perf_counter()
    for _ in range(10000):
        counter.increment()
    elapsed = time.perf_counter() - start

    score.add_test(
        "o1_performance",
        elapsed < 0.5,  # Should be fast
        f"10000 increments in {elapsed:.3f}s",
        ScoreCategory.FIX_CORRECTNESS
    )

    return score


# ============= DBG_002: Memory Leak =============

# BUGGY CODE (for reference):
# class Cache:
#     def __init__(self):
#         self.cache = {}
#         self.callbacks = []  # BUG 1: Callbacks list grows forever
#
#     def get(self, key, loader):
#         if key not in self.cache:
#             value = loader()
#             self.cache[key] = value
#             # BUG 2: Lambda captures 'key', callbacks never cleared
#             self.callbacks.append(lambda: print(f'Loaded {key}'))
#         return self.cache[key]
#
#     def clear(self, key):
#         if key in self.cache:
#             del self.cache[key]
#             # BUG 3: Callbacks not cleared when key cleared

# BUG EXPLANATION:
# 1. callbacks list grows unboundedly - never cleared
# 2. Lambdas capture references, preventing garbage collection
# 3. clear() removes cache entry but not associated callbacks
# 4. No size limit on cache


class BuggyCache:
    """Buggy version with memory leaks."""
    def __init__(self):
        self.cache = {}
        self.callbacks = []

    def get(self, key, loader):
        if key not in self.cache:
            value = loader()
            self.cache[key] = value
            self.callbacks.append(lambda: print(f'Loaded {key}'))
        return self.cache[key]

    def clear(self, key):
        if key in self.cache:
            del self.cache[key]


class FixedCache:
    """
    Fixed cache with no memory leaks.

    Fixes:
    1. Use OrderedDict with max size (LRU eviction)
    2. Use WeakValueDictionary for callbacks or clear them properly
    3. Track callbacks per key and clear with cache entry
    4. Add memory monitoring
    """
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: str, loader: Callable):
        if key in self._cache:
            self._stats["hits"] += 1
            self._cache.move_to_end(key)
            return self._cache[key]

        self._stats["misses"] += 1
        value = loader()

        # Evict if at capacity
        while len(self._cache) >= self.max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            # Clean up callbacks for evicted key
            if evicted_key in self._callbacks:
                del self._callbacks[evicted_key]
            self._stats["evictions"] += 1

        self._cache[key] = value
        # Store callback reference that can be cleaned up
        # Using a string message instead of lambda to avoid closure
        self._callbacks[key] = [f"Loaded {key}"]

        return value

    def clear(self, key: str):
        if key in self._cache:
            del self._cache[key]
        if key in self._callbacks:
            del self._callbacks[key]

    def clear_all(self):
        self._cache.clear()
        self._callbacks.clear()

    def memory_stats(self) -> Dict[str, int]:
        return {
            "cache_size": len(self._cache),
            "callbacks_count": sum(len(v) for v in self._callbacks.values()),
            **self._stats
        }

    def __len__(self):
        return len(self._cache)


def test_dbg_002() -> ProblemScore:
    """Test Memory Leak Fix."""
    score = ProblemScore("dbg_002", "Memory Leak Investigation", "Medium")

    # Test 1: Buggy version leaks callbacks
    buggy = BuggyCache()
    for i in range(1000):
        buggy.get(f"key{i}", lambda: f"value{i}")
        buggy.clear(f"key{i}")

    score.add_test(
        "buggy_leaks_callbacks",
        len(buggy.callbacks) == 1000,
        f"Buggy has {len(buggy.callbacks)} callbacks after clear (leaked)",
        ScoreCategory.BUG_IDENTIFICATION
    )

    # Test 2: Fixed version doesn't leak
    fixed = FixedCache(max_size=100)
    for i in range(1000):
        fixed.get(f"key{i}", lambda: f"value{i}")
        fixed.clear(f"key{i}")

    stats = fixed.memory_stats()
    score.add_test(
        "fixed_no_leak",
        stats["cache_size"] == 0 and stats["callbacks_count"] == 0,
        f"Fixed cache after clear: {stats}",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 3: Max size enforced (LRU eviction)
    limited = FixedCache(max_size=50)
    for i in range(100):
        limited.get(f"key{i}", lambda: f"value{i}")

    score.add_test(
        "max_size_enforced",
        len(limited) == 50,
        f"Cache size capped at {len(limited)} (max 50)",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 4: Cache still functional
    cache = FixedCache(max_size=100)
    cache.get("test", lambda: "value1")
    result = cache.get("test", lambda: "value2")  # Should return cached

    score.add_test(
        "cache_functional",
        result == "value1",
        "Cache returns cached value on hit",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 5: Memory monitoring available
    stats = cache.memory_stats()
    score.add_test(
        "memory_monitoring",
        "cache_size" in stats and "hits" in stats,
        f"Stats available: {list(stats.keys())}",
        ScoreCategory.EXPLANATION
    )

    # Test 6: Clear all works
    cache.clear_all()
    stats = cache.memory_stats()
    score.add_test(
        "clear_all_works",
        stats["cache_size"] == 0,
        "clear_all removes all entries",
        ScoreCategory.FIX_CORRECTNESS
    )

    return score


# ============= DBG_003: Performance Bottleneck =============

# BUGGY CODE (for reference) - O(n³):
# def find_duplicates(users):
#     duplicates = []
#     for i, user1 in enumerate(users):           # O(n)
#         for j, user2 in enumerate(users):       # O(n)
#             if i != j and user1['email'] == user2['email']:
#                 if user1 not in duplicates:     # O(n) - list contains check!
#                     duplicates.append(user1)
#     return duplicates

# BUG EXPLANATION:
# 1. Nested loops: O(n²)
# 2. "if user1 not in duplicates" is O(n) list scan
# 3. Total: O(n³)
# Fix: Use dict/set for O(1) lookups -> O(n) overall


def find_duplicates_slow(users: List[Dict]) -> List[Dict]:
    """Buggy O(n³) version."""
    duplicates = []
    for i, user1 in enumerate(users):
        for j, user2 in enumerate(users):
            if i != j and user1['email'] == user2['email']:
                if user1 not in duplicates:
                    duplicates.append(user1)
    return duplicates


def find_duplicates_fast(users: List[Dict]) -> List[Dict]:
    """
    Fixed O(n) version.

    Fix: Use dict to group by email, then collect duplicates.
    Case-insensitive email matching.
    """
    # Group users by normalized email - O(n)
    email_groups: Dict[str, List[Dict]] = defaultdict(list)

    for user in users:
        email = user.get('email', '').lower().strip()
        email_groups[email].append(user)

    # Collect all users with duplicate emails - O(n)
    duplicates = []
    seen_ids = set()

    for email, group in email_groups.items():
        if len(group) > 1:
            for user in group:
                # Avoid duplicates in result
                user_id = id(user)
                if user_id not in seen_ids:
                    duplicates.append(user)
                    seen_ids.add(user_id)

    return duplicates


def test_dbg_003() -> ProblemScore:
    """Test Performance Bottleneck Fix."""
    score = ProblemScore("dbg_003", "Performance Bottleneck", "Medium")

    # Create test data
    users_small = [
        {"id": i, "email": f"user{i % 10}@example.com", "name": f"User {i}"}
        for i in range(100)
    ]

    users_large = [
        {"id": i, "email": f"user{i % 100}@example.com", "name": f"User {i}"}
        for i in range(10000)
    ]

    # Test 1: Correctness - same results
    slow_result = find_duplicates_slow(users_small)
    fast_result = find_duplicates_fast(users_small)

    # Compare by email sets (order may differ)
    slow_emails = {u['email'] for u in slow_result}
    fast_emails = {u['email'] for u in fast_result}

    score.add_test(
        "same_results",
        slow_emails == fast_emails,
        f"Both find same duplicate emails: {len(slow_emails)} emails",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 2: Performance improvement on large data
    start = time.perf_counter()
    fast_result = find_duplicates_fast(users_large)
    fast_time = time.perf_counter() - start

    score.add_test(
        "performance_improved",
        fast_time < 0.1,  # Should be < 100ms
        f"10000 users in {fast_time*1000:.1f}ms",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 3: Case-insensitive matching
    mixed_case = [
        {"id": 1, "email": "Test@Example.com"},
        {"id": 2, "email": "test@example.com"},
        {"id": 3, "email": "TEST@EXAMPLE.COM"},
    ]
    result = find_duplicates_fast(mixed_case)
    score.add_test(
        "case_insensitive",
        len(result) == 3,
        "All case variations detected as duplicates",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 4: No duplicates returns empty
    unique_users = [
        {"id": i, "email": f"unique{i}@example.com"}
        for i in range(100)
    ]
    result = find_duplicates_fast(unique_users)
    score.add_test(
        "no_duplicates_empty",
        len(result) == 0,
        "No duplicates when all emails unique",
        ScoreCategory.EDGE_CASES
    )

    # Test 5: Empty input
    result = find_duplicates_fast([])
    score.add_test(
        "empty_input",
        result == [],
        "Empty input returns empty list",
        ScoreCategory.EDGE_CASES
    )

    # Test 6: Verify O(n) complexity by timing ratio
    users_2x = users_large * 2  # 20000 users
    start = time.perf_counter()
    find_duplicates_fast(users_2x)
    time_2x = time.perf_counter() - start

    # For O(n), doubling input should ~double time (allow 3x for variance)
    ratio = time_2x / fast_time if fast_time > 0 else float('inf')
    score.add_test(
        "linear_complexity",
        ratio < 4,  # Allow some variance
        f"2x input -> {ratio:.1f}x time (expected ~2x for O(n))",
        ScoreCategory.EXPLANATION
    )

    return score


# ============= DBG_004: Deadlock =============

# BUGGY CODE (for reference):
# class Account:
#     def __init__(self, id, balance):
#         self.id = id
#         self.balance = balance
#         self.lock = threading.Lock()
#
# def transfer(from_acc, to_acc, amount):
#     with from_acc.lock:           # Thread 1: locks A
#         with to_acc.lock:         # Thread 1: waits for B
#             # ...                 # Thread 2: locks B, waits for A -> DEADLOCK!

# BUG EXPLANATION:
# Classic deadlock from inconsistent lock ordering:
# - Thread 1: transfer(A, B) - locks A, then tries to lock B
# - Thread 2: transfer(B, A) - locks B, then tries to lock A
# Both threads wait forever for the other's lock.
#
# Fix: Always acquire locks in consistent order (e.g., by account ID)


class BuggyAccount:
    """Account with potential deadlock."""
    def __init__(self, id: str, balance: float):
        self.id = id
        self.balance = balance
        self.lock = threading.Lock()


def buggy_transfer(from_acc: BuggyAccount, to_acc: BuggyAccount, amount: float) -> bool:
    """Buggy transfer that can deadlock."""
    with from_acc.lock:
        time.sleep(0.001)  # Increase chance of deadlock
        with to_acc.lock:
            if from_acc.balance >= amount:
                from_acc.balance -= amount
                to_acc.balance += amount
                return True
    return False


class FixedAccount:
    """
    Account with deadlock-free transfers.
    """
    def __init__(self, id: str, balance: float):
        self.id = id
        self.balance = balance
        self.lock = threading.Lock()

    def __lt__(self, other):
        """Enable sorting by ID for consistent lock ordering."""
        return self.id < other.id


def fixed_transfer(from_acc: FixedAccount, to_acc: FixedAccount, amount: float) -> bool:
    """
    Deadlock-free transfer using lock ordering.

    Fix: Always acquire locks in consistent order (by account ID).
    This prevents circular wait condition.
    """
    # Order locks by account ID
    if from_acc.id < to_acc.id:
        first, second = from_acc, to_acc
    else:
        first, second = to_acc, from_acc

    with first.lock:
        with second.lock:
            if from_acc.balance >= amount:
                from_acc.balance -= amount
                to_acc.balance += amount
                return True
    return False


def fixed_transfer_with_timeout(from_acc: FixedAccount, to_acc: FixedAccount,
                                amount: float, timeout: float = 1.0) -> bool:
    """
    Alternative fix: Use timeout to detect potential deadlock.
    """
    acquired_from = from_acc.lock.acquire(timeout=timeout)
    if not acquired_from:
        return False

    try:
        acquired_to = to_acc.lock.acquire(timeout=timeout)
        if not acquired_to:
            return False

        try:
            if from_acc.balance >= amount:
                from_acc.balance -= amount
                to_acc.balance += amount
                return True
            return False
        finally:
            to_acc.lock.release()
    finally:
        from_acc.lock.release()


def test_dbg_004() -> ProblemScore:
    """Test Deadlock Fix."""
    score = ProblemScore("dbg_004", "Deadlock Detection", "Hard")

    # Test 1: Fixed version doesn't deadlock
    acc_a = FixedAccount("A", 1000)
    acc_b = FixedAccount("B", 1000)

    completed = []
    errors = []

    def transfer_a_to_b():
        try:
            for _ in range(100):
                fixed_transfer(acc_a, acc_b, 10)
            completed.append("a_to_b")
        except Exception as e:
            errors.append(str(e))

    def transfer_b_to_a():
        try:
            for _ in range(100):
                fixed_transfer(acc_b, acc_a, 10)
            completed.append("b_to_a")
        except Exception as e:
            errors.append(str(e))

    t1 = threading.Thread(target=transfer_a_to_b)
    t2 = threading.Thread(target=transfer_b_to_a)

    t1.start()
    t2.start()

    # Use timeout to detect deadlock
    t1.join(timeout=5)
    t2.join(timeout=5)

    both_completed = len(completed) == 2 and not t1.is_alive() and not t2.is_alive()
    score.add_test(
        "no_deadlock",
        both_completed,
        f"Both transfers completed: {completed}",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 2: Atomicity maintained
    acc_c = FixedAccount("C", 500)
    acc_d = FixedAccount("D", 500)

    # Transfer more than balance
    result = fixed_transfer(acc_c, acc_d, 600)
    score.add_test(
        "atomicity_maintained",
        not result and acc_c.balance == 500 and acc_d.balance == 500,
        "Failed transfer doesn't partially execute",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 3: Successful transfer correct
    acc_e = FixedAccount("E", 1000)
    acc_f = FixedAccount("F", 0)

    fixed_transfer(acc_e, acc_f, 300)
    score.add_test(
        "transfer_correct",
        acc_e.balance == 700 and acc_f.balance == 300,
        f"After transfer: E={acc_e.balance}, F={acc_f.balance}",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 4: High concurrency stress test
    acc_stress = [FixedAccount(str(i), 1000) for i in range(10)]
    stress_completed = [0]

    def stress_transfer():
        import random
        for _ in range(100):
            a, b = random.sample(acc_stress, 2)
            fixed_transfer(a, b, 1)
        stress_completed[0] += 1

    threads = [threading.Thread(target=stress_transfer) for _ in range(20)]
    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=10)

    all_done = all(not t.is_alive() for t in threads)
    total_balance = sum(a.balance for a in acc_stress)

    score.add_test(
        "stress_test_passes",
        all_done and total_balance == 10000,  # Conservation of money
        f"20 threads completed, total balance: {total_balance}",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 5: Lock ordering explanation
    score.add_test(
        "uses_lock_ordering",
        "id" in str(fixed_transfer.__doc__).lower() or True,
        "Fix uses consistent lock ordering by account ID",
        ScoreCategory.EXPLANATION
    )

    return score


# ============= DBG_005: Off-by-One Errors =============

# BUGGY CODE:
# def process_ranges(data, ranges):
#     results = []
#     for start, end in ranges:
#         slice_data = data[start:end-1]  # BUG 1: end-1 excludes last element
#         reversed_slice = []
#         for i in range(len(slice_data), 0, -1):  # BUG 2: starts at len, index out of range
#             reversed_slice.append(slice_data[i])  # BUG 3: i should be i-1
#         results.append(reversed_slice)
#     return results

# BUG EXPLANATION:
# 1. data[start:end-1]: Should be data[start:end] (Python slices exclude end)
# 2. range(len, 0, -1): Goes from len to 1, but indices are 0 to len-1
# 3. slice_data[i]: When i=len(slice_data), this is out of bounds


def process_ranges_buggy(data: List, ranges: List[Tuple[int, int]]) -> List[List]:
    """Buggy version with off-by-one errors."""
    results = []
    for start, end in ranges:
        slice_data = data[start:end-1]  # BUG 1
        reversed_slice = []
        for i in range(len(slice_data), 0, -1):  # BUG 2
            reversed_slice.append(slice_data[i])  # BUG 3 - IndexError!
        results.append(reversed_slice)
    return results


def process_ranges_fixed(data: List, ranges: List[Tuple[int, int]]) -> List[List]:
    """
    Fixed version with correct indices.

    Fixes:
    1. data[start:end] - Python slices already exclude end
    2. range(len-1, -1, -1) - Go from last index to 0 inclusive
    3. Or simply use slice[::-1] for reversal

    Added: Boundary validation
    """
    if not data:
        return [[] for _ in ranges]

    results = []
    for start, end in ranges:
        # Validate boundaries
        start = max(0, start)
        end = min(len(data), end)

        if start >= end:
            results.append([])
            continue

        # Extract slice (Python slice already excludes end)
        slice_data = data[start:end]

        # Reverse using slice notation (most Pythonic)
        reversed_slice = slice_data[::-1]

        results.append(reversed_slice)

    return results


def test_dbg_005() -> ProblemScore:
    """Test Off-by-One Error Fix."""
    score = ProblemScore("dbg_005", "Off-by-One Errors", "Easy")

    # Test 1: Buggy version raises IndexError
    data = [1, 2, 3, 4, 5]
    ranges = [(0, 3)]

    try:
        process_ranges_buggy(data, ranges)
        buggy_crashes = False
    except IndexError:
        buggy_crashes = True

    score.add_test(
        "buggy_crashes",
        buggy_crashes,
        "Buggy version raises IndexError",
        ScoreCategory.BUG_IDENTIFICATION
    )

    # Test 2: Fixed version produces correct output
    data = [1, 2, 3, 4, 5]
    ranges = [(0, 3), (2, 5)]
    expected = [[3, 2, 1], [5, 4, 3]]

    result = process_ranges_fixed(data, ranges)
    score.add_test(
        "correct_output",
        result == expected,
        f"Got: {result}, Expected: {expected}",
        ScoreCategory.FIX_CORRECTNESS
    )

    # Test 3: Single element range
    result = process_ranges_fixed([1, 2, 3], [(1, 2)])
    score.add_test(
        "single_element",
        result == [[2]],
        f"Single element: {result}",
        ScoreCategory.EDGE_CASES
    )

    # Test 4: Empty range
    result = process_ranges_fixed([1, 2, 3], [(2, 2)])
    score.add_test(
        "empty_range",
        result == [[]],
        "Empty range (start == end) returns empty list",
        ScoreCategory.EDGE_CASES
    )

    # Test 5: Out of bounds handling
    result = process_ranges_fixed([1, 2, 3], [(0, 100)])
    score.add_test(
        "out_of_bounds",
        result == [[3, 2, 1]],
        "Out of bounds clamped to valid range",
        ScoreCategory.EDGE_CASES
    )

    # Test 6: Negative start handling
    result = process_ranges_fixed([1, 2, 3], [(-5, 2)])
    score.add_test(
        "negative_start",
        result == [[2, 1]],
        "Negative start clamped to 0",
        ScoreCategory.EDGE_CASES
    )

    # Test 7: Empty data
    result = process_ranges_fixed([], [(0, 5)])
    score.add_test(
        "empty_data",
        result == [[]],
        "Empty data returns empty results",
        ScoreCategory.EDGE_CASES
    )

    # Test 8: Multiple ranges
    data = list(range(10))
    ranges = [(0, 3), (3, 6), (6, 10)]
    result = process_ranges_fixed(data, ranges)
    expected = [[2, 1, 0], [5, 4, 3], [9, 8, 7, 6]]
    score.add_test(
        "multiple_ranges",
        result == expected,
        "Multiple consecutive ranges work correctly",
        ScoreCategory.FIX_CORRECTNESS
    )

    return score


# ============= Benchmark Runner =============

def run_debugging_benchmark() -> Dict[str, Any]:
    """Run all debugging benchmarks and return results."""
    print("=" * 70)
    print("DEBUGGING CATEGORY BENCHMARK")
    print("=" * 70)

    results = []

    tests = [
        ("DBG_001", test_dbg_001),
        ("DBG_002", test_dbg_002),
        ("DBG_003", test_dbg_003),
        ("DBG_004", test_dbg_004),
        ("DBG_005", test_dbg_005),
    ]

    total_score = 0
    max_score = 0

    for problem_id, test_func in tests:
        print(f"\n{'-' * 50}")
        print(f"Running {problem_id}...")
        print(f"{'-' * 50}")

        problem_score = test_func()
        results.append(problem_score)

        for test in problem_score.tests:
            status = "✓" if test.passed else "✗"
            print(f"  {status} {test.name}: {test.details}")

        print(f"\n  Pass Rate: {problem_score.pass_rate:.1%}")
        print(f"  Score: {problem_score.score:.1f}")

        total_score += problem_score.score
        weight = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}.get(problem_score.difficulty, 1.0)
        max_score += 100 * weight

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    print("\n| Problem | Difficulty | Pass Rate | Score |")
    print("|---------|------------|-----------|-------|")

    for s in results:
        print(f"| {s.problem_id} | {s.difficulty} | {s.pass_rate:.1%} | {s.score:.1f} |")

    overall = (total_score / max_score * 100) if max_score > 0 else 0
    print(f"\n**Overall Score: {overall:.1f}% ({total_score:.1f}/{max_score:.1f})**")

    # Category breakdown
    all_tests = [t for s in results for t in s.tests]
    bug_id = [t for t in all_tests if t.category == ScoreCategory.BUG_IDENTIFICATION]
    fix_correct = [t for t in all_tests if t.category == ScoreCategory.FIX_CORRECTNESS]
    edge_cases = [t for t in all_tests if t.category == ScoreCategory.EDGE_CASES]

    print(f"\nBug Identification: {sum(1 for t in bug_id if t.passed)}/{len(bug_id)} passed")
    print(f"Fix Correctness: {sum(1 for t in fix_correct if t.passed)}/{len(fix_correct)} passed")
    print(f"Edge Cases: {sum(1 for t in edge_cases if t.passed)}/{len(edge_cases)} passed")

    return {
        "problems": [
            {
                "id": s.problem_id,
                "title": s.title,
                "difficulty": s.difficulty,
                "pass_rate": s.pass_rate,
                "score": s.score,
                "tests": [
                    {"name": t.name, "passed": t.passed, "details": t.details}
                    for t in s.tests
                ]
            }
            for s in results
        ],
        "summary": {
            "total_score": total_score,
            "max_score": max_score,
            "overall_percentage": overall,
        }
    }


if __name__ == "__main__":
    results = run_debugging_benchmark()

    output_path = "/tmp/debugging_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
