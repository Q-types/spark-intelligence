# Benchmark Categories

8 categories of software engineering challenges for evaluating MCP configurations.

## Category Overview

| # | Category | Problems | Difficulty Distribution | Focus Areas |
|---|----------|----------|------------------------|-------------|
| 1 | Systems Programming | 4 | 0 Easy, 1 Medium, 3 Hard | Concurrency, memory, processes |
| 2 | Web & API | 4 | 0 Easy, 3 Medium, 1 Hard | Auth, rate limiting, webhooks |
| 3 | Security | 5 | 2 Easy, 2 Medium, 1 Hard | Injection, XSS, encryption |
| 4 | Algorithms | 5 | 0 Easy, 4 Medium, 1 Hard | Data structures, graphs, DP |
| 5 | Debugging | 5 | 1 Easy, 2 Medium, 2 Hard | Race conditions, leaks, perf |
| 6 | Code Review | 4 | 1 Easy, 2 Medium, 1 Hard | Refactoring, patterns, review |
| 7 | Testing & QA | 5 | 2 Easy, 2 Medium, 1 Hard | Unit tests, mocking, coverage |
| 8 | DevOps | 5 | 1 Easy, 2 Medium, 2 Hard | Docker, K8s, CI/CD, IaC |

**Total: 37 problems** (7 Easy, 18 Medium, 12 Hard)

---

## Category Details

### 1. Systems Programming (`01_systems_programming.json`)

Low-level programming challenges focusing on concurrency, memory management, and process control.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| sys_001 | Implement a Thread Pool | Medium | 30m |
| sys_002 | Memory-Mapped File Reader | Hard | 25m |
| sys_003 | Process Supervisor | Hard | 40m |
| sys_004 | Lock-Free Queue | Hard | 45m |

**Key Skills:** Threading, mmap, signals, atomic operations

---

### 2. Web & API Development (`02_web_api.json`)

Web application and API challenges covering authentication, rate limiting, and data fetching patterns.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| web_001 | JWT Authentication Middleware | Medium | 30m |
| web_002 | Rate Limiter with Sliding Window | Medium | 35m |
| web_003 | GraphQL Resolver with DataLoader | Hard | 40m |
| web_004 | Webhook Delivery System | Medium | 35m |

**Key Skills:** JWT, Redis, GraphQL, HTTP

---

### 3. Security & Defensive Coding (`03_security.json`)

Security challenges covering common vulnerabilities and secure coding practices.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| sec_001 | SQL Injection Prevention | Easy | 15m |
| sec_002 | Password Hashing and Verification | Medium | 25m |
| sec_003 | XSS Prevention Filter | Medium | 30m |
| sec_004 | Secrets Manager | Hard | 45m |
| sec_005 | CSRF Protection Middleware | Easy | 20m |

**Key Skills:** OWASP, cryptography, input validation

---

### 4. Algorithms & Data Structures (`04_algorithms.json`)

Classic algorithm challenges with practical applications.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| alg_001 | Trie with Autocomplete | Medium | 25m |
| alg_002 | Dijkstra's Shortest Path | Medium | 30m |
| alg_003 | LCS with Diff Generation | Hard | 35m |
| alg_004 | Bloom Filter | Medium | 25m |
| alg_005 | Interval Scheduling | Medium | 25m |

**Key Skills:** Trees, graphs, dynamic programming, probabilistic data structures

---

### 5. Debugging & Troubleshooting (`05_debugging.json`)

Find and fix bugs in provided code samples.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| dbg_001 | Find the Race Condition | Hard | 20m |
| dbg_002 | Memory Leak Investigation | Medium | 25m |
| dbg_003 | Performance Bottleneck | Medium | 20m |
| dbg_004 | Deadlock Detection | Hard | 25m |
| dbg_005 | Off-by-One Errors | Easy | 15m |

**Key Skills:** Concurrency debugging, profiling, memory analysis

---

### 6. Code Review & Refactoring (`06_code_review.json`)

Improve code quality through refactoring and design patterns.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| rev_001 | Extract Method Refactoring | Easy | 20m |
| rev_002 | Apply Strategy Pattern | Medium | 30m |
| rev_003 | Code Review: Find Issues | Medium | 25m |
| rev_004 | Replace Inheritance with Composition | Hard | 35m |

**Key Skills:** SOLID principles, design patterns, code review

---

### 7. Testing & Quality Assurance (`07_testing.json`)

Testing challenges covering unit tests, mocking, and coverage.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| tst_001 | Design Test Suite for Calculator | Easy | 20m |
| tst_002 | Mock External Dependencies | Medium | 30m |
| tst_003 | Property-Based Testing | Medium | 30m |
| tst_004 | Integration Test with Test Containers | Hard | 40m |
| tst_005 | Test Coverage Analysis | Easy | 25m |

**Key Skills:** pytest, mocking, Hypothesis, testcontainers

---

### 8. DevOps & Infrastructure (`08_devops.json`)

Infrastructure and deployment challenges.

| ID | Title | Difficulty | Time |
|----|-------|------------|------|
| ops_001 | Dockerfile Optimization | Easy | 20m |
| ops_002 | CI/CD Pipeline Design | Medium | 35m |
| ops_003 | Kubernetes Deployment Manifest | Medium | 30m |
| ops_004 | Monitoring and Alerting Setup | Hard | 45m |
| ops_005 | Infrastructure as Code | Hard | 50m |

**Key Skills:** Docker, GitHub Actions, Kubernetes, Terraform, Prometheus

---

## Evaluation Approach

Each problem is evaluated on:

1. **Correctness** (25%) - Does the solution work?
2. **Completeness** (15%) - Are all requirements met?
3. **Code Quality** (15%) - Style, types, documentation
4. **Efficiency** (10%) - Time/space complexity
5. **Best Practices** (10%) - Follows conventions
6. **Error Handling** (10%) - Graceful failure handling
7. **Security** (10%) - No vulnerabilities introduced
8. **Testability** (5%) - Can it be tested?

---

## Running Benchmarks

```bash
# Run single category
python benchmarks/test_harness.py --category systems_programming

# Run all categories
python benchmarks/test_harness.py --all

# Compare configurations
python benchmarks/test_harness.py --compare baseline,mind,architect
```
