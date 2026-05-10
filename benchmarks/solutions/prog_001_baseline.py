"""
Benchmark Solution: PROG_001 - Implement LRU Cache
Configuration: BASELINE (Claude Code only)

Requirements:
- O(1) get and put operations
- Evict least recently used when at capacity
- Include type hints and docstrings
"""

from typing import Optional, Dict
from collections import OrderedDict


class LRUCache:
    """
    Least Recently Used (LRU) Cache implementation.

    Uses OrderedDict for O(1) operations:
    - get: O(1) lookup + move_to_end
    - put: O(1) insert/update + optional eviction

    Attributes:
        capacity: Maximum number of items to store
    """

    def __init__(self, capacity: int) -> None:
        """
        Initialize LRU cache with given capacity.

        Args:
            capacity: Maximum number of key-value pairs to store

        Raises:
            ValueError: If capacity is less than 1
        """
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")
        self.capacity = capacity
        self._cache: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        """
        Get value for key if it exists, otherwise return -1.

        Accessing a key marks it as most recently used.

        Args:
            key: The key to look up

        Returns:
            The value if key exists, -1 otherwise
        """
        if key not in self._cache:
            return -1

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: int, value: int) -> None:
        """
        Insert or update key-value pair.

        If cache is at capacity and key is new, evicts the
        least recently used item (first item in OrderedDict).

        Args:
            key: The key to insert/update
            value: The value to store
        """
        if key in self._cache:
            # Update existing and move to end
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            # Check capacity before inserting
            if len(self._cache) >= self.capacity:
                # Evict LRU (first item)
                self._cache.popitem(last=False)
            self._cache[key] = value

    def __len__(self) -> int:
        """Return current number of items in cache."""
        return len(self._cache)

    def __repr__(self) -> str:
        """Return string representation of cache state."""
        return f"LRUCache(capacity={self.capacity}, items={len(self._cache)})"


def run_test_cases() -> bool:
    """Run the provided test cases and verify results."""
    all_passed = True

    # Test case 1
    operations1 = ["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"]
    args1 = [[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]]
    expected1 = [None, None, None, 1, None, -1, None, -1, 3, 4]

    cache = None
    results1 = []
    for op, arg in zip(operations1, args1):
        if op == "LRUCache":
            cache = LRUCache(arg[0])
            results1.append(None)
        elif op == "get":
            results1.append(cache.get(arg[0]))
        elif op == "put":
            cache.put(arg[0], arg[1])
            results1.append(None)

    if results1 == expected1:
        print("Test 1: PASSED")
    else:
        print(f"Test 1: FAILED")
        print(f"  Expected: {expected1}")
        print(f"  Got:      {results1}")
        all_passed = False

    # Test case 2
    operations2 = ["LRUCache", "put", "get", "put", "get", "get"]
    args2 = [[1], [2, 1], [2], [3, 2], [2], [3]]
    expected2 = [None, None, 1, None, -1, 2]

    cache = None
    results2 = []
    for op, arg in zip(operations2, args2):
        if op == "LRUCache":
            cache = LRUCache(arg[0])
            results2.append(None)
        elif op == "get":
            results2.append(cache.get(arg[0]))
        elif op == "put":
            cache.put(arg[0], arg[1])
            results2.append(None)

    if results2 == expected2:
        print("Test 2: PASSED")
    else:
        print(f"Test 2: FAILED")
        print(f"  Expected: {expected2}")
        print(f"  Got:      {results2}")
        all_passed = False

    return all_passed


if __name__ == "__main__":
    print("Running LRU Cache Tests...")
    print("-" * 40)

    passed = run_test_cases()

    print("-" * 40)
    if passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")

    # Additional demo
    print("\nDemo:")
    cache = LRUCache(3)
    cache.put(1, 100)
    cache.put(2, 200)
    cache.put(3, 300)
    print(f"After put(1,100), put(2,200), put(3,300): {cache}")
    print(f"get(1) = {cache.get(1)}")  # Returns 100, marks 1 as recent
    cache.put(4, 400)  # Evicts key 2 (LRU)
    print(f"After put(4,400): {cache}")
    print(f"get(2) = {cache.get(2)}")  # Returns -1 (evicted)
    print(f"get(3) = {cache.get(3)}")  # Returns 300
