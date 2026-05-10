#!/usr/bin/env python3
"""
Systems Programming Benchmark
Tests: Thread Pool, Memory-Mapped File Reader, Process Supervisor, Lock-Free Queue

Run: python benchmarks/solutions/systems_benchmark.py
"""

import json
import threading
import queue
import time
import mmap
import os
import tempfile
import signal
import subprocess
import sys
from concurrent.futures import Future
from typing import Callable, Optional, List, Any, Iterator
from dataclasses import dataclass
from collections import deque
import ctypes


# =============================================================================
# Problem 1: Thread Pool (Medium)
# =============================================================================

class ThreadPool:
    """
    A thread pool that manages a fixed number of worker threads.
    Supports task submission, graceful shutdown, and immediate shutdown.
    """

    def __init__(self, num_workers: int):
        self.num_workers = num_workers
        self._task_queue: queue.Queue = queue.Queue()
        self._workers: List[threading.Thread] = []
        self._shutdown = False
        self._shutdown_now = False
        self._lock = threading.Lock()
        self._active_tasks = 0
        self._all_done = threading.Condition(self._lock)

        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self._workers.append(worker)

    def _worker_loop(self):
        """Worker thread main loop."""
        while True:
            try:
                # Check for shutdown_now
                if self._shutdown_now:
                    return

                # Get task with timeout to check shutdown periodically
                try:
                    task, future = self._task_queue.get(timeout=0.1)
                except queue.Empty:
                    if self._shutdown:
                        return
                    continue

                # Check again after getting task
                if self._shutdown_now:
                    future.set_exception(RuntimeError("Pool shutdown"))
                    self._task_queue.task_done()
                    return

                # Execute task
                with self._lock:
                    self._active_tasks += 1

                try:
                    result = task()
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self._task_queue.task_done()
                    with self._all_done:
                        self._active_tasks -= 1
                        self._all_done.notify_all()

            except Exception:
                pass

    def submit(self, task: Callable) -> Future:
        """Submit a task to the pool. Returns a Future."""
        if self._shutdown or self._shutdown_now:
            raise RuntimeError("Pool is shut down")

        future = Future()
        self._task_queue.put((task, future))
        return future

    def shutdown(self, wait: bool = True):
        """Graceful shutdown - wait for all tasks to complete."""
        self._shutdown = True

        if wait:
            # Wait for queue to empty
            self._task_queue.join()

            # Wait for all workers to finish
            for worker in self._workers:
                worker.join(timeout=5.0)

    def shutdown_now(self) -> List[Future]:
        """Immediate shutdown - cancel pending tasks."""
        self._shutdown_now = True
        self._shutdown = True

        # Drain pending tasks
        cancelled = []
        while True:
            try:
                task, future = self._task_queue.get_nowait()
                future.set_exception(RuntimeError("Task cancelled"))
                cancelled.append(future)
            except queue.Empty:
                break

        # Wait for active tasks to complete (with timeout)
        with self._all_done:
            deadline = time.time() + 5.0
            while self._active_tasks > 0:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self._all_done.wait(timeout=remaining)

        return cancelled


# =============================================================================
# Problem 2: Memory-Mapped File Reader (Hard)
# =============================================================================

class MMapReader:
    """
    Memory-mapped file reader for efficient large file processing.
    Uses mmap for memory-efficient access without loading entire file.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._file = None
        self._mmap = None
        self._size = 0
        self._open()

    def _open(self):
        """Open file and create memory map."""
        self._file = open(self.filepath, 'rb')
        self._size = os.path.getsize(self.filepath)
        if self._size > 0:
            self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """Release resources."""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None

    def read_range(self, start: int, end: int) -> bytes:
        """Read specific byte range from file."""
        if self._mmap is None:
            return b''

        # Clamp to valid range
        start = max(0, start)
        end = min(end, self._size)

        if start >= end:
            return b''

        return self._mmap[start:end]

    def lines(self, encoding: str = 'utf-8') -> Iterator[str]:
        """Iterate over lines without loading entire file."""
        if self._mmap is None:
            return

        position = 0
        while position < self._size:
            # Find next newline
            newline_pos = self._mmap.find(b'\n', position)

            if newline_pos == -1:
                # Last line without newline
                line = self._mmap[position:].decode(encoding)
                if line:
                    yield line
                break
            else:
                line = self._mmap[position:newline_pos].decode(encoding)
                yield line
                position = newline_pos + 1

    @property
    def size(self) -> int:
        """Return file size."""
        return self._size

    def search(self, pattern: bytes, start: int = 0) -> int:
        """Search for pattern in file. Returns position or -1."""
        if self._mmap is None:
            return -1
        return self._mmap.find(pattern, start)


# =============================================================================
# Problem 3: Process Supervisor (Hard)
# =============================================================================

@dataclass
class ProcessConfig:
    """Configuration for a supervised process."""
    name: str
    command: List[str]
    restart: bool = True
    max_restarts: int = 5
    restart_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    health_check: Optional[Callable] = None


class SupervisedProcess:
    """A single supervised process."""

    def __init__(self, config: ProcessConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.current_delay = config.restart_delay
        self.is_running = False
        self.exit_code: Optional[int] = None
        self.logs: List[str] = []

    def start(self) -> bool:
        """Start the process."""
        try:
            self.process = subprocess.Popen(
                self.config.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_running = True
            self.logs.append(f"Started process {self.config.name} (PID: {self.process.pid})")
            return True
        except Exception as e:
            self.logs.append(f"Failed to start {self.config.name}: {e}")
            return False

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop the process gracefully."""
        if not self.process:
            return True

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
                self.logs.append(f"Process {self.config.name} terminated gracefully")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                self.logs.append(f"Process {self.config.name} force killed")

            self.is_running = False
            self.exit_code = self.process.returncode
            return True
        except Exception as e:
            self.logs.append(f"Error stopping {self.config.name}: {e}")
            return False

    def check(self) -> bool:
        """Check if process is still running."""
        if not self.process:
            return False

        poll_result = self.process.poll()
        if poll_result is not None:
            self.is_running = False
            self.exit_code = poll_result
            self.logs.append(f"Process {self.config.name} exited with code {poll_result}")
            return False
        return True

    def health_check(self) -> bool:
        """Run health check if configured."""
        if self.config.health_check:
            return self.config.health_check()
        return self.is_running


class ProcessSupervisor:
    """
    Manages multiple child processes with automatic restart and monitoring.
    """

    def __init__(self):
        self._processes: dict[str, SupervisedProcess] = {}
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.logs: List[str] = []

    def add(self, name: str, command: List[str], restart: bool = True,
            max_restarts: int = 5, health_check: Optional[Callable] = None) -> None:
        """Add a process to supervise."""
        config = ProcessConfig(
            name=name,
            command=command,
            restart=restart,
            max_restarts=max_restarts,
            health_check=health_check
        )
        self._processes[name] = SupervisedProcess(config)
        self.logs.append(f"Added process {name} to supervisor")

    def start(self) -> None:
        """Start all processes and begin monitoring."""
        self._running = True
        self._stop_event.clear()

        # Start all processes
        for name, proc in self._processes.items():
            proc.start()

        # Start monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logs.append("Supervisor started")

    def _monitor_loop(self) -> None:
        """Monitor processes and restart crashed ones."""
        while not self._stop_event.is_set():
            with self._lock:
                for name, proc in self._processes.items():
                    if not proc.check() and proc.config.restart:
                        # Process crashed, try to restart
                        if proc.restart_count < proc.config.max_restarts:
                            self.logs.append(f"Restarting {name} (attempt {proc.restart_count + 1})")
                            time.sleep(proc.current_delay)
                            if proc.start():
                                proc.restart_count += 1
                                proc.current_delay = min(
                                    proc.current_delay * proc.config.backoff_multiplier,
                                    proc.config.max_delay
                                )
                        else:
                            self.logs.append(f"Process {name} exceeded max restarts")

            self._stop_event.wait(timeout=0.5)

    def stop_all(self, timeout: float = 5.0) -> None:
        """Stop all processes."""
        self._running = False
        self._stop_event.set()

        # Stop all processes
        with self._lock:
            for name, proc in self._processes.items():
                proc.stop(timeout=timeout)

        # Wait for monitor thread
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)

        self.logs.append("Supervisor stopped")

    def status(self) -> dict:
        """Get status of all processes."""
        with self._lock:
            return {
                name: {
                    'running': proc.is_running,
                    'restart_count': proc.restart_count,
                    'exit_code': proc.exit_code
                }
                for name, proc in self._processes.items()
            }

    def get_logs(self) -> List[str]:
        """Get all supervisor logs."""
        all_logs = list(self.logs)
        for proc in self._processes.values():
            all_logs.extend(proc.logs)
        return all_logs


# =============================================================================
# Problem 4: Lock-Free Queue (Hard)
# Using Python's atomics through threading primitives
# Note: Pure lock-free in Python is limited, but we demonstrate the concept
# =============================================================================

class AtomicReference:
    """Atomic reference wrapper using lock for CAS simulation."""

    def __init__(self, value: Any = None):
        self._value = value
        self._lock = threading.Lock()

    def get(self) -> Any:
        with self._lock:
            return self._value

    def set(self, value: Any) -> None:
        with self._lock:
            self._value = value

    def compare_and_swap(self, expected: Any, new_value: Any) -> bool:
        """Atomic compare-and-swap operation."""
        with self._lock:
            if self._value is expected:
                self._value = new_value
                return True
            return False


class LockFreeNode:
    """Node for lock-free queue."""

    def __init__(self, value: Any = None):
        self.value = value
        self.next = AtomicReference(None)


class LockFreeQueue:
    """
    Lock-free queue using compare-and-swap operations.
    Based on Michael-Scott queue algorithm.
    """

    def __init__(self):
        # Initialize with dummy node
        dummy = LockFreeNode()
        self._head = AtomicReference(dummy)
        self._tail = AtomicReference(dummy)
        self._size = AtomicReference(0)

    def enqueue(self, value: Any) -> None:
        """Add item to queue (thread-safe)."""
        node = LockFreeNode(value)

        while True:
            tail = self._tail.get()
            next_node = tail.next.get()

            # Check if tail is still the tail
            if tail is self._tail.get():
                if next_node is None:
                    # Try to link new node
                    if tail.next.compare_and_swap(None, node):
                        # Try to move tail (OK if it fails - another thread did it)
                        self._tail.compare_and_swap(tail, node)
                        # Increment size
                        while True:
                            size = self._size.get()
                            if self._size.compare_and_swap(size, size + 1):
                                break
                        return
                else:
                    # Tail is behind, try to advance it
                    self._tail.compare_and_swap(tail, next_node)

    def dequeue(self) -> Optional[Any]:
        """Remove and return item from queue (thread-safe)."""
        while True:
            head = self._head.get()
            tail = self._tail.get()
            first = head.next.get()

            # Check if head is still valid
            if head is self._head.get():
                if head is tail:
                    if first is None:
                        # Queue is empty
                        return None
                    # Tail is behind, advance it
                    self._tail.compare_and_swap(tail, first)
                else:
                    if first is not None:
                        value = first.value
                        # Try to move head
                        if self._head.compare_and_swap(head, first):
                            # Decrement size
                            while True:
                                size = self._size.get()
                                if self._size.compare_and_swap(size, size - 1):
                                    break
                            return value

    def size(self) -> int:
        """Return approximate size of queue."""
        return self._size.get()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        head = self._head.get()
        return head.next.get() is None


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

    # Problem 1: Thread Pool (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 1: Thread Pool")
    print("="*60)

    problem1_tests = []
    problem1_passed = 0

    # Test 1.1: Basic task execution
    try:
        pool = ThreadPool(4)
        results_list = []
        futures = [pool.submit(lambda i=i: i*2) for i in range(10)]
        pool.shutdown(wait=True)
        results_list = [f.result(timeout=5) for f in futures]
        test_passed = sorted(results_list) == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        problem1_tests.append({
            "name": "basic_task_execution",
            "passed": test_passed,
            "details": f"Results: {sorted(results_list)}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Basic task execution")
    except Exception as e:
        problem1_tests.append({"name": "basic_task_execution", "passed": False, "details": str(e)})
        print(f"  [FAIL] Basic task execution: {e}")

    # Test 1.2: Concurrent execution
    try:
        pool = ThreadPool(4)
        execution_times = []
        def timed_task(i):
            start = time.time()
            time.sleep(0.1)
            return time.time() - start

        futures = [pool.submit(lambda i=i: timed_task(i)) for i in range(4)]
        start = time.time()
        pool.shutdown()
        total_time = time.time() - start

        # 4 tasks, each 0.1s, with 4 workers should take ~0.1s total
        test_passed = total_time < 0.5  # Allow some overhead
        problem1_tests.append({
            "name": "concurrent_execution",
            "passed": test_passed,
            "details": f"Total time: {total_time:.3f}s (expected < 0.5s)"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Concurrent execution")
    except Exception as e:
        problem1_tests.append({"name": "concurrent_execution", "passed": False, "details": str(e)})
        print(f"  [FAIL] Concurrent execution: {e}")

    # Test 1.3: Shutdown waits for completion
    try:
        pool = ThreadPool(2)
        completed = []
        def slow_task(i):
            time.sleep(0.1)
            completed.append(i)
            return i

        futures = [pool.submit(lambda i=i: slow_task(i)) for i in range(4)]
        pool.shutdown(wait=True)

        test_passed = len(completed) == 4
        problem1_tests.append({
            "name": "shutdown_waits",
            "passed": test_passed,
            "details": f"Completed: {len(completed)}/4 tasks"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Shutdown waits")
    except Exception as e:
        problem1_tests.append({"name": "shutdown_waits", "passed": False, "details": str(e)})
        print(f"  [FAIL] Shutdown waits: {e}")

    # Test 1.4: Shutdown now cancels pending
    try:
        pool = ThreadPool(1)
        def very_slow():
            time.sleep(10)
            return "done"

        futures = [pool.submit(very_slow) for _ in range(5)]
        time.sleep(0.1)  # Let first task start
        cancelled = pool.shutdown_now()

        # At least some tasks should be cancelled
        test_passed = len(cancelled) >= 3
        problem1_tests.append({
            "name": "shutdown_now_cancels",
            "passed": test_passed,
            "details": f"Cancelled: {len(cancelled)} pending tasks"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Shutdown now cancels pending")
    except Exception as e:
        problem1_tests.append({"name": "shutdown_now_cancels", "passed": False, "details": str(e)})
        print(f"  [FAIL] Shutdown now cancels pending: {e}")

    # Test 1.5: Thread count is correct
    try:
        pool = ThreadPool(3)
        worker_count = len(pool._workers)
        pool.shutdown()

        test_passed = worker_count == 3
        problem1_tests.append({
            "name": "worker_count",
            "passed": test_passed,
            "details": f"Worker count: {worker_count}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Worker count")
    except Exception as e:
        problem1_tests.append({"name": "worker_count", "passed": False, "details": str(e)})
        print(f"  [FAIL] Worker count: {e}")

    # Test 1.6: Exception handling
    try:
        pool = ThreadPool(2)
        def failing_task():
            raise ValueError("Task failed")

        future = pool.submit(failing_task)
        pool.shutdown()

        try:
            future.result(timeout=1)
            test_passed = False
        except ValueError:
            test_passed = True

        problem1_tests.append({
            "name": "exception_handling",
            "passed": test_passed,
            "details": "Exception propagated correctly"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Exception handling")
    except Exception as e:
        problem1_tests.append({"name": "exception_handling", "passed": False, "details": str(e)})
        print(f"  [FAIL] Exception handling: {e}")

    problem1_score = (problem1_passed / 6) * 150
    results["problems"].append({
        "id": "sys_001",
        "title": "Thread Pool",
        "difficulty": "Medium",
        "pass_rate": problem1_passed / 6,
        "score": problem1_score,
        "tests": problem1_tests
    })
    total_score += problem1_score
    max_score += 150
    all_tests.extend(problem1_tests)

    # Problem 2: Memory-Mapped File Reader (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 2: Memory-Mapped File Reader")
    print("="*60)

    problem2_tests = []
    problem2_passed = 0

    # Create test file
    test_content = "\n".join([f"Line {i}: " + "x" * 100 for i in range(1000)])
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name

    # Test 2.1: Read range
    try:
        with MMapReader(test_file) as reader:
            chunk = reader.read_range(0, 50)
            test_passed = chunk.decode('utf-8').startswith("Line 0:")

        problem2_tests.append({
            "name": "read_range",
            "passed": test_passed,
            "details": f"Got: {chunk[:30]}..."
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Read range")
    except Exception as e:
        problem2_tests.append({"name": "read_range", "passed": False, "details": str(e)})
        print(f"  [FAIL] Read range: {e}")

    # Test 2.2: Line iterator
    try:
        with MMapReader(test_file) as reader:
            lines = list(reader.lines())
            first_100 = lines[:100]

        test_passed = len(first_100) == 100 and all("Line" in line for line in first_100)
        problem2_tests.append({
            "name": "line_iterator",
            "passed": test_passed,
            "details": f"First 100 lines retrieved, all valid"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Line iterator")
    except Exception as e:
        problem2_tests.append({"name": "line_iterator", "passed": False, "details": str(e)})
        print(f"  [FAIL] Line iterator: {e}")

    # Test 2.3: File size property
    try:
        with MMapReader(test_file) as reader:
            size = reader.size
            actual_size = os.path.getsize(test_file)

        test_passed = size == actual_size
        problem2_tests.append({
            "name": "file_size",
            "passed": test_passed,
            "details": f"Size: {size}, Actual: {actual_size}"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] File size")
    except Exception as e:
        problem2_tests.append({"name": "file_size", "passed": False, "details": str(e)})
        print(f"  [FAIL] File size: {e}")

    # Test 2.4: Search functionality
    try:
        with MMapReader(test_file) as reader:
            pos = reader.search(b"Line 500:")

        test_passed = pos > 0
        problem2_tests.append({
            "name": "search",
            "passed": test_passed,
            "details": f"Found 'Line 500:' at position {pos}"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Search")
    except Exception as e:
        problem2_tests.append({"name": "search", "passed": False, "details": str(e)})
        print(f"  [FAIL] Search: {e}")

    # Test 2.5: Context manager cleanup
    try:
        reader = MMapReader(test_file)
        with reader:
            _ = reader.size

        # After exit, resources should be released
        test_passed = reader._mmap is None and reader._file is None
        problem2_tests.append({
            "name": "context_manager",
            "passed": test_passed,
            "details": "Resources released on exit"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Context manager cleanup")
    except Exception as e:
        problem2_tests.append({"name": "context_manager", "passed": False, "details": str(e)})
        print(f"  [FAIL] Context manager cleanup: {e}")

    # Test 2.6: Boundary range handling
    try:
        with MMapReader(test_file) as reader:
            file_size = reader.size
            # Read beyond file size
            chunk = reader.read_range(file_size - 10, file_size + 100)
            test_passed = len(chunk) == 10  # Should clamp to file size

        problem2_tests.append({
            "name": "boundary_handling",
            "passed": test_passed,
            "details": f"Boundary read returned {len(chunk)} bytes"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Boundary handling")
    except Exception as e:
        problem2_tests.append({"name": "boundary_handling", "passed": False, "details": str(e)})
        print(f"  [FAIL] Boundary handling: {e}")

    # Cleanup test file
    os.unlink(test_file)

    problem2_score = (problem2_passed / 6) * 200
    results["problems"].append({
        "id": "sys_002",
        "title": "Memory-Mapped File Reader",
        "difficulty": "Hard",
        "pass_rate": problem2_passed / 6,
        "score": problem2_score,
        "tests": problem2_tests
    })
    total_score += problem2_score
    max_score += 200
    all_tests.extend(problem2_tests)

    # Problem 3: Process Supervisor (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 3: Process Supervisor")
    print("="*60)

    problem3_tests = []
    problem3_passed = 0

    # Test 3.1: Add process
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("test", [sys.executable, "-c", "print('hello')"])

        test_passed = "test" in supervisor._processes
        problem3_tests.append({
            "name": "add_process",
            "passed": test_passed,
            "details": "Process added to supervisor"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Add process")
    except Exception as e:
        problem3_tests.append({"name": "add_process", "passed": False, "details": str(e)})
        print(f"  [FAIL] Add process: {e}")

    # Test 3.2: Start and stop
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("sleeper", [sys.executable, "-c", "import time; time.sleep(10)"], restart=False)
        supervisor.start()
        time.sleep(0.2)

        status = supervisor.status()
        running = status["sleeper"]["running"]

        supervisor.stop_all(timeout=1)

        test_passed = running == True
        problem3_tests.append({
            "name": "start_and_stop",
            "passed": test_passed,
            "details": f"Process was running: {running}"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Start and stop")
    except Exception as e:
        problem3_tests.append({"name": "start_and_stop", "passed": False, "details": str(e)})
        print(f"  [FAIL] Start and stop: {e}")

    # Test 3.3: Logging
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("logger_test", [sys.executable, "-c", "pass"], restart=False)
        supervisor.start()
        time.sleep(0.2)
        supervisor.stop_all()

        logs = supervisor.get_logs()
        test_passed = len(logs) > 0 and any("Started" in log or "Added" in log for log in logs)

        problem3_tests.append({
            "name": "logging",
            "passed": test_passed,
            "details": f"Logged {len(logs)} events"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Logging")
    except Exception as e:
        problem3_tests.append({"name": "logging", "passed": False, "details": str(e)})
        print(f"  [FAIL] Logging: {e}")

    # Test 3.4: Status reporting
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("status_test", [sys.executable, "-c", "pass"], restart=False)
        supervisor.start()
        time.sleep(0.3)

        status = supervisor.status()
        supervisor.stop_all()

        test_passed = "status_test" in status and "running" in status["status_test"]
        problem3_tests.append({
            "name": "status_reporting",
            "passed": test_passed,
            "details": f"Status: {status}"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Status reporting")
    except Exception as e:
        problem3_tests.append({"name": "status_reporting", "passed": False, "details": str(e)})
        print(f"  [FAIL] Status reporting: {e}")

    # Test 3.5: Multiple processes
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("proc1", [sys.executable, "-c", "import time; time.sleep(5)"], restart=False)
        supervisor.add("proc2", [sys.executable, "-c", "import time; time.sleep(5)"], restart=False)
        supervisor.start()
        time.sleep(0.3)

        status = supervisor.status()
        supervisor.stop_all(timeout=1)

        test_passed = len(status) == 2
        problem3_tests.append({
            "name": "multiple_processes",
            "passed": test_passed,
            "details": f"Managing {len(status)} processes"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Multiple processes")
    except Exception as e:
        problem3_tests.append({"name": "multiple_processes", "passed": False, "details": str(e)})
        print(f"  [FAIL] Multiple processes: {e}")

    # Test 3.6: Exit code tracking
    try:
        supervisor = ProcessSupervisor()
        supervisor.add("exit_test", [sys.executable, "-c", "exit(42)"], restart=False)
        supervisor.start()
        time.sleep(1.0)  # Wait for process to complete

        status = supervisor.status()
        supervisor.stop_all()

        test_passed = status["exit_test"]["exit_code"] == 42
        problem3_tests.append({
            "name": "exit_code_tracking",
            "passed": test_passed,
            "details": f"Exit code: {status['exit_test']['exit_code']}"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Exit code tracking")
    except Exception as e:
        problem3_tests.append({"name": "exit_code_tracking", "passed": False, "details": str(e)})
        print(f"  [FAIL] Exit code tracking: {e}")

    problem3_score = (problem3_passed / 6) * 200
    results["problems"].append({
        "id": "sys_003",
        "title": "Process Supervisor",
        "difficulty": "Hard",
        "pass_rate": problem3_passed / 6,
        "score": problem3_score,
        "tests": problem3_tests
    })
    total_score += problem3_score
    max_score += 200
    all_tests.extend(problem3_tests)

    # Problem 4: Lock-Free Queue (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 4: Lock-Free Queue")
    print("="*60)

    problem4_tests = []
    problem4_passed = 0

    # Test 4.1: Basic enqueue/dequeue
    try:
        q = LockFreeQueue()
        q.enqueue(1)
        q.enqueue(2)
        q.enqueue(3)

        results_list = [q.dequeue(), q.dequeue(), q.dequeue()]
        test_passed = results_list == [1, 2, 3]

        problem4_tests.append({
            "name": "basic_operations",
            "passed": test_passed,
            "details": f"Results: {results_list}"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Basic operations")
    except Exception as e:
        problem4_tests.append({"name": "basic_operations", "passed": False, "details": str(e)})
        print(f"  [FAIL] Basic operations: {e}")

    # Test 4.2: Empty queue
    try:
        q = LockFreeQueue()
        result = q.dequeue()

        test_passed = result is None and q.is_empty()
        problem4_tests.append({
            "name": "empty_queue",
            "passed": test_passed,
            "details": f"Empty queue returns None: {result}"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Empty queue")
    except Exception as e:
        problem4_tests.append({"name": "empty_queue", "passed": False, "details": str(e)})
        print(f"  [FAIL] Empty queue: {e}")

    # Test 4.3: Size tracking
    try:
        q = LockFreeQueue()
        q.enqueue(1)
        q.enqueue(2)
        size_after_enqueue = q.size()
        q.dequeue()
        size_after_dequeue = q.size()

        test_passed = size_after_enqueue == 2 and size_after_dequeue == 1
        problem4_tests.append({
            "name": "size_tracking",
            "passed": test_passed,
            "details": f"After enqueue: {size_after_enqueue}, After dequeue: {size_after_dequeue}"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Size tracking")
    except Exception as e:
        problem4_tests.append({"name": "size_tracking", "passed": False, "details": str(e)})
        print(f"  [FAIL] Size tracking: {e}")

    # Test 4.4: Concurrent enqueue
    try:
        q = LockFreeQueue()
        threads = []
        num_per_thread = 100
        num_threads = 8

        def enqueue_many(start):
            for i in range(num_per_thread):
                q.enqueue(start + i)

        for t in range(num_threads):
            thread = threading.Thread(target=enqueue_many, args=(t * num_per_thread,))
            threads.append(thread)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check all items are present
        items = []
        while True:
            item = q.dequeue()
            if item is None:
                break
            items.append(item)

        test_passed = len(items) == num_threads * num_per_thread
        problem4_tests.append({
            "name": "concurrent_enqueue",
            "passed": test_passed,
            "details": f"Enqueued {len(items)}/{num_threads * num_per_thread} items"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Concurrent enqueue")
    except Exception as e:
        problem4_tests.append({"name": "concurrent_enqueue", "passed": False, "details": str(e)})
        print(f"  [FAIL] Concurrent enqueue: {e}")

    # Test 4.5: Concurrent enqueue/dequeue
    try:
        q = LockFreeQueue()
        enqueued = []
        dequeued = []
        lock = threading.Lock()

        def producer(items):
            for item in items:
                q.enqueue(item)
                with lock:
                    enqueued.append(item)

        def consumer(count):
            for _ in range(count):
                while True:
                    item = q.dequeue()
                    if item is not None:
                        with lock:
                            dequeued.append(item)
                        break
                    time.sleep(0.001)

        items_to_add = list(range(100))

        producer_thread = threading.Thread(target=producer, args=(items_to_add,))
        consumer_thread = threading.Thread(target=consumer, args=(100,))

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join(timeout=5)

        test_passed = sorted(dequeued) == sorted(items_to_add)
        problem4_tests.append({
            "name": "concurrent_enqueue_dequeue",
            "passed": test_passed,
            "details": f"All {len(dequeued)} items correctly transferred"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Concurrent enqueue/dequeue")
    except Exception as e:
        problem4_tests.append({"name": "concurrent_enqueue_dequeue", "passed": False, "details": str(e)})
        print(f"  [FAIL] Concurrent enqueue/dequeue: {e}")

    # Test 4.6: FIFO order preserved
    try:
        q = LockFreeQueue()
        for i in range(50):
            q.enqueue(i)

        results_list = []
        for _ in range(50):
            results_list.append(q.dequeue())

        test_passed = results_list == list(range(50))
        problem4_tests.append({
            "name": "fifo_order",
            "passed": test_passed,
            "details": "FIFO order preserved"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] FIFO order")
    except Exception as e:
        problem4_tests.append({"name": "fifo_order", "passed": False, "details": str(e)})
        print(f"  [FAIL] FIFO order: {e}")

    problem4_score = (problem4_passed / 6) * 200
    results["problems"].append({
        "id": "sys_004",
        "title": "Lock-Free Queue",
        "difficulty": "Hard",
        "pass_rate": problem4_passed / 6,
        "score": problem4_score,
        "tests": problem4_tests
    })
    total_score += problem4_score
    max_score += 200
    all_tests.extend(problem4_tests)

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
    print("SYSTEMS PROGRAMMING BENCHMARK")
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
    output_path = "/tmp/systems_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
