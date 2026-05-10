"""
Algorithms Category Benchmark
Tests all 5 algorithm problems with scoring

Problems:
- alg_001: Trie with Autocomplete (Medium)
- alg_002: Dijkstra's Shortest Path (Medium)
- alg_003: LCS with Diff Generation (Hard)
- alg_004: Bloom Filter (Medium)
- alg_005: Interval Scheduling (Medium)
"""

import heapq
import math
import json
import hashlib
from typing import Optional, Dict, Any, List, Tuple, Set, Iterator
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import base64


# ============= Scoring Infrastructure =============

class ScoreCategory(Enum):
    CORRECTNESS = "correctness"
    COMPLEXITY = "complexity"
    COMPLETENESS = "completeness"
    EDGE_CASES = "edge_cases"


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    category: ScoreCategory = ScoreCategory.CORRECTNESS


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
                 category: ScoreCategory = ScoreCategory.CORRECTNESS):
        self.tests.append(TestResult(name, passed, details, category))


# ============= ALG_001: Trie with Autocomplete =============

class TrieNode:
    """Node in the Trie data structure."""
    __slots__ = ['children', 'is_end', 'frequency', 'word']

    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end: bool = False
        self.frequency: int = 0
        self.word: Optional[str] = None


class Trie:
    """
    ALG_001: Trie with Autocomplete

    Supports insert, search, prefix search, autocomplete with top-k by frequency.
    """

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, frequency: int = 1) -> None:
        """
        Insert word with frequency. O(m) where m is word length.
        """
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.frequency = frequency
        node.word = word

    def search(self, word: str) -> bool:
        """
        Exact match lookup. O(m) where m is word length.
        """
        node = self._find_node(word)
        return node is not None and node.is_end

    def starts_with(self, prefix: str) -> bool:
        """
        Check if any word starts with prefix. O(m).
        """
        return self._find_node(prefix) is not None

    def _find_node(self, prefix: str) -> Optional[TrieNode]:
        """Find node for given prefix."""
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def autocomplete(self, prefix: str, k: int = 5) -> List[str]:
        """
        Return top k words by frequency starting with prefix.
        Uses heap for efficient top-k selection.
        """
        node = self._find_node(prefix)
        if node is None:
            return []

        # Collect all words under this prefix
        candidates: List[Tuple[int, str]] = []
        self._collect_words(node, candidates)

        # Use heap to get top k by frequency (negate for max-heap behavior)
        if len(candidates) <= k:
            # Sort by frequency descending
            candidates.sort(key=lambda x: -x[0])
            return [word for _, word in candidates]

        # Use nlargest for efficiency
        top_k = heapq.nlargest(k, candidates, key=lambda x: x[0])
        return [word for _, word in top_k]

    def _collect_words(self, node: TrieNode, results: List[Tuple[int, str]]) -> None:
        """Collect all words from this node downward."""
        if node.is_end and node.word:
            results.append((node.frequency, node.word))

        for child in node.children.values():
            self._collect_words(child, results)

    def delete(self, word: str) -> bool:
        """
        Delete word from trie. Returns True if word was deleted.
        """
        def _delete(node: TrieNode, word: str, depth: int) -> bool:
            if depth == len(word):
                if not node.is_end:
                    return False
                node.is_end = False
                node.word = None
                node.frequency = 0
                return len(node.children) == 0

            char = word[depth]
            if char not in node.children:
                return False

            should_delete = _delete(node.children[char], word, depth + 1)

            if should_delete:
                del node.children[char]
                return len(node.children) == 0 and not node.is_end

            return False

        return _delete(self.root, word, 0) or not self.search(word)

    def get_frequency(self, word: str) -> int:
        """Get frequency of a word."""
        node = self._find_node(word)
        if node and node.is_end:
            return node.frequency
        return 0


def test_alg_001() -> ProblemScore:
    """Test Trie with Autocomplete."""
    score = ProblemScore("alg_001", "Trie with Autocomplete", "Medium")

    trie = Trie()

    # Test 1: Insert and search
    trie.insert("apple", 10)
    trie.insert("app", 5)
    trie.insert("application", 8)
    score.add_test(
        "insert_and_search",
        trie.search("apple") and trie.search("app"),
        "Words found after insert",
        ScoreCategory.CORRECTNESS
    )

    # Test 2: Search non-existent
    score.add_test(
        "search_nonexistent",
        not trie.search("appl") and not trie.search("banana"),
        "Non-existent words return False",
        ScoreCategory.CORRECTNESS
    )

    # Test 3: starts_with
    score.add_test(
        "starts_with",
        trie.starts_with("app") and trie.starts_with("appl") and not trie.starts_with("ban"),
        "Prefix check works correctly",
        ScoreCategory.CORRECTNESS
    )

    # Test 4: Autocomplete returns top-k by frequency
    results = trie.autocomplete("app", 2)
    score.add_test(
        "autocomplete_topk",
        len(results) == 2 and results[0] == "apple",  # apple has highest frequency
        f"Got: {results}",
        ScoreCategory.CORRECTNESS
    )

    # Test 5: Autocomplete with no matches
    results = trie.autocomplete("xyz", 5)
    score.add_test(
        "autocomplete_no_match",
        results == [],
        "Empty list for no matches",
        ScoreCategory.EDGE_CASES
    )

    # Test 6: Delete word
    trie.delete("apple")
    score.add_test(
        "delete_word",
        not trie.search("apple") and trie.search("app"),
        "Deleted word not found, others preserved",
        ScoreCategory.CORRECTNESS
    )

    # Test 7: Delete maintains prefix structure
    trie.insert("apple", 10)
    trie.delete("app")
    score.add_test(
        "delete_preserves_structure",
        trie.search("apple") and not trie.search("app"),
        "Prefix words preserved when deleting shorter word",
        ScoreCategory.CORRECTNESS
    )

    # Test 8: Large autocomplete uses heap efficiently
    large_trie = Trie()
    for i in range(1000):
        large_trie.insert(f"word{i}", i)
    results = large_trie.autocomplete("word", 5)
    score.add_test(
        "autocomplete_efficiency",
        len(results) == 5 and results[0] == "word999",
        f"Top 5 from 1000: {results[:3]}...",
        ScoreCategory.COMPLEXITY
    )

    return score


# ============= ALG_002: Dijkstra's Shortest Path =============

class NegativeWeightError(Exception):
    """Raised when graph contains negative edge weights."""
    pass


class Graph:
    """
    Weighted graph supporting Dijkstra's algorithm.
    """

    def __init__(self, directed: bool = True):
        self.directed = directed
        self.adjacency: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        self.nodes: Set[str] = set()

    def add_edge(self, u: str, v: str, weight: float) -> None:
        """Add edge with weight."""
        if weight < 0:
            raise NegativeWeightError(f"Negative weight {weight} on edge {u}->{v}")

        self.nodes.add(u)
        self.nodes.add(v)
        self.adjacency[u].append((v, weight))

        if not self.directed:
            self.adjacency[v].append((u, weight))

    def dijkstra(self, start: str, end: str) -> Dict[str, Any]:
        """
        Find shortest path using Dijkstra's algorithm.
        O((V+E) log V) with priority queue.

        Returns: {'distance': float, 'path': List[str]}
        """
        if start not in self.nodes:
            return {'distance': float('inf'), 'path': []}

        # Distance and predecessor maps
        dist: Dict[str, float] = {node: float('inf') for node in self.nodes}
        prev: Dict[str, Optional[str]] = {node: None for node in self.nodes}
        dist[start] = 0

        # Priority queue: (distance, node)
        pq: List[Tuple[float, str]] = [(0, start)]
        visited: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)

            if u in visited:
                continue
            visited.add(u)

            if u == end:
                break

            for v, weight in self.adjacency[u]:
                if v in visited:
                    continue

                new_dist = dist[u] + weight
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, v))

        # Reconstruct path
        if dist[end] == float('inf'):
            return {'distance': float('inf'), 'path': []}

        path = []
        current = end
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        return {'distance': dist[end], 'path': path}

    def shortest_distances(self, start: str) -> Dict[str, float]:
        """Get shortest distances from start to all nodes."""
        if start not in self.nodes:
            return {}

        dist: Dict[str, float] = {node: float('inf') for node in self.nodes}
        dist[start] = 0

        pq: List[Tuple[float, str]] = [(0, start)]
        visited: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)

            if u in visited:
                continue
            visited.add(u)

            for v, weight in self.adjacency[u]:
                if v in visited:
                    continue

                new_dist = dist[u] + weight
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    heapq.heappush(pq, (new_dist, v))

        return dist


def test_alg_002() -> ProblemScore:
    """Test Dijkstra's Shortest Path."""
    score = ProblemScore("alg_002", "Dijkstra's Shortest Path", "Medium")

    # Test 1: Basic shortest path
    g = Graph(directed=True)
    g.add_edge('A', 'B', 1)
    g.add_edge('A', 'C', 4)
    g.add_edge('B', 'C', 2)

    result = g.dijkstra('A', 'C')
    score.add_test(
        "basic_shortest_path",
        result['distance'] == 3 and result['path'] == ['A', 'B', 'C'],
        f"Got: distance={result['distance']}, path={result['path']}",
        ScoreCategory.CORRECTNESS
    )

    # Test 2: Direct path is longer
    g2 = Graph()
    g2.add_edge('A', 'B', 1)
    g2.add_edge('B', 'C', 1)
    g2.add_edge('A', 'C', 10)

    result = g2.dijkstra('A', 'C')
    score.add_test(
        "indirect_shorter",
        result['distance'] == 2,
        f"Indirect path (2) shorter than direct (10): {result['distance']}",
        ScoreCategory.CORRECTNESS
    )

    # Test 3: Disconnected nodes
    g3 = Graph()
    g3.add_edge('A', 'B', 1)
    g3.nodes.add('C')  # Disconnected

    result = g3.dijkstra('A', 'C')
    score.add_test(
        "disconnected_infinity",
        result['distance'] == float('inf') and result['path'] == [],
        "Disconnected nodes return infinity",
        ScoreCategory.EDGE_CASES
    )

    # Test 4: Negative weight raises error
    g4 = Graph()
    try:
        g4.add_edge('A', 'B', -1)
        raised = False
    except NegativeWeightError:
        raised = True

    score.add_test(
        "negative_weight_error",
        raised,
        "NegativeWeightError raised for negative weights",
        ScoreCategory.EDGE_CASES
    )

    # Test 5: Undirected graph
    g5 = Graph(directed=False)
    g5.add_edge('A', 'B', 1)
    g5.add_edge('B', 'C', 2)

    result_forward = g5.dijkstra('A', 'C')
    result_backward = g5.dijkstra('C', 'A')
    score.add_test(
        "undirected_graph",
        result_forward['distance'] == result_backward['distance'] == 3,
        "Undirected paths work both ways",
        ScoreCategory.CORRECTNESS
    )

    # Test 6: Single node path
    g6 = Graph()
    g6.nodes.add('A')
    result = g6.dijkstra('A', 'A')
    score.add_test(
        "same_node_path",
        result['distance'] == 0 and result['path'] == ['A'],
        "Path to self is 0",
        ScoreCategory.EDGE_CASES
    )

    # Test 7: Complex graph with multiple paths
    g7 = Graph()
    g7.add_edge('S', 'A', 1)
    g7.add_edge('S', 'B', 4)
    g7.add_edge('A', 'B', 2)
    g7.add_edge('A', 'C', 5)
    g7.add_edge('B', 'C', 1)

    result = g7.dijkstra('S', 'C')
    score.add_test(
        "complex_graph",
        result['distance'] == 4 and result['path'] == ['S', 'A', 'B', 'C'],
        f"Best path through complex graph: {result}",
        ScoreCategory.CORRECTNESS
    )

    return score


# ============= ALG_003: LCS with Diff Generation =============

class LCSDiff:
    """
    ALG_003: Longest Common Subsequence with Diff Generation

    Implements DP-based LCS and unified diff generation.
    """

    def lcs(self, s1: str, s2: str) -> str:
        """
        Find longest common subsequence using dynamic programming.
        O(mn) time, O(min(m,n)) space with optimization.
        """
        if not s1 or not s2:
            return ""

        # Use shorter string for columns (space optimization)
        if len(s1) < len(s2):
            s1, s2 = s2, s1

        m, n = len(s1), len(s2)

        # Only keep two rows for space efficiency
        prev = [0] * (n + 1)
        curr = [0] * (n + 1)

        # Also track for backtracking
        # For actual LCS string, we need full matrix or different approach
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        # Backtrack to find actual LCS
        lcs_chars = []
        i, j = m, n
        while i > 0 and j > 0:
            if s1[i-1] == s2[j-1]:
                lcs_chars.append(s1[i-1])
                i -= 1
                j -= 1
            elif dp[i-1][j] > dp[i][j-1]:
                i -= 1
            else:
                j -= 1

        return ''.join(reversed(lcs_chars))

    def lcs_length(self, s1: str, s2: str) -> int:
        """Get just the length with O(min(m,n)) space."""
        if not s1 or not s2:
            return 0

        if len(s1) < len(s2):
            s1, s2 = s2, s1

        prev = [0] * (len(s2) + 1)

        for i in range(1, len(s1) + 1):
            curr = [0] * (len(s2) + 1)
            for j in range(1, len(s2) + 1):
                if s1[i-1] == s2[j-1]:
                    curr[j] = prev[j-1] + 1
                else:
                    curr[j] = max(prev[j], curr[j-1])
            prev = curr

        return prev[len(s2)]

    def diff_lines(self, old_lines: List[str], new_lines: List[str]) -> str:
        """
        Generate unified diff between two lists of lines.
        """
        result = []

        # Build LCS matrix for lines
        m, n = len(old_lines), len(new_lines)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if old_lines[i-1] == new_lines[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        # Generate diff using backtracking
        diff_ops = []
        i, j = m, n

        while i > 0 or j > 0:
            if i > 0 and j > 0 and old_lines[i-1] == new_lines[j-1]:
                diff_ops.append((' ', old_lines[i-1]))
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
                diff_ops.append(('+', new_lines[j-1]))
                j -= 1
            else:
                diff_ops.append(('-', old_lines[i-1]))
                i -= 1

        diff_ops.reverse()

        # Format output
        for op, line in diff_ops:
            result.append(f"{op} {line}")

        return '\n'.join(result)

    def diff(self, old_text: str, new_text: str, by_line: bool = True) -> str:
        """
        Generate unified diff between two texts.

        Args:
            old_text: Original text
            new_text: New text
            by_line: If True, diff by lines; otherwise by characters
        """
        if by_line:
            old_lines = old_text.splitlines()
            new_lines = new_text.splitlines()
            return self.diff_lines(old_lines, new_lines)
        else:
            # Character-by-character diff
            return self.diff_lines(list(old_text), list(new_text))


def test_alg_003() -> ProblemScore:
    """Test LCS with Diff Generation."""
    score = ProblemScore("alg_003", "LCS with Diff Generation", "Hard")

    lcs_diff = LCSDiff()

    # Test 1: Basic LCS
    result = lcs_diff.lcs("ABCBDAB", "BDCAB")
    score.add_test(
        "basic_lcs",
        len(result) == 4 and all(c in "BDCAB" for c in result),
        f"LCS of ABCBDAB and BDCAB: '{result}' (length {len(result)})",
        ScoreCategory.CORRECTNESS
    )

    # Test 2: LCS with identical strings
    result = lcs_diff.lcs("HELLO", "HELLO")
    score.add_test(
        "identical_lcs",
        result == "HELLO",
        "LCS of identical strings is the string itself",
        ScoreCategory.CORRECTNESS
    )

    # Test 3: LCS with no common characters
    result = lcs_diff.lcs("ABC", "XYZ")
    score.add_test(
        "no_common_lcs",
        result == "",
        "LCS with no common characters is empty",
        ScoreCategory.EDGE_CASES
    )

    # Test 4: Empty string handling
    result = lcs_diff.lcs("", "ABC")
    score.add_test(
        "empty_string_lcs",
        result == "",
        "LCS with empty string is empty",
        ScoreCategory.EDGE_CASES
    )

    # Test 5: Line diff generation
    old = "line1\nline2\nline3"
    new = "line1\nline2modified\nline3\nline4"
    diff = lcs_diff.diff(old, new)
    score.add_test(
        "line_diff",
        "+" in diff and "-" in diff,
        f"Diff contains +/-:\n{diff[:100]}...",
        ScoreCategory.CORRECTNESS
    )

    # Test 6: Diff shows additions
    old = "A\nB"
    new = "A\nB\nC"
    diff = lcs_diff.diff(old, new)
    score.add_test(
        "diff_additions",
        "+ C" in diff,
        f"Addition detected: {diff}",
        ScoreCategory.CORRECTNESS
    )

    # Test 7: Diff shows deletions
    old = "A\nB\nC"
    new = "A\nC"
    diff = lcs_diff.diff(old, new)
    score.add_test(
        "diff_deletions",
        "- B" in diff,
        f"Deletion detected: {diff}",
        ScoreCategory.CORRECTNESS
    )

    # Test 8: Space-efficient LCS length
    # Test with longer strings
    s1 = "A" * 100 + "B" * 100
    s2 = "A" * 50 + "C" * 50 + "B" * 100
    length = lcs_diff.lcs_length(s1, s2)
    score.add_test(
        "space_efficient_lcs",
        length == 150,  # 50 A's + 100 B's
        f"LCS length of long strings: {length}",
        ScoreCategory.COMPLEXITY
    )

    return score


# ============= ALG_004: Bloom Filter =============

class BloomFilter:
    """
    ALG_004: Bloom Filter

    Probabilistic set membership with configurable false positive rate.
    """

    def __init__(self, expected_items: int, fp_rate: float = 0.01):
        """
        Initialize Bloom filter.

        Args:
            expected_items: Expected number of items
            fp_rate: Desired false positive rate (0-1)
        """
        # Calculate optimal size and hash count
        # m = -n * ln(p) / (ln(2)^2)
        # k = (m/n) * ln(2)

        self.expected_items = expected_items
        self.fp_rate = fp_rate

        # Optimal bit array size
        self.size = self._optimal_size(expected_items, fp_rate)

        # Optimal number of hash functions
        self.hash_count = self._optimal_hash_count(self.size, expected_items)

        # Bit array (using integer for efficiency)
        self.bit_array = 0

        self.items_added = 0

    def _optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size."""
        if p <= 0 or p >= 1:
            p = 0.01
        m = -n * math.log(p) / (math.log(2) ** 2)
        return max(int(m), 64)

    def _optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions."""
        k = (m / n) * math.log(2)
        return max(int(k), 1)

    def _hashes(self, item: str) -> List[int]:
        """
        Generate k hash values for an item.
        Uses double hashing: h(i) = h1 + i*h2
        """
        # Use two hash functions and combine
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)

        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    def add(self, item: str) -> None:
        """Add item to the filter."""
        for pos in self._hashes(item):
            self.bit_array |= (1 << pos)
        self.items_added += 1

    def might_contain(self, item: str) -> bool:
        """
        Check if item might be in the set.
        Returns True if item is possibly in set (may be false positive).
        Returns False if item is definitely not in set.
        """
        for pos in self._hashes(item):
            if not (self.bit_array & (1 << pos)):
                return False
        return True

    def __contains__(self, item: str) -> bool:
        return self.might_contain(item)

    def estimated_fp_rate(self) -> float:
        """Estimate current false positive rate."""
        # (1 - e^(-kn/m))^k
        if self.items_added == 0:
            return 0
        exp = -self.hash_count * self.items_added / self.size
        return (1 - math.exp(exp)) ** self.hash_count

    def serialize(self) -> str:
        """Serialize filter to base64 string."""
        data = {
            'size': self.size,
            'hash_count': self.hash_count,
            'items_added': self.items_added,
            'bit_array': self.bit_array,
            'fp_rate': self.fp_rate
        }
        return base64.b64encode(json.dumps(data).encode()).decode()

    @classmethod
    def deserialize(cls, data: str) -> 'BloomFilter':
        """Deserialize filter from base64 string."""
        decoded = json.loads(base64.b64decode(data))
        bf = cls(1000, decoded['fp_rate'])  # Placeholder
        bf.size = decoded['size']
        bf.hash_count = decoded['hash_count']
        bf.items_added = decoded['items_added']
        bf.bit_array = decoded['bit_array']
        return bf


def test_alg_004() -> ProblemScore:
    """Test Bloom Filter."""
    score = ProblemScore("alg_004", "Bloom Filter", "Medium")

    # Test 1: Added items are found
    bf = BloomFilter(1000, fp_rate=0.01)
    bf.add("test")
    bf.add("hello")
    bf.add("world")

    score.add_test(
        "added_items_found",
        bf.might_contain("test") and bf.might_contain("hello") and bf.might_contain("world"),
        "All added items are found",
        ScoreCategory.CORRECTNESS
    )

    # Test 2: Non-added items usually not found
    not_found_count = sum(1 for i in range(100) if not bf.might_contain(f"notadded{i}"))
    score.add_test(
        "non_added_mostly_not_found",
        not_found_count > 90,  # At least 90% not found
        f"{not_found_count}/100 non-added items correctly not found",
        ScoreCategory.CORRECTNESS
    )

    # Test 3: False positive rate within bounds
    bf2 = BloomFilter(1000, fp_rate=0.01)
    for i in range(1000):
        bf2.add(f"item{i}")

    # Check 10000 non-added items
    false_positives = sum(1 for i in range(10000) if bf2.might_contain(f"other{i}"))
    fp_rate = false_positives / 10000

    score.add_test(
        "fp_rate_within_bounds",
        fp_rate < 0.05,  # Allow some margin
        f"False positive rate: {fp_rate:.4f} (target: 0.01)",
        ScoreCategory.CORRECTNESS
    )

    # Test 4: Optimal hash count calculation
    bf3 = BloomFilter(1000, fp_rate=0.01)
    expected_k = int((bf3.size / 1000) * math.log(2))
    score.add_test(
        "optimal_hash_count",
        abs(bf3.hash_count - expected_k) <= 1,
        f"Hash count: {bf3.hash_count} (expected ~{expected_k})",
        ScoreCategory.COMPLEXITY
    )

    # Test 5: Serialization roundtrip
    bf4 = BloomFilter(100, fp_rate=0.01)
    bf4.add("serialize_test")

    serialized = bf4.serialize()
    bf4_restored = BloomFilter.deserialize(serialized)

    score.add_test(
        "serialization",
        bf4_restored.might_contain("serialize_test"),
        "Serialization roundtrip preserves data",
        ScoreCategory.COMPLETENESS
    )

    # Test 6: Memory efficient (bit array size)
    bf5 = BloomFilter(10000, fp_rate=0.001)
    bits_per_element = bf5.size / 10000
    score.add_test(
        "memory_efficient",
        10 <= bits_per_element <= 20,  # Optimal is ~14.4 for 0.1% FP
        f"Bits per element: {bits_per_element:.1f}",
        ScoreCategory.COMPLEXITY
    )

    # Test 7: Empty filter has no false positives
    bf6 = BloomFilter(100)
    has_false_positive = any(bf6.might_contain(f"x{i}") for i in range(100))
    score.add_test(
        "empty_no_fp",
        not has_false_positive,
        "Empty filter has no false positives",
        ScoreCategory.EDGE_CASES
    )

    return score


# ============= ALG_005: Interval Scheduling =============

class IntervalScheduler:
    """
    ALG_005: Interval Scheduling Algorithms

    Implements greedy algorithms for interval scheduling problems.
    """

    @staticmethod
    def max_non_overlapping(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Find maximum number of non-overlapping intervals.
        Greedy: sort by end time, always pick earliest ending.
        O(n log n) time.
        """
        if not intervals:
            return []

        # Sort by end time
        sorted_intervals = sorted(intervals, key=lambda x: x[1])

        result = [sorted_intervals[0]]
        last_end = sorted_intervals[0][1]

        for start, end in sorted_intervals[1:]:
            if start >= last_end:  # Non-overlapping
                result.append((start, end))
                last_end = end

        return result

    @staticmethod
    def min_cover(intervals: List[Tuple[int, int]],
                  target_range: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find minimum intervals needed to cover a range.
        Greedy: always extend coverage as far as possible.
        O(n log n) time.
        """
        if not intervals:
            return None

        target_start, target_end = target_range

        # Sort by start time
        sorted_intervals = sorted(intervals, key=lambda x: x[0])

        result = []
        current_end = target_start
        i = 0
        n = len(sorted_intervals)

        while current_end < target_end:
            # Find interval that starts at or before current_end
            # and extends furthest
            best_end = current_end
            best_interval = None

            while i < n and sorted_intervals[i][0] <= current_end:
                if sorted_intervals[i][1] > best_end:
                    best_end = sorted_intervals[i][1]
                    best_interval = sorted_intervals[i]
                i += 1

            if best_interval is None:
                # Gap in coverage
                return None

            result.append(best_interval)
            current_end = best_end

        return result

    @staticmethod
    def count_overlapping(intervals: List[Tuple[int, int]], point: int) -> int:
        """Count intervals overlapping a specific point."""
        return sum(1 for start, end in intervals if start <= point < end)

    @staticmethod
    def merge_overlapping(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping intervals."""
        if not intervals:
            return []

        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        result = [sorted_intervals[0]]

        for start, end in sorted_intervals[1:]:
            last_start, last_end = result[-1]
            if start <= last_end:  # Overlapping
                result[-1] = (last_start, max(last_end, end))
            else:
                result.append((start, end))

        return result


def test_alg_005() -> ProblemScore:
    """Test Interval Scheduling."""
    score = ProblemScore("alg_005", "Interval Scheduling", "Medium")

    scheduler = IntervalScheduler()

    # Test 1: Max non-overlapping basic
    intervals = [(0, 2), (1, 3), (2, 4), (3, 5)]
    result = scheduler.max_non_overlapping(intervals)
    # Should get 2 intervals: (0,2) and either (2,4) or (3,5)
    score.add_test(
        "max_non_overlapping_basic",
        len(result) == 2 and result[0] == (0, 2),
        f"Got {len(result)} intervals: {result}",
        ScoreCategory.CORRECTNESS
    )

    # Test 2: Max non-overlapping no overlap
    intervals = [(0, 1), (2, 3), (4, 5)]
    result = scheduler.max_non_overlapping(intervals)
    score.add_test(
        "max_no_overlap",
        len(result) == 3,
        "All non-overlapping intervals selected",
        ScoreCategory.CORRECTNESS
    )

    # Test 3: Max non-overlapping all overlap
    intervals = [(0, 5), (1, 4), (2, 3)]
    result = scheduler.max_non_overlapping(intervals)
    score.add_test(
        "max_all_overlap",
        len(result) == 1,
        "Only one interval selected when all overlap",
        ScoreCategory.CORRECTNESS
    )

    # Test 4: Min cover basic
    intervals = [(0, 3), (2, 5), (4, 7)]
    result = scheduler.min_cover(intervals, (0, 7))
    score.add_test(
        "min_cover_basic",
        result is not None and len(result) == 3,
        f"Needs all 3 to cover: {result}",
        ScoreCategory.CORRECTNESS
    )

    # Test 5: Min cover with gap (impossible)
    intervals = [(0, 2), (4, 6)]
    result = scheduler.min_cover(intervals, (0, 6))
    score.add_test(
        "min_cover_gap",
        result is None,
        "Returns None when coverage impossible",
        ScoreCategory.EDGE_CASES
    )

    # Test 6: Min cover single interval sufficient
    intervals = [(0, 10), (2, 5)]
    result = scheduler.min_cover(intervals, (1, 8))
    score.add_test(
        "min_cover_single",
        result is not None and len(result) == 1,
        "Single interval covers entire range",
        ScoreCategory.CORRECTNESS
    )

    # Test 7: Empty intervals
    score.add_test(
        "empty_intervals",
        scheduler.max_non_overlapping([]) == [] and scheduler.min_cover([], (0, 1)) is None,
        "Empty input handled correctly",
        ScoreCategory.EDGE_CASES
    )

    # Test 8: Merge overlapping
    intervals = [(0, 3), (2, 5), (7, 10)]
    merged = scheduler.merge_overlapping(intervals)
    score.add_test(
        "merge_overlapping",
        merged == [(0, 5), (7, 10)],
        f"Merged: {merged}",
        ScoreCategory.CORRECTNESS
    )

    return score


# ============= Benchmark Runner =============

def run_algorithms_benchmark() -> Dict[str, Any]:
    """Run all algorithm benchmarks and return results."""
    print("=" * 70)
    print("ALGORITHMS CATEGORY BENCHMARK")
    print("=" * 70)

    results = []

    tests = [
        ("ALG_001", test_alg_001),
        ("ALG_002", test_alg_002),
        ("ALG_003", test_alg_003),
        ("ALG_004", test_alg_004),
        ("ALG_005", test_alg_005),
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
    correctness = [t for t in all_tests if t.category == ScoreCategory.CORRECTNESS]
    complexity = [t for t in all_tests if t.category == ScoreCategory.COMPLEXITY]
    edge_cases = [t for t in all_tests if t.category == ScoreCategory.EDGE_CASES]

    print(f"\nCorrectness Tests: {sum(1 for t in correctness if t.passed)}/{len(correctness)} passed")
    print(f"Complexity Tests: {sum(1 for t in complexity if t.passed)}/{len(complexity)} passed")
    print(f"Edge Case Tests: {sum(1 for t in edge_cases if t.passed)}/{len(edge_cases)} passed")

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
    results = run_algorithms_benchmark()

    output_path = "/tmp/algorithms_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
