#!/usr/bin/env python3
"""
Testing & Quality Assurance Benchmark
Tests: Calculator Test Suite, Mocking, Property-Based Testing, Integration Tests, Coverage

Run: python benchmarks/solutions/testing_benchmark.py
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from unittest.mock import Mock, MagicMock, patch, call
from functools import wraps
import random


# =============================================================================
# Problem 1: Calculator Test Suite (Easy)
# =============================================================================

class Calculator:
    """Calculator class to be tested."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ValueError('Division by zero')
        return a / b

    def power(self, base, exp):
        return base ** exp


class CalculatorTestSuite:
    """Comprehensive test suite for Calculator."""

    def __init__(self):
        self.calc = Calculator()
        self.results = []

    def _test(self, name: str, test_fn: Callable) -> bool:
        """Run a single test and record result."""
        try:
            test_fn()
            self.results.append({"name": name, "passed": True, "error": None})
            return True
        except AssertionError as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False
        except Exception as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False

    def run_all(self) -> List[dict]:
        """Run all tests."""
        self.results = []

        # Positive numbers
        self._test("add_positive", lambda: self._assert_eq(self.calc.add(2, 3), 5))
        self._test("subtract_positive", lambda: self._assert_eq(self.calc.subtract(5, 3), 2))
        self._test("multiply_positive", lambda: self._assert_eq(self.calc.multiply(4, 5), 20))
        self._test("divide_positive", lambda: self._assert_eq(self.calc.divide(10, 2), 5))
        self._test("power_positive", lambda: self._assert_eq(self.calc.power(2, 3), 8))

        # Negative numbers
        self._test("add_negative", lambda: self._assert_eq(self.calc.add(-2, -3), -5))
        self._test("subtract_negative", lambda: self._assert_eq(self.calc.subtract(-5, -3), -2))
        self._test("multiply_negative", lambda: self._assert_eq(self.calc.multiply(-4, 5), -20))
        self._test("divide_negative", lambda: self._assert_eq(self.calc.divide(-10, 2), -5))
        self._test("power_negative_base", lambda: self._assert_eq(self.calc.power(-2, 3), -8))

        # Zero operations
        self._test("add_zero", lambda: self._assert_eq(self.calc.add(5, 0), 5))
        self._test("subtract_zero", lambda: self._assert_eq(self.calc.subtract(5, 0), 5))
        self._test("multiply_zero", lambda: self._assert_eq(self.calc.multiply(5, 0), 0))
        self._test("power_zero_exp", lambda: self._assert_eq(self.calc.power(5, 0), 1))

        # Floating point
        self._test("add_float", lambda: self._assert_close(self.calc.add(0.1, 0.2), 0.3))
        self._test("divide_float", lambda: self._assert_close(self.calc.divide(1, 3), 0.333333))
        self._test("multiply_float", lambda: self._assert_close(self.calc.multiply(0.5, 0.5), 0.25))

        # Error conditions
        self._test("divide_by_zero", self._test_divide_by_zero)
        self._test("power_negative_exp", lambda: self._assert_close(self.calc.power(2, -1), 0.5))

        # Edge cases
        self._test("large_numbers", lambda: self._assert_eq(self.calc.add(10**15, 10**15), 2 * 10**15))
        self._test("identity_add", lambda: self._assert_eq(self.calc.add(0, 0), 0))

        return self.results

    def _assert_eq(self, actual, expected):
        assert actual == expected, f"Expected {expected}, got {actual}"

    def _assert_close(self, actual, expected, tolerance=1e-5):
        assert abs(actual - expected) < tolerance, f"Expected ~{expected}, got {actual}"

    def _test_divide_by_zero(self):
        try:
            self.calc.divide(5, 0)
            raise AssertionError("Expected ValueError for division by zero")
        except ValueError as e:
            assert "zero" in str(e).lower()


# =============================================================================
# Problem 2: Mock External Dependencies (Medium)
# =============================================================================

class PaymentError(Exception):
    pass


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    error: Optional[str] = None


class OrderService:
    """Service with external dependencies to test."""

    def __init__(self, db, payment_api, email_service):
        self.db = db
        self.payment_api = payment_api
        self.email_service = email_service

    def create_order(self, user_id, items):
        # Calculate total
        total = sum(item['price'] * item['quantity'] for item in items)

        # Charge payment
        payment_result = self.payment_api.charge(user_id, total)
        if not payment_result.success:
            raise PaymentError(payment_result.error)

        # Save order
        order = self.db.orders.create({
            'user_id': user_id,
            'items': items,
            'total': total,
            'payment_id': payment_result.transaction_id,
            'created_at': datetime.now()
        })

        # Send confirmation
        self.email_service.send_order_confirmation(user_id, order)

        return order


class OrderServiceTests:
    """Tests for OrderService with mocked dependencies."""

    def __init__(self):
        self.results = []

    def _create_mocks(self):
        """Create mock objects for dependencies."""
        db = MagicMock()
        payment_api = MagicMock()
        email_service = MagicMock()
        return db, payment_api, email_service

    def _test(self, name: str, test_fn: Callable) -> bool:
        """Run a single test."""
        try:
            test_fn()
            self.results.append({"name": name, "passed": True, "error": None})
            return True
        except Exception as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False

    def run_all(self) -> List[dict]:
        """Run all tests."""
        self.results = []

        self._test("successful_order", self._test_successful_order)
        self._test("payment_failure", self._test_payment_failure)
        self._test("email_sent", self._test_email_sent)
        self._test("order_saved", self._test_order_saved)
        self._test("correct_total", self._test_correct_total)
        self._test("payment_called_with_total", self._test_payment_called_with_total)

        return self.results

    def _test_successful_order(self):
        """Test successful order creation."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(
            success=True,
            transaction_id="tx_123"
        )
        db.orders.create.return_value = {"id": 1, "status": "created"}

        service = OrderService(db, payment_api, email)
        items = [{"price": 10, "quantity": 2}]

        order = service.create_order("user1", items)

        assert order is not None
        assert db.orders.create.called

    def _test_payment_failure(self):
        """Test payment failure handling."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(
            success=False,
            error="Card declined"
        )

        service = OrderService(db, payment_api, email)

        try:
            service.create_order("user1", [{"price": 10, "quantity": 1}])
            raise AssertionError("Expected PaymentError")
        except PaymentError as e:
            assert "Card declined" in str(e)

        # Email should NOT be sent on failure
        assert not email.send_order_confirmation.called

    def _test_email_sent(self):
        """Test confirmation email is sent."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(success=True, transaction_id="tx_123")
        db.orders.create.return_value = {"id": 1}

        service = OrderService(db, payment_api, email)
        service.create_order("user1", [{"price": 10, "quantity": 1}])

        email.send_order_confirmation.assert_called_once()
        call_args = email.send_order_confirmation.call_args
        assert call_args[0][0] == "user1"

    def _test_order_saved(self):
        """Test order is saved to database."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(success=True, transaction_id="tx_123")

        service = OrderService(db, payment_api, email)
        items = [{"price": 10, "quantity": 2}]
        service.create_order("user1", items)

        db.orders.create.assert_called_once()
        saved_order = db.orders.create.call_args[0][0]
        assert saved_order["user_id"] == "user1"
        assert saved_order["items"] == items
        assert saved_order["payment_id"] == "tx_123"

    def _test_correct_total(self):
        """Test total is calculated correctly."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(success=True, transaction_id="tx_123")

        service = OrderService(db, payment_api, email)
        items = [
            {"price": 10, "quantity": 2},  # 20
            {"price": 5, "quantity": 3}    # 15
        ]
        service.create_order("user1", items)

        saved_order = db.orders.create.call_args[0][0]
        assert saved_order["total"] == 35

    def _test_payment_called_with_total(self):
        """Test payment API is called with correct total."""
        db, payment_api, email = self._create_mocks()

        payment_api.charge.return_value = PaymentResult(success=True, transaction_id="tx_123")

        service = OrderService(db, payment_api, email)
        items = [{"price": 25, "quantity": 4}]  # 100
        service.create_order("user1", items)

        payment_api.charge.assert_called_once_with("user1", 100)


# =============================================================================
# Problem 3: Property-Based Testing (Medium)
# =============================================================================

def custom_sort(items, key=None, reverse=False):
    """Sort items with custom key function."""
    return sorted(items, key=key, reverse=reverse)


def filter_range(items, min_val=None, max_val=None):
    """Filter items within range."""
    result = items
    if min_val is not None:
        result = [x for x in result if x >= min_val]
    if max_val is not None:
        result = [x for x in result if x <= max_val]
    return result


def unique(items):
    """Return unique items preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


class PropertyBasedTests:
    """Property-based tests for sorting/filtering functions."""

    def __init__(self, num_iterations=100):
        self.num_iterations = num_iterations
        self.results = []

    def _test(self, name: str, test_fn: Callable) -> bool:
        """Run a property test multiple times."""
        try:
            for _ in range(self.num_iterations):
                test_fn()
            self.results.append({"name": name, "passed": True, "iterations": self.num_iterations})
            return True
        except AssertionError as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False

    def _generate_int_list(self, max_len=20, min_val=-100, max_val=100):
        """Generate random integer list."""
        length = random.randint(0, max_len)
        return [random.randint(min_val, max_val) for _ in range(length)]

    def run_all(self) -> List[dict]:
        """Run all property tests."""
        self.results = []

        # Sort properties
        self._test("sort_idempotent", self._test_sort_idempotent)
        self._test("sort_length_preserved", self._test_sort_length_preserved)
        self._test("sort_ordered", self._test_sort_ordered)
        self._test("sort_same_elements", self._test_sort_same_elements)

        # Filter properties
        self._test("filter_subset", self._test_filter_subset)
        self._test("filter_bounds_respected", self._test_filter_bounds_respected)

        # Unique properties
        self._test("unique_no_duplicates", self._test_unique_no_duplicates)
        self._test("unique_subset", self._test_unique_subset)
        self._test("unique_preserves_order", self._test_unique_preserves_order)

        return self.results

    def _test_sort_idempotent(self):
        """Sorting twice gives same result as sorting once."""
        items = self._generate_int_list()
        once = custom_sort(items)
        twice = custom_sort(once)
        assert once == twice, f"Sort not idempotent: {items}"

    def _test_sort_length_preserved(self):
        """Sorting preserves length."""
        items = self._generate_int_list()
        result = custom_sort(items)
        assert len(result) == len(items), f"Length changed: {len(items)} -> {len(result)}"

    def _test_sort_ordered(self):
        """Sorted list is in order."""
        items = self._generate_int_list()
        result = custom_sort(items)
        for i in range(len(result) - 1):
            assert result[i] <= result[i+1], f"Not ordered at index {i}: {result}"

    def _test_sort_same_elements(self):
        """Sorted list has same elements."""
        items = self._generate_int_list()
        result = custom_sort(items)
        assert sorted(items) == sorted(result), "Elements changed"

    def _test_filter_subset(self):
        """Filtered result is subset of input."""
        items = self._generate_int_list()
        min_val = random.randint(-50, 0)
        max_val = random.randint(0, 50)
        result = filter_range(items, min_val, max_val)
        for item in result:
            assert item in items, f"{item} not in original list"

    def _test_filter_bounds_respected(self):
        """All filtered items are within bounds."""
        items = self._generate_int_list()
        min_val = random.randint(-50, 0)
        max_val = random.randint(0, 50)
        result = filter_range(items, min_val, max_val)
        for item in result:
            assert min_val <= item <= max_val, f"{item} out of bounds [{min_val}, {max_val}]"

    def _test_unique_no_duplicates(self):
        """Unique result has no duplicates."""
        items = self._generate_int_list()
        result = unique(items)
        assert len(result) == len(set(result)), "Duplicates found in unique result"

    def _test_unique_subset(self):
        """Unique result is subset of input."""
        items = self._generate_int_list()
        result = unique(items)
        for item in result:
            assert item in items, f"{item} not in original list"

    def _test_unique_preserves_order(self):
        """First occurrence order is preserved."""
        items = self._generate_int_list()
        result = unique(items)

        # Build expected order
        seen = set()
        expected = []
        for item in items:
            if item not in seen:
                seen.add(item)
                expected.append(item)

        assert result == expected, f"Order not preserved: {result} vs {expected}"


# =============================================================================
# Problem 4: Integration Test with Mock Containers (Hard)
# =============================================================================

class MockRedis:
    """Mock Redis for testing."""

    def __init__(self):
        self._data = {}
        self._ttl = {}

    def get(self, key):
        if key in self._ttl and self._ttl[key] < time.time():
            del self._data[key]
            del self._ttl[key]
            return None
        return self._data.get(key)

    def setex(self, key, ttl, value):
        self._data[key] = value
        self._ttl[key] = time.time() + ttl

    def delete(self, key):
        self._data.pop(key, None)
        self._ttl.pop(key, None)

    def flushall(self):
        self._data.clear()
        self._ttl.clear()


class MockDB:
    """Mock database for testing."""

    def __init__(self):
        self._data = {}
        self._counter = 0

    def query(self, sql, *args):
        if "SELECT" in sql and "id = ?" in sql:
            return self._data.get(args[0])
        return None

    def execute(self, sql, *args):
        if "INSERT" in sql:
            self._counter += 1
            user = {"id": self._counter, "name": args[0], "email": args[1]}
            self._data[self._counter] = user
            return user
        return None

    def clear(self):
        self._data.clear()
        self._counter = 0


class UserRepository:
    """Repository with cache and database."""

    def __init__(self, db, cache):
        self.db = db
        self.cache = cache

    def get_user(self, user_id):
        # Try cache first
        cached = self.cache.get(f'user:{user_id}')
        if cached:
            return json.loads(cached)

        # Query database
        user = self.db.query('SELECT * FROM users WHERE id = ?', user_id)
        if user:
            self.cache.setex(f'user:{user_id}', 300, json.dumps(user))
        return user

    def create_user(self, data):
        user = self.db.execute(
            'INSERT INTO users (name, email) VALUES (?, ?)',
            data['name'], data['email']
        )
        return user

    def invalidate_cache(self, user_id):
        self.cache.delete(f'user:{user_id}')


class IntegrationTests:
    """Integration tests for UserRepository."""

    def __init__(self):
        self.results = []

    def _setup(self):
        """Create fresh mocks for each test."""
        db = MockDB()
        cache = MockRedis()
        return db, cache

    def _test(self, name: str, test_fn: Callable) -> bool:
        """Run a test."""
        try:
            test_fn()
            self.results.append({"name": name, "passed": True})
            return True
        except Exception as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False

    def run_all(self) -> List[dict]:
        """Run all tests."""
        self.results = []

        self._test("create_user", self._test_create_user)
        self._test("get_user_cache_miss", self._test_get_user_cache_miss)
        self._test("get_user_cache_hit", self._test_get_user_cache_hit)
        self._test("invalidate_cache", self._test_invalidate_cache)
        self._test("user_not_found", self._test_user_not_found)
        self._test("cache_isolation", self._test_cache_isolation)

        return self.results

    def _test_create_user(self):
        """Test user creation."""
        db, cache = self._setup()
        repo = UserRepository(db, cache)

        user = repo.create_user({"name": "Alice", "email": "alice@test.com"})

        assert user is not None
        assert user["name"] == "Alice"
        assert user["email"] == "alice@test.com"
        assert "id" in user

    def _test_get_user_cache_miss(self):
        """Test fetching user when not in cache."""
        db, cache = self._setup()
        repo = UserRepository(db, cache)

        # Create user directly in DB
        user = repo.create_user({"name": "Bob", "email": "bob@test.com"})

        # Fetch should hit DB and populate cache
        fetched = repo.get_user(user["id"])

        assert fetched is not None
        assert fetched["name"] == "Bob"

        # Now cache should have it
        cached = cache.get(f'user:{user["id"]}')
        assert cached is not None

    def _test_get_user_cache_hit(self):
        """Test fetching user from cache."""
        db, cache = self._setup()
        repo = UserRepository(db, cache)

        # Pre-populate cache
        user_data = {"id": 1, "name": "Charlie", "email": "charlie@test.com"}
        cache.setex("user:1", 300, json.dumps(user_data))

        # Fetch should hit cache, not DB
        fetched = repo.get_user(1)

        assert fetched is not None
        assert fetched["name"] == "Charlie"

    def _test_invalidate_cache(self):
        """Test cache invalidation."""
        db, cache = self._setup()
        repo = UserRepository(db, cache)

        # Pre-populate cache
        cache.setex("user:1", 300, json.dumps({"id": 1, "name": "Dave"}))

        # Invalidate
        repo.invalidate_cache(1)

        # Cache should be empty
        assert cache.get("user:1") is None

    def _test_user_not_found(self):
        """Test fetching non-existent user."""
        db, cache = self._setup()
        repo = UserRepository(db, cache)

        result = repo.get_user(999)

        assert result is None

    def _test_cache_isolation(self):
        """Test that tests are isolated."""
        db1, cache1 = self._setup()
        db2, cache2 = self._setup()

        cache1.setex("key", 300, "value1")

        # cache2 should not have key
        assert cache2.get("key") is None


# =============================================================================
# Problem 5: Test Coverage Analysis (Easy)
# =============================================================================

def process_data(data, options=None):
    """Function with multiple branches to test."""
    options = options or {}

    if not data:
        return {'error': 'No data provided'}

    result = []
    for item in data:
        if options.get('skip_none') and item is None:
            continue

        if options.get('transform'):
            item = options['transform'](item)

        if options.get('filter'):
            if not options['filter'](item):
                continue

        result.append(item)

    if options.get('sort'):
        result.sort(key=options.get('sort_key'))

    if options.get('limit'):
        result = result[:options['limit']]

    return {'data': result, 'count': len(result)}


class CoverageTests:
    """Tests designed for 100% branch coverage."""

    def __init__(self):
        self.results = []
        self.coverage_map = {}

    def _test(self, name: str, branch: str, test_fn: Callable) -> bool:
        """Run a test and track coverage."""
        try:
            test_fn()
            self.results.append({"name": name, "passed": True, "branch": branch})
            self.coverage_map[branch] = True
            return True
        except Exception as e:
            self.results.append({"name": name, "passed": False, "error": str(e)})
            return False

    def run_all(self) -> List[dict]:
        """Run all tests."""
        self.results = []
        self.coverage_map = {}

        # Empty data path
        self._test("empty_data", "data_empty", self._test_empty_data)

        # Basic path
        self._test("basic_data", "data_present", self._test_basic_data)

        # skip_none option
        self._test("skip_none_true", "skip_none_branch", self._test_skip_none)

        # transform option
        self._test("transform_applied", "transform_branch", self._test_transform)

        # filter option
        self._test("filter_applied", "filter_branch", self._test_filter)

        # sort option
        self._test("sort_applied", "sort_branch", self._test_sort)

        # sort with key
        self._test("sort_with_key", "sort_key_branch", self._test_sort_with_key)

        # limit option
        self._test("limit_applied", "limit_branch", self._test_limit)

        # Combinations
        self._test("all_options", "combined", self._test_all_options)

        return self.results

    def _test_empty_data(self):
        """Test empty data returns error. Covers: if not data"""
        result = process_data(None)
        assert result == {'error': 'No data provided'}

        result = process_data([])
        assert result == {'error': 'No data provided'}

    def _test_basic_data(self):
        """Test basic data processing. Covers: data present, no options"""
        result = process_data([1, 2, 3])
        assert result == {'data': [1, 2, 3], 'count': 3}

    def _test_skip_none(self):
        """Test skip_none option. Covers: skip_none branch"""
        result = process_data([1, None, 2, None, 3], {'skip_none': True})
        assert result == {'data': [1, 2, 3], 'count': 3}

        # Without skip_none, None stays
        result = process_data([1, None, 2], {'skip_none': False})
        assert None in result['data']

    def _test_transform(self):
        """Test transform option. Covers: transform branch"""
        result = process_data([1, 2, 3], {'transform': lambda x: x * 2})
        assert result == {'data': [2, 4, 6], 'count': 3}

    def _test_filter(self):
        """Test filter option. Covers: filter branch"""
        result = process_data([1, 2, 3, 4, 5], {'filter': lambda x: x > 2})
        assert result == {'data': [3, 4, 5], 'count': 3}

    def _test_sort(self):
        """Test sort option. Covers: sort branch"""
        result = process_data([3, 1, 2], {'sort': True})
        assert result == {'data': [1, 2, 3], 'count': 3}

    def _test_sort_with_key(self):
        """Test sort with key. Covers: sort_key branch"""
        result = process_data(['bb', 'a', 'ccc'], {'sort': True, 'sort_key': len})
        assert result == {'data': ['a', 'bb', 'ccc'], 'count': 3}

    def _test_limit(self):
        """Test limit option. Covers: limit branch"""
        result = process_data([1, 2, 3, 4, 5], {'limit': 3})
        assert result == {'data': [1, 2, 3], 'count': 3}

    def _test_all_options(self):
        """Test all options combined."""
        result = process_data(
            [5, None, 3, 1, 4, 2],
            {
                'skip_none': True,
                'transform': lambda x: x * 10,
                'filter': lambda x: x >= 20,
                'sort': True,
                'limit': 3
            }
        )
        # 5,3,1,4,2 -> 50,30,10,40,20 -> filter >= 20: 50,30,40,20 -> sort: 20,30,40,50 -> limit 3: 20,30,40
        assert result == {'data': [20, 30, 40], 'count': 3}

    def get_coverage(self) -> dict:
        """Get coverage information."""
        all_branches = [
            "data_empty", "data_present", "skip_none_branch",
            "transform_branch", "filter_branch", "sort_branch",
            "sort_key_branch", "limit_branch", "combined"
        ]
        covered = [b for b in all_branches if self.coverage_map.get(b)]
        return {
            "branches_total": len(all_branches),
            "branches_covered": len(covered),
            "coverage_percent": (len(covered) / len(all_branches)) * 100
        }


# =============================================================================
# Benchmark Runner
# =============================================================================

def run_tests() -> dict:
    """Run all benchmark tests and return results."""
    results = {
        "problems": [],
        "summary": {}
    }

    total_score = 0
    max_score = 0
    all_tests = []

    # Problem 1: Calculator Test Suite (Easy - 100 points)
    print("\n" + "="*60)
    print("Problem 1: Calculator Test Suite")
    print("="*60)

    calc_tests = CalculatorTestSuite()
    test_results = calc_tests.run_all()

    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    for t in test_results:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  [{status}] {t['name']}")

    problem1_score = (passed / total) * 100
    results["problems"].append({
        "id": "tst_001",
        "title": "Calculator Test Suite",
        "difficulty": "Easy",
        "pass_rate": passed / total,
        "score": problem1_score,
        "tests": [{"name": t["name"], "passed": t["passed"], "details": t.get("error", "OK")} for t in test_results]
    })
    total_score += problem1_score
    max_score += 100
    all_tests.extend([{"name": t["name"], "passed": t["passed"]} for t in test_results])

    # Problem 2: Mock External Dependencies (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 2: Mock External Dependencies")
    print("="*60)

    mock_tests = OrderServiceTests()
    test_results = mock_tests.run_all()

    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    for t in test_results:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  [{status}] {t['name']}")

    problem2_score = (passed / total) * 150
    results["problems"].append({
        "id": "tst_002",
        "title": "Mock External Dependencies",
        "difficulty": "Medium",
        "pass_rate": passed / total,
        "score": problem2_score,
        "tests": [{"name": t["name"], "passed": t["passed"], "details": t.get("error", "OK")} for t in test_results]
    })
    total_score += problem2_score
    max_score += 150
    all_tests.extend([{"name": t["name"], "passed": t["passed"]} for t in test_results])

    # Problem 3: Property-Based Testing (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 3: Property-Based Testing")
    print("="*60)

    prop_tests = PropertyBasedTests(num_iterations=50)
    test_results = prop_tests.run_all()

    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    for t in test_results:
        status = "PASS" if t["passed"] else "FAIL"
        iters = t.get("iterations", "")
        print(f"  [{status}] {t['name']} ({iters} iterations)" if iters else f"  [{status}] {t['name']}")

    problem3_score = (passed / total) * 150
    results["problems"].append({
        "id": "tst_003",
        "title": "Property-Based Testing",
        "difficulty": "Medium",
        "pass_rate": passed / total,
        "score": problem3_score,
        "tests": [{"name": t["name"], "passed": t["passed"], "details": f"{t.get('iterations', 0)} iterations"} for t in test_results]
    })
    total_score += problem3_score
    max_score += 150
    all_tests.extend([{"name": t["name"], "passed": t["passed"]} for t in test_results])

    # Problem 4: Integration Tests (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 4: Integration Tests")
    print("="*60)

    int_tests = IntegrationTests()
    test_results = int_tests.run_all()

    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    for t in test_results:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  [{status}] {t['name']}")

    problem4_score = (passed / total) * 200
    results["problems"].append({
        "id": "tst_004",
        "title": "Integration Tests",
        "difficulty": "Hard",
        "pass_rate": passed / total,
        "score": problem4_score,
        "tests": [{"name": t["name"], "passed": t["passed"], "details": t.get("error", "OK")} for t in test_results]
    })
    total_score += problem4_score
    max_score += 200
    all_tests.extend([{"name": t["name"], "passed": t["passed"]} for t in test_results])

    # Problem 5: Test Coverage Analysis (Easy - 100 points)
    print("\n" + "="*60)
    print("Problem 5: Test Coverage Analysis")
    print("="*60)

    cov_tests = CoverageTests()
    test_results = cov_tests.run_all()
    coverage = cov_tests.get_coverage()

    passed = sum(1 for t in test_results if t["passed"])
    total = len(test_results)

    for t in test_results:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  [{status}] {t['name']} (covers: {t.get('branch', 'N/A')})")

    print(f"\n  Coverage: {coverage['coverage_percent']:.1f}% ({coverage['branches_covered']}/{coverage['branches_total']} branches)")

    problem5_score = (passed / total) * 100
    results["problems"].append({
        "id": "tst_005",
        "title": "Test Coverage Analysis",
        "difficulty": "Easy",
        "pass_rate": passed / total,
        "score": problem5_score,
        "tests": [{"name": t["name"], "passed": t["passed"], "details": f"Branch: {t.get('branch', 'N/A')}"} for t in test_results],
        "coverage": coverage
    })
    total_score += problem5_score
    max_score += 100
    all_tests.extend([{"name": t["name"], "passed": t["passed"]} for t in test_results])

    # Summary
    passed_tests = sum(1 for t in all_tests if t["passed"])
    total_tests = len(all_tests)

    results["summary"] = {
        "total_score": total_score,
        "max_score": max_score,
        "overall_percentage": (total_score / max_score) * 100 if max_score > 0 else 0,
        "tests_passed": passed_tests,
        "tests_total": total_tests,
        "pass_rate": passed_tests / total_tests if total_tests > 0 else 0
    }

    return results


def main():
    print("="*60)
    print("TESTING & QUALITY ASSURANCE BENCHMARK")
    print("="*60)

    results = run_tests()

    # Print summary table
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\n| Problem | Difficulty | Pass Rate | Score |")
    print(f"|---------|------------|-----------|-------|")
    for p in results["problems"]:
        print(f"| {p['id']} | {p['difficulty']} | {p['pass_rate']*100:.1f}% | {p['score']:.1f} |")

    print(f"\n**Overall Score: {results['summary']['overall_percentage']:.1f}% ({results['summary']['total_score']:.1f}/{results['summary']['max_score']:.1f})**")
    print(f"**Tests: {results['summary']['tests_passed']}/{results['summary']['tests_total']} passed**")

    # Save results
    output_path = "/tmp/testing_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
