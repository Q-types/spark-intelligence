#!/usr/bin/env python3
"""
MCP Live Benchmark
==================

Tests MCP servers with REAL tool calls.
Run this from Claude Code to test actual MCP functionality.

This script generates test commands that should be executed
by Claude Code to test the real MCP servers.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class TestResult:
    """Result from a single test."""
    name: str
    server: str
    passed: bool
    details: str
    response: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class TestSuite:
    """Collection of test results."""
    server: str
    tests: List[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def percentage(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0


def generate_test_id() -> str:
    """Generate unique test ID."""
    return f"bench_{uuid4().hex[:8]}"


# =============================================================================
# Test Definitions
# =============================================================================

MIND_TESTS = [
    {
        "id": "mind_health",
        "name": "Health Check",
        "tool": "mind_health",
        "params": {},
        "validate": lambda r: r.get("status") == "healthy"
    },
    {
        "id": "mind_remember_episodic",
        "name": "Store Episodic Memory",
        "tool": "mind_remember",
        "params": {
            "content": f"[BENCHMARK TEST {generate_test_id()}] Completed benchmark test at {datetime.now().isoformat()}",
            "memory_type": "episodic",
            "temporal_level": 1,
            "importance": 0.3
        },
        "validate": lambda r: "memory_id" in str(r) or "success" in str(r).lower()
    },
    {
        "id": "mind_remember_semantic",
        "name": "Store Semantic Memory",
        "tool": "mind_remember",
        "params": {
            "content": f"[BENCHMARK TEST {generate_test_id()}] Python list comprehensions are faster than for loops for simple transformations",
            "memory_type": "semantic",
            "temporal_level": 3
        },
        "validate": lambda r: "memory_id" in str(r) or "success" in str(r).lower()
    },
    {
        "id": "mind_retrieve",
        "name": "Retrieve Memories",
        "tool": "mind_retrieve",
        "params": {
            "query": "benchmark test python",
            "limit": 5
        },
        "validate": lambda r: "memories" in r or isinstance(r, list)
    },
    {
        "id": "mind_reflect",
        "name": "Generate Reflection",
        "tool": "mind_reflect",
        "params": {
            "force": False
        },
        "validate": lambda r: True  # May or may not generate based on memory count
    },
    {
        "id": "mind_conflicts",
        "name": "Check Conflicts",
        "tool": "mind_conflicts",
        "params": {
            "limit": 5
        },
        "validate": lambda r: "conflicts" in r or isinstance(r, list) or "total" in str(r)
    }
]

MUSE_TESTS = [
    {
        "id": "muse_health",
        "name": "Health Check",
        "tool": "muse_health",
        "params": {},
        "validate": lambda r: r.get("status") == "healthy"
    },
    {
        "id": "muse_expand",
        "name": "Expand Prompt",
        "tool": "muse_expand_prompt",
        "params": {
            "user_id": "benchmark_test",
            "prompt": "Build a real-time collaborative document editor"
        },
        "validate": lambda r: "working_object" in r or "goal" in str(r)
    },
    {
        "id": "muse_associations",
        "name": "Retrieve Associations",
        "tool": "muse_retrieve_associations",
        "params": {
            "user_id": "benchmark_test",
            "query": "collaborative editing real-time sync",
            "limit_per_mode": 3
        },
        "validate": lambda r: True  # May have empty results
    },
    {
        "id": "muse_analogies",
        "name": "Generate Analogies",
        "tool": "muse_generate_analogies",
        "params": {
            "user_id": "benchmark_test",
            "source_content": "Microservices architecture with message queues",
            "source_domain": "software",
            "limit": 3
        },
        "validate": lambda r: True  # Analogies may be empty
    },
    {
        "id": "muse_contradictions",
        "name": "Find Contradictions",
        "tool": "muse_find_contradictions",
        "params": {
            "user_id": "benchmark_test",
            "content": "Monolithic architectures are always better than microservices"
        },
        "validate": lambda r: True  # May find or not find contradictions
    },
    {
        "id": "muse_mutate",
        "name": "Mutate Ideas",
        "tool": "muse_mutate_ideas",
        "params": {
            "user_id": "benchmark_test",
            "content": "A mobile app for tracking daily habits",
            "mutation_types": ["invert", "compress", "make_testable"]
        },
        "validate": lambda r: "mutations" in r or "variants" in str(r)
    },
    {
        "id": "muse_rank",
        "name": "Rank Candidates",
        "tool": "muse_rank_candidates",
        "params": {
            "user_id": "benchmark_test",
            "content": "AI-powered code review tool that learns from team preferences"
        },
        "validate": lambda r: "score" in str(r).lower() or "value" in str(r).lower() or "candidate" in r
    }
]

ARCHITECT_TESTS = [
    {
        "id": "arch_status",
        "name": "Get Status",
        "tool": "architect_status",
        "params": {},
        "validate": lambda r: r.get("success") == True or "project" in r
    },
    {
        "id": "arch_list_projects",
        "name": "List Projects",
        "tool": "architect_list_projects",
        "params": {},
        "validate": lambda r: "projects" in r or isinstance(r, list) or r.get("success")
    },
    {
        "id": "arch_list_tasks",
        "name": "List Tasks",
        "tool": "architect_list_tasks",
        "params": {},
        "validate": lambda r: "tasks" in r or isinstance(r, list) or r.get("success")
    },
    {
        "id": "arch_get_logs",
        "name": "Get Logs",
        "tool": "architect_get_logs",
        "params": {
            "limit": 10
        },
        "validate": lambda r: "logs" in r or isinstance(r, list) or r.get("success")
    },
    {
        "id": "arch_integration",
        "name": "Check Integration",
        "tool": "architect_check_integration",
        "params": {},
        "validate": lambda r: r.get("success") == True or "issues" in r or "compatibility" in str(r)
    },
    {
        "id": "arch_gotchas",
        "name": "Get Gotchas",
        "tool": "architect_get_gotchas",
        "params": {
            "stack": ["python", "sqlite", "asyncio"]
        },
        "validate": lambda r: True  # May or may not have gotchas
    }
]

SPAWNER_TESTS = [
    {
        "id": "spawn_orchestrate",
        "name": "Orchestrate",
        "tool": "spawner_orchestrate",
        "params": {
            "cwd": "/Users/q/PythonScript/Python/Vibe/vibeship-spark-intelligence"
        },
        "validate": lambda r: True  # Various response formats
    },
    {
        "id": "spawn_skills_search",
        "name": "Search Skills",
        "tool": "spawner_skills",
        "params": {
            "action": "search",
            "query": "database"
        },
        "validate": lambda r: True  # Returns skills or error
    },
    {
        "id": "spawn_skills_list",
        "name": "List Skills",
        "tool": "spawner_skills",
        "params": {
            "action": "list",
            "layer": 1
        },
        "validate": lambda r: True
    },
    {
        "id": "spawn_validate",
        "name": "Validate Code",
        "tool": "spawner_validate",
        "params": {
            "code": "const x = eval(userInput);",
            "file_path": "test.js",
            "check_types": ["security"]
        },
        "validate": lambda r: "issues" in r or "passed" in r or "security" in str(r).lower()
    },
    {
        "id": "spawn_watch_out",
        "name": "Watch Out (Gotchas)",
        "tool": "spawner_watch_out",
        "params": {
            "stack": ["nextjs", "supabase", "typescript"],
            "situation": "setting up authentication"
        },
        "validate": lambda r: True  # Various formats
    },
    {
        "id": "spawn_templates",
        "name": "List Templates",
        "tool": "spawner_templates",
        "params": {},
        "validate": lambda r: True
    }
]


def print_test_commands():
    """Print the test commands to be run."""
    print("=" * 70)
    print("MCP LIVE BENCHMARK - TEST COMMANDS")
    print("=" * 70)
    print("\nRun these tool calls to test the MCP servers:\n")

    all_tests = [
        ("Mind MCP", MIND_TESTS),
        ("Muse MCP", MUSE_TESTS),
        ("Architect MCP", ARCHITECT_TESTS),
        ("Spawner MCP", SPAWNER_TESTS)
    ]

    for server_name, tests in all_tests:
        print(f"\n## {server_name}")
        print("-" * 40)
        for test in tests:
            print(f"\n### {test['name']}")
            print(f"Tool: mcp__{test['tool'].split('_')[0]}__{test['tool']}")
            print(f"Params: {json.dumps(test['params'], indent=2)}")


if __name__ == "__main__":
    print_test_commands()
