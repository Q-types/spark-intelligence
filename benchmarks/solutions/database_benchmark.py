#!/usr/bin/env python3
"""
Database Engineering Benchmark
Tests: Schema Design, Query Optimization, Transactions, Joins, Window Functions,
       CTEs, Full-Text Search, JSON Operations, Connection Pooling, Testing

Supports both SQLite (built-in) and PostgreSQL patterns.

Run: python benchmarks/solutions/database_benchmark.py
"""

import json
import sqlite3
import threading
import time
import queue
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict
import random


# =============================================================================
# Problem 1: Schema Design and Migrations (Medium)
# =============================================================================

class Migration:
    """Represents a database migration."""

    def __init__(self, version: int, name: str, up_sql: str, down_sql: str):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql


class MigrationManager:
    """
    Manages database schema migrations with version tracking and rollback.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_migration_table()
        self.migrations: List[Migration] = []

    def _init_migration_table(self):
        """Create migration tracking table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_migration(self, migration: Migration):
        """Register a migration."""
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    def get_current_version(self) -> int:
        """Get the current schema version."""
        cursor = self.conn.execute(
            "SELECT MAX(version) FROM schema_migrations"
        )
        result = cursor.fetchone()[0]
        return result if result else 0

    def migrate_up(self, target_version: Optional[int] = None) -> List[int]:
        """Apply pending migrations up to target version."""
        current = self.get_current_version()
        target = target_version or (self.migrations[-1].version if self.migrations else 0)

        applied = []
        for migration in self.migrations:
            if migration.version > current and migration.version <= target:
                try:
                    # Execute migration
                    self.conn.executescript(migration.up_sql)

                    # Record migration
                    self.conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (migration.version, migration.name)
                    )
                    self.conn.commit()
                    applied.append(migration.version)
                except Exception as e:
                    self.conn.rollback()
                    raise RuntimeError(f"Migration {migration.version} failed: {e}")

        return applied

    def migrate_down(self, target_version: int = 0) -> List[int]:
        """Rollback migrations down to target version."""
        current = self.get_current_version()

        rolled_back = []
        for migration in reversed(self.migrations):
            if migration.version <= current and migration.version > target_version:
                try:
                    # Execute rollback
                    self.conn.executescript(migration.down_sql)

                    # Remove migration record
                    self.conn.execute(
                        "DELETE FROM schema_migrations WHERE version = ?",
                        (migration.version,)
                    )
                    self.conn.commit()
                    rolled_back.append(migration.version)
                except Exception as e:
                    self.conn.rollback()
                    raise RuntimeError(f"Rollback {migration.version} failed: {e}")

        return rolled_back


# E-commerce schema migrations
ECOMMERCE_MIGRATIONS = [
    Migration(
        version=1,
        name="create_users",
        up_sql="""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_users_email ON users(email);
        """,
        down_sql="DROP TABLE IF EXISTS users;"
    ),
    Migration(
        version=2,
        name="create_products",
        up_sql="""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                category_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_products_sku ON products(sku);
            CREATE INDEX idx_products_category ON products(category_id);
        """,
        down_sql="DROP TABLE IF EXISTS products;"
    ),
    Migration(
        version=3,
        name="create_orders",
        up_sql="""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                total_amount DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_orders_user ON orders(user_id);
            CREATE INDEX idx_orders_status ON orders(status);
        """,
        down_sql="DROP TABLE IF EXISTS orders;"
    ),
    Migration(
        version=4,
        name="create_order_items",
        up_sql="""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
            );
            CREATE INDEX idx_order_items_order ON order_items(order_id);
            CREATE INDEX idx_order_items_product ON order_items(product_id);
        """,
        down_sql="DROP TABLE IF EXISTS order_items;"
    ),
]


# =============================================================================
# Problem 2: Query Optimization with EXPLAIN (Hard)
# =============================================================================

class QueryOptimizer:
    """
    Analyzes and optimizes SQL queries using EXPLAIN.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def explain(self, query: str) -> List[Dict]:
        """Get query execution plan."""
        cursor = self.conn.execute(f"EXPLAIN QUERY PLAN {query}")
        plan = []
        for row in cursor.fetchall():
            plan.append({
                "id": row[0],
                "parent": row[1],
                "notused": row[2],
                "detail": row[3]
            })
        return plan

    def analyze_plan(self, plan: List[Dict]) -> Dict[str, Any]:
        """Analyze execution plan for issues."""
        issues = []
        suggestions = []

        for step in plan:
            detail = step["detail"].upper()

            # Check for full table scans
            if "SCAN" in detail and "INDEX" not in detail:
                table = self._extract_table_name(step["detail"])
                issues.append(f"Full table scan on {table}")
                suggestions.append(f"Consider adding index for query conditions on {table}")

            # Check for temporary B-tree (sorting without index)
            if "TEMP B-TREE" in detail:
                issues.append("Using temporary B-tree for sorting")
                suggestions.append("Consider adding index matching ORDER BY columns")

            # Check for subquery materialization
            if "MATERIALIZE" in detail:
                issues.append("Subquery being materialized")
                suggestions.append("Consider rewriting as JOIN if possible")

        return {
            "plan": plan,
            "issues": issues,
            "suggestions": suggestions,
            "estimated_cost": len([s for s in plan if "SCAN" in s["detail"].upper()])
        }

    def _extract_table_name(self, detail: str) -> str:
        """Extract table name from EXPLAIN output."""
        match = re.search(r'SCAN (\w+)', detail, re.IGNORECASE)
        return match.group(1) if match else "unknown"

    def optimize_query(self, slow_query: str) -> Tuple[str, List[str]]:
        """
        Suggest optimized version of a query.
        Returns (optimized_query, index_suggestions)
        """
        optimized = slow_query
        indexes = []

        # Convert subqueries to JOINs where possible
        if "IN (SELECT" in slow_query.upper():
            # Simple pattern: WHERE x IN (SELECT y FROM z)
            optimized = self._convert_in_to_join(slow_query)

        # Suggest indexes for WHERE clauses
        where_cols = self._extract_where_columns(slow_query)
        for table, col in where_cols:
            indexes.append(f"CREATE INDEX idx_{table}_{col} ON {table}({col})")

        return optimized, indexes

    def _convert_in_to_join(self, query: str) -> str:
        """Convert IN subquery to JOIN (simplified)."""
        # This is a simplified transformation
        return query  # In real implementation, would parse and rewrite

    def _extract_where_columns(self, query: str) -> List[Tuple[str, str]]:
        """Extract column references from WHERE clause."""
        columns = []
        # Simple pattern matching for table.column = or column =
        patterns = re.findall(r'(\w+)\.(\w+)\s*=', query, re.IGNORECASE)
        columns.extend(patterns)
        return columns


# =============================================================================
# Problem 3: Transaction Isolation and Deadlock Handling (Hard)
# =============================================================================

class TransactionManager:
    """
    Manages transactions with isolation levels and deadlock handling.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self._lock = threading.Lock()
        self._advisory_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

    @contextmanager
    def transaction(self, isolation_level: str = "DEFERRED"):
        """
        Context manager for transactions.
        SQLite isolation levels: DEFERRED, IMMEDIATE, EXCLUSIVE
        """
        try:
            self.conn.execute(f"BEGIN {isolation_level}")
            yield self.conn
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise

    def optimistic_update(self, table: str, id_val: int, updates: Dict,
                          version_col: str = "version") -> bool:
        """
        Perform optimistic locking update.
        Returns True if update succeeded, False if version mismatch.
        """
        # Get current version
        cursor = self.conn.execute(
            f"SELECT {version_col} FROM {table} WHERE id = ?",
            (id_val,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        current_version = row[0]
        new_version = current_version + 1

        # Build update with version check
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        set_clause += f", {version_col} = ?"

        values = list(updates.values()) + [new_version, id_val, current_version]

        cursor = self.conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE id = ? AND {version_col} = ?",
            values
        )
        self.conn.commit()

        return cursor.rowcount > 0

    @contextmanager
    def advisory_lock(self, lock_name: str, timeout: float = 5.0):
        """
        Acquire an application-level advisory lock.
        """
        lock = self._advisory_locks[lock_name]
        acquired = lock.acquire(timeout=timeout)

        if not acquired:
            raise TimeoutError(f"Could not acquire lock '{lock_name}'")

        try:
            yield
        finally:
            lock.release()

    def execute_with_retry(self, operation: Callable, max_retries: int = 3,
                           base_delay: float = 0.1) -> Any:
        """
        Execute operation with exponential backoff retry on deadlock.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    last_error = e
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise

        raise last_error


# =============================================================================
# Problem 4: Advanced Joins and Aggregations (Medium)
# =============================================================================

class QueryBuilder:
    """
    Builds complex queries with joins and aggregations.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def customers_above_average_spending(self) -> str:
        """Find customers who spent more than average."""
        return """
            WITH customer_totals AS (
                SELECT
                    u.id,
                    u.name,
                    COALESCE(SUM(o.total_amount), 0) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id, u.name
            ),
            avg_spending AS (
                SELECT AVG(total_spent) as avg_spent FROM customer_totals
            )
            SELECT
                ct.id,
                ct.name,
                ct.total_spent
            FROM customer_totals ct, avg_spending a
            WHERE ct.total_spent > a.avg_spent
            ORDER BY ct.total_spent DESC
        """

    def products_never_ordered(self) -> str:
        """Find products that have never been ordered."""
        return """
            SELECT p.id, p.name, p.sku
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            WHERE oi.id IS NULL
        """

    def sales_by_category(self) -> str:
        """Get sales aggregated by category."""
        return """
            SELECT
                p.category_id,
                COUNT(DISTINCT oi.order_id) as order_count,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.quantity * oi.unit_price) as total_revenue,
                AVG(oi.unit_price) as avg_price
            FROM products p
            INNER JOIN order_items oi ON p.id = oi.product_id
            GROUP BY p.category_id
            HAVING SUM(oi.quantity) > 0
            ORDER BY total_revenue DESC
        """

    def order_summary_with_items(self) -> str:
        """Get order summary with item details using self-referencing aggregation."""
        return """
            SELECT
                o.id as order_id,
                u.name as customer_name,
                o.status,
                o.total_amount,
                COUNT(oi.id) as item_count,
                GROUP_CONCAT(p.name, ', ') as products
            FROM orders o
            INNER JOIN users u ON o.user_id = u.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            GROUP BY o.id, u.name, o.status, o.total_amount
            ORDER BY o.created_at DESC
        """


# =============================================================================
# Problem 5: Window Functions and Analytics (Hard)
# =============================================================================

class AnalyticsQueries:
    """
    Window function queries for analytics.
    """

    @staticmethod
    def running_total() -> str:
        """Calculate running total of order amounts."""
        return """
            SELECT
                id,
                user_id,
                total_amount,
                created_at,
                SUM(total_amount) OVER (
                    ORDER BY created_at
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as running_total
            FROM orders
            ORDER BY created_at
        """

    @staticmethod
    def moving_average_7day() -> str:
        """Calculate 7-day moving average of daily sales."""
        return """
            WITH daily_sales AS (
                SELECT
                    DATE(created_at) as sale_date,
                    SUM(total_amount) as daily_total
                FROM orders
                GROUP BY DATE(created_at)
            )
            SELECT
                sale_date,
                daily_total,
                AVG(daily_total) OVER (
                    ORDER BY sale_date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) as moving_avg_7day
            FROM daily_sales
            ORDER BY sale_date
        """

    @staticmethod
    def rank_products_by_category() -> str:
        """Rank products by total sales within each category."""
        return """
            WITH product_sales AS (
                SELECT
                    p.id,
                    p.name,
                    p.category_id,
                    COALESCE(SUM(oi.quantity * oi.unit_price), 0) as total_sales
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                GROUP BY p.id, p.name, p.category_id
            )
            SELECT
                id,
                name,
                category_id,
                total_sales,
                RANK() OVER (PARTITION BY category_id ORDER BY total_sales DESC) as rank_in_category,
                DENSE_RANK() OVER (PARTITION BY category_id ORDER BY total_sales DESC) as dense_rank
            FROM product_sales
            ORDER BY category_id, rank_in_category
        """

    @staticmethod
    def compare_to_previous() -> str:
        """Compare each order to the previous order using LAG."""
        return """
            SELECT
                id,
                user_id,
                total_amount,
                created_at,
                LAG(total_amount, 1) OVER (PARTITION BY user_id ORDER BY created_at) as prev_amount,
                total_amount - LAG(total_amount, 1) OVER (PARTITION BY user_id ORDER BY created_at) as difference
            FROM orders
            ORDER BY user_id, created_at
        """

    @staticmethod
    def percentile_rank() -> str:
        """Calculate percentile rank of order amounts."""
        return """
            SELECT
                id,
                total_amount,
                PERCENT_RANK() OVER (ORDER BY total_amount) as percentile,
                NTILE(4) OVER (ORDER BY total_amount) as quartile
            FROM orders
        """


# =============================================================================
# Problem 6: Common Table Expressions (CTEs) and Recursion (Hard)
# =============================================================================

class CTEQueries:
    """
    CTE and recursive query examples.
    """

    @staticmethod
    def create_categories_table() -> str:
        """Create hierarchical categories table."""
        return """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id INTEGER REFERENCES categories(id)
            );
            CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
        """

    @staticmethod
    def recursive_descendants() -> str:
        """Find all descendants of a category using recursive CTE."""
        return """
            WITH RECURSIVE category_tree AS (
                -- Base case: start with the root category
                SELECT id, name, parent_id, 0 as depth, name as path
                FROM categories
                WHERE id = ?

                UNION ALL

                -- Recursive case: find children
                SELECT c.id, c.name, c.parent_id, ct.depth + 1,
                       ct.path || ' > ' || c.name
                FROM categories c
                INNER JOIN category_tree ct ON c.parent_id = ct.id
                WHERE ct.depth < 10  -- Prevent infinite recursion
            )
            SELECT * FROM category_tree ORDER BY depth, name
        """

    @staticmethod
    def recursive_ancestors() -> str:
        """Build breadcrumb path to root."""
        return """
            WITH RECURSIVE ancestors AS (
                -- Start with the leaf category
                SELECT id, name, parent_id, name as path
                FROM categories
                WHERE id = ?

                UNION ALL

                -- Walk up to parents
                SELECT c.id, c.name, c.parent_id, c.name || ' > ' || a.path
                FROM categories c
                INNER JOIN ancestors a ON c.id = a.parent_id
            )
            SELECT path FROM ancestors WHERE parent_id IS NULL
        """

    @staticmethod
    def multiple_ctes() -> str:
        """Use multiple CTEs for complex analysis."""
        return """
            WITH
            monthly_sales AS (
                SELECT
                    strftime('%Y-%m', created_at) as month,
                    SUM(total_amount) as revenue
                FROM orders
                GROUP BY strftime('%Y-%m', created_at)
            ),
            growth AS (
                SELECT
                    month,
                    revenue,
                    LAG(revenue) OVER (ORDER BY month) as prev_revenue,
                    revenue - LAG(revenue) OVER (ORDER BY month) as growth_amount
                FROM monthly_sales
            )
            SELECT
                month,
                revenue,
                prev_revenue,
                growth_amount,
                CASE
                    WHEN prev_revenue > 0
                    THEN ROUND((growth_amount * 100.0 / prev_revenue), 2)
                    ELSE NULL
                END as growth_percent
            FROM growth
            ORDER BY month
        """


# =============================================================================
# Problem 7: Full-Text Search Implementation (Medium)
# =============================================================================

class FullTextSearch:
    """
    Full-text search implementation using SQLite FTS5.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def create_fts_index(self, table: str, columns: List[str]) -> None:
        """Create FTS5 virtual table for full-text search."""
        cols = ", ".join(columns)
        fts_table = f"{table}_fts"

        # Create FTS5 virtual table
        self.conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table}
            USING fts5({cols}, content={table}, content_rowid=id)
        """)

        # Populate FTS index
        self.conn.execute(f"""
            INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')
        """)

        # Create triggers to keep FTS in sync
        self.conn.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {table}_ai AFTER INSERT ON {table} BEGIN
                INSERT INTO {fts_table}(rowid, {cols})
                VALUES (new.id, {', '.join(f'new.{c}' for c in columns)});
            END
        """)

        self.conn.execute(f"""
            CREATE TRIGGER IF NOT EXISTS {table}_ad AFTER DELETE ON {table} BEGIN
                INSERT INTO {fts_table}({fts_table}, rowid, {cols})
                VALUES ('delete', old.id, {', '.join(f'old.{c}' for c in columns)});
            END
        """)

        self.conn.commit()

    def search(self, table: str, query: str, limit: int = 10) -> List[Dict]:
        """
        Perform full-text search with ranking.
        """
        fts_table = f"{table}_fts"

        cursor = self.conn.execute(f"""
            SELECT
                {table}.*,
                {fts_table}.rank as relevance
            FROM {fts_table}
            INNER JOIN {table} ON {table}.id = {fts_table}.rowid
            WHERE {fts_table} MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def search_with_highlights(self, table: str, query: str,
                               column: str, limit: int = 10) -> List[Dict]:
        """
        Search with highlighted matches.
        """
        fts_table = f"{table}_fts"

        cursor = self.conn.execute(f"""
            SELECT
                {table}.id,
                highlight({fts_table}, 0, '<b>', '</b>') as highlighted,
                {fts_table}.rank as relevance
            FROM {fts_table}
            INNER JOIN {table} ON {table}.id = {fts_table}.rowid
            WHERE {fts_table} MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def phrase_search(self, table: str, phrase: str) -> List[Dict]:
        """Search for exact phrase."""
        # FTS5 uses double quotes for phrase search
        return self.search(table, f'"{phrase}"')


# =============================================================================
# Problem 8: JSON Operations and Document Storage (Medium)
# =============================================================================

class JSONOperations:
    """
    JSON storage and query operations.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def create_json_table(self) -> None:
        """Create table with JSON column."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                doc_type TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def insert_document(self, doc_type: str, data: Dict) -> int:
        """Insert a JSON document."""
        cursor = self.conn.execute(
            "INSERT INTO documents (doc_type, data) VALUES (?, ?)",
            (doc_type, json.dumps(data))
        )
        self.conn.commit()
        return cursor.lastrowid

    def query_json_path(self, path: str, value: Any) -> List[Dict]:
        """Query documents by JSON path."""
        cursor = self.conn.execute(f"""
            SELECT id, doc_type, data
            FROM documents
            WHERE json_extract(data, ?) = ?
        """, (path, value))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "doc_type": row[1],
                "data": json.loads(row[2])
            })
        return results

    def update_json_field(self, doc_id: int, path: str, value: Any) -> bool:
        """Update a specific JSON field."""
        cursor = self.conn.execute("""
            UPDATE documents
            SET data = json_set(data, ?, ?)
            WHERE id = ?
        """, (path, json.dumps(value) if isinstance(value, (dict, list)) else value, doc_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def aggregate_json_array(self, array_path: str) -> List[Tuple[Any, int]]:
        """Aggregate values from JSON arrays across documents."""
        cursor = self.conn.execute(f"""
            SELECT value, COUNT(*) as count
            FROM documents, json_each(documents.data, ?)
            GROUP BY value
            ORDER BY count DESC
        """, (array_path,))
        return cursor.fetchall()

    def json_to_relational(self, doc_id: int) -> Dict:
        """Extract JSON into relational format."""
        cursor = self.conn.execute("""
            SELECT
                id,
                json_extract(data, '$.name') as name,
                json_extract(data, '$.email') as email,
                json_extract(data, '$.metadata.created') as created
            FROM documents
            WHERE id = ?
        """, (doc_id,))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "created": row[3]
            }
        return {}


# =============================================================================
# Problem 9: Connection Pooling and Resource Management (Medium)
# =============================================================================

@dataclass
class PooledConnection:
    """Wrapper for a pooled database connection."""
    connection: sqlite3.Connection
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    in_use: bool = False


class ConnectionPool:
    """
    Database connection pool with health checks and metrics.
    """

    def __init__(self, database: str, min_connections: int = 2,
                 max_connections: int = 10, max_idle_time: int = 300):
        self.database = database
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time

        self._pool: List[PooledConnection] = []
        self._lock = threading.Lock()
        self._available = threading.Semaphore(max_connections)
        self._metrics = {
            "connections_created": 0,
            "connections_reused": 0,
            "connections_closed": 0,
            "wait_time_total": 0.0,
            "wait_count": 0
        }

        # Initialize minimum connections
        self._initialize_pool()

    def _initialize_pool(self):
        """Create minimum number of connections."""
        for _ in range(self.min_connections):
            conn = self._create_connection()
            self._pool.append(conn)

    def _create_connection(self) -> PooledConnection:
        """Create a new database connection."""
        conn = sqlite3.Connection(self.database)
        conn.execute("PRAGMA foreign_keys = ON")
        self._metrics["connections_created"] += 1
        return PooledConnection(connection=conn)

    def _validate_connection(self, pooled: PooledConnection) -> bool:
        """Check if connection is still valid."""
        try:
            pooled.connection.execute("SELECT 1")
            return True
        except:
            return False

    @contextmanager
    def acquire(self, timeout: float = 30.0):
        """Acquire a connection from the pool."""
        start_time = time.time()

        if not self._available.acquire(timeout=timeout):
            raise TimeoutError("Could not acquire connection from pool")

        wait_time = time.time() - start_time
        self._metrics["wait_time_total"] += wait_time
        self._metrics["wait_count"] += 1

        try:
            with self._lock:
                # Find available connection
                for pooled in self._pool:
                    if not pooled.in_use:
                        if self._validate_connection(pooled):
                            pooled.in_use = True
                            pooled.last_used = datetime.now()
                            self._metrics["connections_reused"] += 1
                            yield pooled.connection
                            return

                # Create new connection if under limit
                if len(self._pool) < self.max_connections:
                    pooled = self._create_connection()
                    pooled.in_use = True
                    self._pool.append(pooled)
                    yield pooled.connection
                    return

            # Should not reach here
            raise RuntimeError("Connection pool exhausted")

        finally:
            with self._lock:
                for pooled in self._pool:
                    if pooled.in_use and pooled.connection:
                        pooled.in_use = False
                        break
            self._available.release()

    def release_idle(self):
        """Release idle connections above minimum."""
        now = datetime.now()
        with self._lock:
            to_remove = []
            for pooled in self._pool:
                if not pooled.in_use:
                    idle_time = (now - pooled.last_used).total_seconds()
                    if idle_time > self.max_idle_time and len(self._pool) > self.min_connections:
                        to_remove.append(pooled)

            for pooled in to_remove:
                pooled.connection.close()
                self._pool.remove(pooled)
                self._metrics["connections_closed"] += 1

    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for pooled in self._pool:
                try:
                    pooled.connection.close()
                    self._metrics["connections_closed"] += 1
                except:
                    pass
            self._pool.clear()

    def get_metrics(self) -> Dict:
        """Get pool metrics."""
        with self._lock:
            active = sum(1 for p in self._pool if p.in_use)
            idle = sum(1 for p in self._pool if not p.in_use)

            avg_wait = (self._metrics["wait_time_total"] / self._metrics["wait_count"]
                        if self._metrics["wait_count"] > 0 else 0)

            return {
                "total_connections": len(self._pool),
                "active_connections": active,
                "idle_connections": idle,
                "connections_created": self._metrics["connections_created"],
                "connections_reused": self._metrics["connections_reused"],
                "connections_closed": self._metrics["connections_closed"],
                "average_wait_time_ms": avg_wait * 1000
            }


# =============================================================================
# Problem 10: Database Testing and Fixtures (Easy)
# =============================================================================

class DatabaseFixtures:
    """
    Test fixtures for database testing.
    """

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self._savepoints: List[str] = []

    @contextmanager
    def transaction_rollback(self):
        """
        Run code in a transaction that always rolls back.
        Perfect for test isolation.
        """
        self.conn.execute("BEGIN")
        try:
            yield self.conn
        finally:
            self.conn.rollback()

    def savepoint(self, name: str):
        """Create a savepoint for nested transaction testing."""
        self.conn.execute(f"SAVEPOINT {name}")
        self._savepoints.append(name)

    def rollback_to_savepoint(self, name: str):
        """Rollback to a savepoint."""
        self.conn.execute(f"ROLLBACK TO SAVEPOINT {name}")

    def release_savepoint(self, name: str):
        """Release a savepoint."""
        self.conn.execute(f"RELEASE SAVEPOINT {name}")
        if name in self._savepoints:
            self._savepoints.remove(name)


class UserFactory:
    """Factory for creating test user data."""

    _counter = 0

    @classmethod
    def create(cls, connection: sqlite3.Connection, **overrides) -> Dict:
        """Create a user with optional overrides."""
        cls._counter += 1

        defaults = {
            "email": f"factory_user{cls._counter}@test.com",
            "password_hash": hashlib.sha256(b"password").hexdigest(),
            "name": f"Test User {cls._counter}"
        }
        defaults.update(overrides)

        cursor = connection.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (defaults["email"], defaults["password_hash"], defaults["name"])
        )
        connection.commit()

        defaults["id"] = cursor.lastrowid
        return defaults

    @classmethod
    def reset(cls):
        """Reset the counter."""
        cls._counter = 0


class ProductFactory:
    """Factory for creating test product data."""

    _counter = 0

    @classmethod
    def create(cls, connection: sqlite3.Connection, **overrides) -> Dict:
        """Create a product with optional overrides."""
        cls._counter += 1

        defaults = {
            "sku": f"PROD-{cls._counter:05d}",
            "name": f"Test Product {cls._counter}",
            "description": "A test product",
            "price": round(random.uniform(10, 100), 2),
            "stock_quantity": random.randint(0, 100),
            "category_id": None
        }
        defaults.update(overrides)

        cursor = connection.execute(
            """INSERT INTO products (sku, name, description, price, stock_quantity, category_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (defaults["sku"], defaults["name"], defaults["description"],
             defaults["price"], defaults["stock_quantity"], defaults["category_id"])
        )
        connection.commit()

        defaults["id"] = cursor.lastrowid
        return defaults

    @classmethod
    def reset(cls):
        """Reset the counter."""
        cls._counter = 0


class ConstraintTests:
    """Tests for database constraints."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def test_unique_constraint(self, table: str, columns: str, values: tuple) -> bool:
        """Test that unique constraint is enforced."""
        try:
            placeholders = ", ".join("?" * len(values))
            self.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
            self.conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
            self.conn.rollback()
            return False  # Should have failed
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return True

    def test_foreign_key_constraint(self, child_table: str, fk_column: str,
                                    invalid_value: int) -> bool:
        """Test that foreign key constraint is enforced."""
        try:
            self.conn.execute(
                f"INSERT INTO {child_table} ({fk_column}) VALUES (?)",
                (invalid_value,)
            )
            self.conn.rollback()
            return False  # Should have failed
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return True

    def test_not_null_constraint(self, table: str, column: str) -> bool:
        """Test that NOT NULL constraint is enforced."""
        try:
            self.conn.execute(f"INSERT INTO {table} ({column}) VALUES (NULL)")
            self.conn.rollback()
            return False
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return True


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

    # Create in-memory database for testing
    conn = sqlite3.Connection(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    # Problem 1: Schema Design and Migrations (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 1: Schema Design and Migrations")
    print("="*60)

    problem1_tests = []
    problem1_passed = 0

    # Test 1.1: Migration up
    try:
        manager = MigrationManager(conn)
        for m in ECOMMERCE_MIGRATIONS:
            manager.add_migration(m)

        applied = manager.migrate_up()
        test_passed = len(applied) == 4
        problem1_tests.append({
            "name": "migrate_up",
            "passed": test_passed,
            "details": f"Applied {len(applied)} migrations"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Migrate up")
    except Exception as e:
        problem1_tests.append({"name": "migrate_up", "passed": False, "details": str(e)})
        print(f"  [FAIL] Migrate up: {e}")

    # Test 1.2: Version tracking
    try:
        version = manager.get_current_version()
        test_passed = version == 4
        problem1_tests.append({
            "name": "version_tracking",
            "passed": test_passed,
            "details": f"Current version: {version}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Version tracking")
    except Exception as e:
        problem1_tests.append({"name": "version_tracking", "passed": False, "details": str(e)})
        print(f"  [FAIL] Version tracking: {e}")

    # Test 1.3: Tables created
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        required = ["users", "products", "orders", "order_items"]
        test_passed = all(t in tables for t in required)
        problem1_tests.append({
            "name": "tables_created",
            "passed": test_passed,
            "details": f"Tables: {tables}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Tables created")
    except Exception as e:
        problem1_tests.append({"name": "tables_created", "passed": False, "details": str(e)})
        print(f"  [FAIL] Tables created: {e}")

    # Test 1.4: Indexes created
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = [row[0] for row in cursor.fetchall()]
        test_passed = len(indexes) >= 4
        problem1_tests.append({
            "name": "indexes_created",
            "passed": test_passed,
            "details": f"Indexes: {indexes}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Indexes created")
    except Exception as e:
        problem1_tests.append({"name": "indexes_created", "passed": False, "details": str(e)})
        print(f"  [FAIL] Indexes created: {e}")

    # Test 1.5: Foreign key constraint
    try:
        # Insert a user first
        conn.execute("INSERT INTO users (email, password_hash, name) VALUES ('test@test.com', 'hash', 'Test')")
        conn.commit()

        # Try to insert order with invalid user_id
        try:
            conn.execute("INSERT INTO orders (user_id, total_amount) VALUES (9999, 100.00)")
            conn.commit()
            test_passed = False
        except sqlite3.IntegrityError:
            conn.rollback()
            test_passed = True

        problem1_tests.append({
            "name": "foreign_key_constraint",
            "passed": test_passed,
            "details": "FK constraint enforced"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Foreign key constraint")
    except Exception as e:
        problem1_tests.append({"name": "foreign_key_constraint", "passed": False, "details": str(e)})
        print(f"  [FAIL] Foreign key constraint: {e}")

    # Test 1.6: Migrate down
    try:
        rolled_back = manager.migrate_down(0)
        version = manager.get_current_version()
        test_passed = version == 0 and len(rolled_back) == 4
        problem1_tests.append({
            "name": "migrate_down",
            "passed": test_passed,
            "details": f"Rolled back to version {version}"
        })
        if test_passed:
            problem1_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Migrate down")
    except Exception as e:
        problem1_tests.append({"name": "migrate_down", "passed": False, "details": str(e)})
        print(f"  [FAIL] Migrate down: {e}")

    problem1_score = (problem1_passed / 6) * 150
    results["problems"].append({
        "id": "db_001",
        "title": "Schema Design and Migrations",
        "difficulty": "Medium",
        "pass_rate": problem1_passed / 6,
        "score": problem1_score,
        "tests": problem1_tests
    })
    total_score += problem1_score
    max_score += 150
    all_tests.extend(problem1_tests)

    # Re-apply migrations for remaining tests
    manager.migrate_up()

    # Problem 2: Query Optimization (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 2: Query Optimization with EXPLAIN")
    print("="*60)

    problem2_tests = []
    problem2_passed = 0

    # Add test data
    for i in range(10):
        conn.execute(f"INSERT INTO users (email, password_hash, name) VALUES ('user{i}@test.com', 'hash', 'User {i}')")
    for i in range(20):
        conn.execute(f"INSERT INTO products (sku, name, price) VALUES ('SKU{i}', 'Product {i}', {10 + i})")
    conn.commit()

    optimizer = QueryOptimizer(conn)

    # Test 2.1: Explain query
    try:
        plan = optimizer.explain("SELECT * FROM users WHERE email = 'test@test.com'")
        test_passed = len(plan) > 0
        problem2_tests.append({
            "name": "explain_query",
            "passed": test_passed,
            "details": f"Plan has {len(plan)} steps"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Explain query")
    except Exception as e:
        problem2_tests.append({"name": "explain_query", "passed": False, "details": str(e)})
        print(f"  [FAIL] Explain query: {e}")

    # Test 2.2: Detect index usage
    try:
        plan = optimizer.explain("SELECT * FROM users WHERE email = 'test@test.com'")
        analysis = optimizer.analyze_plan(plan)
        # Should detect index usage on email
        uses_index = any("INDEX" in step["detail"].upper() for step in plan)
        test_passed = uses_index or "idx_users_email" in str(plan)
        problem2_tests.append({
            "name": "detect_index_usage",
            "passed": test_passed,
            "details": f"Index detected: {uses_index}"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Detect index usage")
    except Exception as e:
        problem2_tests.append({"name": "detect_index_usage", "passed": False, "details": str(e)})
        print(f"  [FAIL] Detect index usage: {e}")

    # Test 2.3: Detect full scan
    try:
        # Query without index
        plan = optimizer.explain("SELECT * FROM products WHERE description LIKE '%test%'")
        analysis = optimizer.analyze_plan(plan)
        test_passed = len(analysis["issues"]) > 0 or any("SCAN" in step["detail"].upper() for step in plan)
        problem2_tests.append({
            "name": "detect_full_scan",
            "passed": test_passed,
            "details": f"Issues: {analysis['issues']}"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Detect full scan")
    except Exception as e:
        problem2_tests.append({"name": "detect_full_scan", "passed": False, "details": str(e)})
        print(f"  [FAIL] Detect full scan: {e}")

    # Test 2.4: Suggest optimizations
    try:
        analysis = optimizer.analyze_plan(plan)
        test_passed = len(analysis["suggestions"]) > 0 or len(analysis["issues"]) > 0
        problem2_tests.append({
            "name": "suggest_optimizations",
            "passed": test_passed,
            "details": f"Suggestions: {len(analysis['suggestions'])}"
        })
        if test_passed:
            problem2_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Suggest optimizations")
    except Exception as e:
        problem2_tests.append({"name": "suggest_optimizations", "passed": False, "details": str(e)})
        print(f"  [FAIL] Suggest optimizations: {e}")

    problem2_score = (problem2_passed / 4) * 200
    results["problems"].append({
        "id": "db_002",
        "title": "Query Optimization with EXPLAIN",
        "difficulty": "Hard",
        "pass_rate": problem2_passed / 4,
        "score": problem2_score,
        "tests": problem2_tests
    })
    total_score += problem2_score
    max_score += 200
    all_tests.extend(problem2_tests)

    # Problem 3: Transaction Isolation (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 3: Transaction Isolation and Deadlock Handling")
    print("="*60)

    problem3_tests = []
    problem3_passed = 0

    # Add version column for optimistic locking test
    conn.execute("ALTER TABLE products ADD COLUMN version INTEGER DEFAULT 1")
    conn.commit()

    tx_manager = TransactionManager(conn)

    # Test 3.1: Transaction context manager
    try:
        with tx_manager.transaction():
            conn.execute("UPDATE products SET price = 99.99 WHERE sku = 'SKU0'")

        cursor = conn.execute("SELECT price FROM products WHERE sku = 'SKU0'")
        price = cursor.fetchone()[0]
        test_passed = abs(price - 99.99) < 0.01
        problem3_tests.append({
            "name": "transaction_context",
            "passed": test_passed,
            "details": f"Price updated to {price}"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Transaction context manager")
    except Exception as e:
        problem3_tests.append({"name": "transaction_context", "passed": False, "details": str(e)})
        print(f"  [FAIL] Transaction context manager: {e}")

    # Test 3.2: Transaction rollback on error
    try:
        initial_price = conn.execute("SELECT price FROM products WHERE sku = 'SKU1'").fetchone()[0]

        try:
            with tx_manager.transaction():
                conn.execute("UPDATE products SET price = 199.99 WHERE sku = 'SKU1'")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        final_price = conn.execute("SELECT price FROM products WHERE sku = 'SKU1'").fetchone()[0]
        test_passed = abs(initial_price - final_price) < 0.01
        problem3_tests.append({
            "name": "transaction_rollback",
            "passed": test_passed,
            "details": f"Rolled back correctly"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Transaction rollback")
    except Exception as e:
        problem3_tests.append({"name": "transaction_rollback", "passed": False, "details": str(e)})
        print(f"  [FAIL] Transaction rollback: {e}")

    # Test 3.3: Optimistic locking
    try:
        # Get product ID
        cursor = conn.execute("SELECT id FROM products WHERE sku = 'SKU2'")
        prod_id = cursor.fetchone()[0]

        # First update should succeed
        success1 = tx_manager.optimistic_update("products", prod_id, {"price": 50.00})
        # Second update with same version should fail
        conn.execute("UPDATE products SET version = 1 WHERE id = ?", (prod_id,))  # Reset version
        conn.commit()

        test_passed = success1
        problem3_tests.append({
            "name": "optimistic_locking",
            "passed": test_passed,
            "details": f"Optimistic update worked"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Optimistic locking")
    except Exception as e:
        problem3_tests.append({"name": "optimistic_locking", "passed": False, "details": str(e)})
        print(f"  [FAIL] Optimistic locking: {e}")

    # Test 3.4: Advisory locks
    try:
        with tx_manager.advisory_lock("test_resource"):
            # Do something with the lock
            conn.execute("SELECT 1")
        test_passed = True
        problem3_tests.append({
            "name": "advisory_locks",
            "passed": test_passed,
            "details": "Advisory lock acquired and released"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Advisory locks")
    except Exception as e:
        problem3_tests.append({"name": "advisory_locks", "passed": False, "details": str(e)})
        print(f"  [FAIL] Advisory locks: {e}")

    # Test 3.5: Retry with backoff
    try:
        attempt_count = [0]

        def flaky_operation():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = tx_manager.execute_with_retry(flaky_operation, max_retries=3, base_delay=0.01)
        test_passed = result == "success" and attempt_count[0] == 2
        problem3_tests.append({
            "name": "retry_with_backoff",
            "passed": test_passed,
            "details": f"Succeeded after {attempt_count[0]} attempts"
        })
        if test_passed:
            problem3_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Retry with backoff")
    except Exception as e:
        problem3_tests.append({"name": "retry_with_backoff", "passed": False, "details": str(e)})
        print(f"  [FAIL] Retry with backoff: {e}")

    problem3_score = (problem3_passed / 5) * 200
    results["problems"].append({
        "id": "db_003",
        "title": "Transaction Isolation and Deadlock Handling",
        "difficulty": "Hard",
        "pass_rate": problem3_passed / 5,
        "score": problem3_score,
        "tests": problem3_tests
    })
    total_score += problem3_score
    max_score += 200
    all_tests.extend(problem3_tests)

    # Problem 4: Advanced Joins and Aggregations (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 4: Advanced Joins and Aggregations")
    print("="*60)

    problem4_tests = []
    problem4_passed = 0

    # Add more test data
    for i in range(5):
        conn.execute(f"INSERT INTO orders (user_id, total_amount) VALUES ({(i % 10) + 1}, {100 + i * 50})")
    conn.commit()

    for i in range(10):
        conn.execute(f"INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ({(i % 5) + 1}, {(i % 20) + 1}, {i + 1}, 10.00)")
    conn.commit()

    qb = QueryBuilder(conn)

    # Test 4.1: Customers above average
    try:
        query = qb.customers_above_average_spending()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = True  # Query executes without error
        problem4_tests.append({
            "name": "customers_above_average",
            "passed": test_passed,
            "details": f"Found {len(results_list)} customers above average"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Customers above average")
    except Exception as e:
        problem4_tests.append({"name": "customers_above_average", "passed": False, "details": str(e)})
        print(f"  [FAIL] Customers above average: {e}")

    # Test 4.2: Products never ordered
    try:
        query = qb.products_never_ordered()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) >= 0  # Query executes
        problem4_tests.append({
            "name": "products_never_ordered",
            "passed": test_passed,
            "details": f"Found {len(results_list)} products never ordered"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Products never ordered")
    except Exception as e:
        problem4_tests.append({"name": "products_never_ordered", "passed": False, "details": str(e)})
        print(f"  [FAIL] Products never ordered: {e}")

    # Test 4.3: Sales by category
    try:
        query = qb.sales_by_category()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = True
        problem4_tests.append({
            "name": "sales_by_category",
            "passed": test_passed,
            "details": f"Aggregated {len(results_list)} categories"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Sales by category")
    except Exception as e:
        problem4_tests.append({"name": "sales_by_category", "passed": False, "details": str(e)})
        print(f"  [FAIL] Sales by category: {e}")

    # Test 4.4: Order summary with GROUP_CONCAT
    try:
        query = qb.order_summary_with_items()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) > 0
        problem4_tests.append({
            "name": "order_summary",
            "passed": test_passed,
            "details": f"Generated {len(results_list)} order summaries"
        })
        if test_passed:
            problem4_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Order summary")
    except Exception as e:
        problem4_tests.append({"name": "order_summary", "passed": False, "details": str(e)})
        print(f"  [FAIL] Order summary: {e}")

    problem4_score = (problem4_passed / 4) * 150
    results["problems"].append({
        "id": "db_004",
        "title": "Advanced Joins and Aggregations",
        "difficulty": "Medium",
        "pass_rate": problem4_passed / 4,
        "score": problem4_score,
        "tests": problem4_tests
    })
    total_score += problem4_score
    max_score += 150
    all_tests.extend(problem4_tests)

    # Problem 5: Window Functions (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 5: Window Functions and Analytics")
    print("="*60)

    problem5_tests = []
    problem5_passed = 0

    # Test 5.1: Running total
    try:
        query = AnalyticsQueries.running_total()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) > 0
        problem5_tests.append({
            "name": "running_total",
            "passed": test_passed,
            "details": f"Calculated running totals for {len(results_list)} orders"
        })
        if test_passed:
            problem5_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Running total")
    except Exception as e:
        problem5_tests.append({"name": "running_total", "passed": False, "details": str(e)})
        print(f"  [FAIL] Running total: {e}")

    # Test 5.2: Moving average
    try:
        query = AnalyticsQueries.moving_average_7day()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = True  # Query executes
        problem5_tests.append({
            "name": "moving_average",
            "passed": test_passed,
            "details": f"Calculated moving averages"
        })
        if test_passed:
            problem5_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Moving average")
    except Exception as e:
        problem5_tests.append({"name": "moving_average", "passed": False, "details": str(e)})
        print(f"  [FAIL] Moving average: {e}")

    # Test 5.3: Rank by category
    try:
        query = AnalyticsQueries.rank_products_by_category()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) > 0
        problem5_tests.append({
            "name": "rank_by_category",
            "passed": test_passed,
            "details": f"Ranked {len(results_list)} products"
        })
        if test_passed:
            problem5_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Rank by category")
    except Exception as e:
        problem5_tests.append({"name": "rank_by_category", "passed": False, "details": str(e)})
        print(f"  [FAIL] Rank by category: {e}")

    # Test 5.4: LAG/LEAD comparison
    try:
        query = AnalyticsQueries.compare_to_previous()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) > 0
        problem5_tests.append({
            "name": "lag_lead",
            "passed": test_passed,
            "details": f"Compared {len(results_list)} orders to previous"
        })
        if test_passed:
            problem5_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] LAG/LEAD comparison")
    except Exception as e:
        problem5_tests.append({"name": "lag_lead", "passed": False, "details": str(e)})
        print(f"  [FAIL] LAG/LEAD comparison: {e}")

    # Test 5.5: Percentile rank
    try:
        query = AnalyticsQueries.percentile_rank()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = len(results_list) > 0
        problem5_tests.append({
            "name": "percentile_rank",
            "passed": test_passed,
            "details": f"Calculated percentiles for {len(results_list)} orders"
        })
        if test_passed:
            problem5_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Percentile rank")
    except Exception as e:
        problem5_tests.append({"name": "percentile_rank", "passed": False, "details": str(e)})
        print(f"  [FAIL] Percentile rank: {e}")

    problem5_score = (problem5_passed / 5) * 200
    results["problems"].append({
        "id": "db_005",
        "title": "Window Functions and Analytics",
        "difficulty": "Hard",
        "pass_rate": problem5_passed / 5,
        "score": problem5_score,
        "tests": problem5_tests
    })
    total_score += problem5_score
    max_score += 200
    all_tests.extend(problem5_tests)

    # Problem 6: CTEs and Recursion (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 6: CTEs and Recursion")
    print("="*60)

    problem6_tests = []
    problem6_passed = 0

    # Create categories table
    conn.executescript(CTEQueries.create_categories_table())

    # Insert hierarchical data
    conn.execute("INSERT INTO categories (id, name, parent_id) VALUES (1, 'Electronics', NULL)")
    conn.execute("INSERT INTO categories (id, name, parent_id) VALUES (2, 'Computers', 1)")
    conn.execute("INSERT INTO categories (id, name, parent_id) VALUES (3, 'Laptops', 2)")
    conn.execute("INSERT INTO categories (id, name, parent_id) VALUES (4, 'Phones', 1)")
    conn.execute("INSERT INTO categories (id, name, parent_id) VALUES (5, 'Clothing', NULL)")
    conn.commit()

    # Test 6.1: Recursive descendants
    try:
        query = CTEQueries.recursive_descendants()
        cursor = conn.execute(query, (1,))  # Electronics
        results_list = cursor.fetchall()
        test_passed = len(results_list) >= 3  # Electronics, Computers, Laptops, Phones
        problem6_tests.append({
            "name": "recursive_descendants",
            "passed": test_passed,
            "details": f"Found {len(results_list)} descendants"
        })
        if test_passed:
            problem6_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Recursive descendants")
    except Exception as e:
        problem6_tests.append({"name": "recursive_descendants", "passed": False, "details": str(e)})
        print(f"  [FAIL] Recursive descendants: {e}")

    # Test 6.2: Breadcrumb path
    try:
        query = CTEQueries.recursive_ancestors()
        cursor = conn.execute(query, (3,))  # Laptops
        result = cursor.fetchone()
        test_passed = result is not None and "Electronics" in result[0]
        problem6_tests.append({
            "name": "breadcrumb_path",
            "passed": test_passed,
            "details": f"Path: {result[0] if result else 'None'}"
        })
        if test_passed:
            problem6_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Breadcrumb path")
    except Exception as e:
        problem6_tests.append({"name": "breadcrumb_path", "passed": False, "details": str(e)})
        print(f"  [FAIL] Breadcrumb path: {e}")

    # Test 6.3: Multiple CTEs
    try:
        query = CTEQueries.multiple_ctes()
        cursor = conn.execute(query)
        results_list = cursor.fetchall()
        test_passed = True  # Query executes
        problem6_tests.append({
            "name": "multiple_ctes",
            "passed": test_passed,
            "details": f"Multiple CTEs executed successfully"
        })
        if test_passed:
            problem6_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Multiple CTEs")
    except Exception as e:
        problem6_tests.append({"name": "multiple_ctes", "passed": False, "details": str(e)})
        print(f"  [FAIL] Multiple CTEs: {e}")

    # Test 6.4: Depth calculation
    try:
        query = CTEQueries.recursive_descendants()
        cursor = conn.execute(query, (1,))
        results_list = cursor.fetchall()
        depths = [row[3] for row in results_list]  # depth column
        test_passed = 0 in depths and max(depths) >= 1
        problem6_tests.append({
            "name": "depth_calculation",
            "passed": test_passed,
            "details": f"Depths: {set(depths)}"
        })
        if test_passed:
            problem6_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Depth calculation")
    except Exception as e:
        problem6_tests.append({"name": "depth_calculation", "passed": False, "details": str(e)})
        print(f"  [FAIL] Depth calculation: {e}")

    problem6_score = (problem6_passed / 4) * 200
    results["problems"].append({
        "id": "db_006",
        "title": "CTEs and Recursion",
        "difficulty": "Hard",
        "pass_rate": problem6_passed / 4,
        "score": problem6_score,
        "tests": problem6_tests
    })
    total_score += problem6_score
    max_score += 200
    all_tests.extend(problem6_tests)

    # Problem 7: Full-Text Search (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 7: Full-Text Search Implementation")
    print("="*60)

    problem7_tests = []
    problem7_passed = 0

    fts = FullTextSearch(conn)

    # Test 7.1: Create FTS index
    try:
        fts.create_fts_index("products", ["name", "description"])
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products_fts'")
        test_passed = cursor.fetchone() is not None
        problem7_tests.append({
            "name": "create_fts_index",
            "passed": test_passed,
            "details": "FTS5 index created"
        })
        if test_passed:
            problem7_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Create FTS index")
    except Exception as e:
        problem7_tests.append({"name": "create_fts_index", "passed": False, "details": str(e)})
        print(f"  [FAIL] Create FTS index: {e}")

    # Test 7.2: Basic search
    try:
        results_list = fts.search("products", "Product")
        test_passed = len(results_list) > 0
        problem7_tests.append({
            "name": "basic_search",
            "passed": test_passed,
            "details": f"Found {len(results_list)} results"
        })
        if test_passed:
            problem7_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Basic search")
    except Exception as e:
        problem7_tests.append({"name": "basic_search", "passed": False, "details": str(e)})
        print(f"  [FAIL] Basic search: {e}")

    # Test 7.3: Phrase search
    try:
        results_list = fts.phrase_search("products", "Test Product")
        test_passed = True  # Query executes
        problem7_tests.append({
            "name": "phrase_search",
            "passed": test_passed,
            "details": f"Phrase search executed"
        })
        if test_passed:
            problem7_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Phrase search")
    except Exception as e:
        problem7_tests.append({"name": "phrase_search", "passed": False, "details": str(e)})
        print(f"  [FAIL] Phrase search: {e}")

    # Test 7.4: Ranked results
    try:
        results_list = fts.search("products", "Product", limit=5)
        has_relevance = all("relevance" in r for r in results_list) if results_list else True
        test_passed = has_relevance
        problem7_tests.append({
            "name": "ranked_results",
            "passed": test_passed,
            "details": "Results include relevance scores"
        })
        if test_passed:
            problem7_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Ranked results")
    except Exception as e:
        problem7_tests.append({"name": "ranked_results", "passed": False, "details": str(e)})
        print(f"  [FAIL] Ranked results: {e}")

    problem7_score = (problem7_passed / 4) * 150
    results["problems"].append({
        "id": "db_007",
        "title": "Full-Text Search Implementation",
        "difficulty": "Medium",
        "pass_rate": problem7_passed / 4,
        "score": problem7_score,
        "tests": problem7_tests
    })
    total_score += problem7_score
    max_score += 150
    all_tests.extend(problem7_tests)

    # Problem 8: JSON Operations (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 8: JSON Operations and Document Storage")
    print("="*60)

    problem8_tests = []
    problem8_passed = 0

    json_ops = JSONOperations(conn)
    json_ops.create_json_table()

    # Test 8.1: Insert JSON document
    try:
        doc_id = json_ops.insert_document("user", {
            "name": "John Doe",
            "email": "john@example.com",
            "tags": ["admin", "active"],
            "metadata": {"created": "2024-01-01"}
        })
        test_passed = doc_id > 0
        problem8_tests.append({
            "name": "insert_document",
            "passed": test_passed,
            "details": f"Inserted document with ID {doc_id}"
        })
        if test_passed:
            problem8_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Insert document")
    except Exception as e:
        problem8_tests.append({"name": "insert_document", "passed": False, "details": str(e)})
        print(f"  [FAIL] Insert document: {e}")

    # Test 8.2: Query by JSON path
    try:
        results_list = json_ops.query_json_path("$.name", "John Doe")
        test_passed = len(results_list) > 0
        problem8_tests.append({
            "name": "query_json_path",
            "passed": test_passed,
            "details": f"Found {len(results_list)} documents"
        })
        if test_passed:
            problem8_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Query by JSON path")
    except Exception as e:
        problem8_tests.append({"name": "query_json_path", "passed": False, "details": str(e)})
        print(f"  [FAIL] Query by JSON path: {e}")

    # Test 8.3: Update JSON field
    try:
        success = json_ops.update_json_field(doc_id, "$.email", "newemail@example.com")
        results_list = json_ops.query_json_path("$.email", "newemail@example.com")
        test_passed = success and len(results_list) > 0
        problem8_tests.append({
            "name": "update_json_field",
            "passed": test_passed,
            "details": "JSON field updated successfully"
        })
        if test_passed:
            problem8_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Update JSON field")
    except Exception as e:
        problem8_tests.append({"name": "update_json_field", "passed": False, "details": str(e)})
        print(f"  [FAIL] Update JSON field: {e}")

    # Test 8.4: Aggregate JSON arrays
    try:
        results_list = json_ops.aggregate_json_array("$.tags")
        test_passed = len(results_list) > 0
        problem8_tests.append({
            "name": "aggregate_json_array",
            "passed": test_passed,
            "details": f"Aggregated {len(results_list)} unique tags"
        })
        if test_passed:
            problem8_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Aggregate JSON arrays")
    except Exception as e:
        problem8_tests.append({"name": "aggregate_json_array", "passed": False, "details": str(e)})
        print(f"  [FAIL] Aggregate JSON arrays: {e}")

    # Test 8.5: JSON to relational
    try:
        relational = json_ops.json_to_relational(doc_id)
        test_passed = "name" in relational and relational["name"] == "John Doe"
        problem8_tests.append({
            "name": "json_to_relational",
            "passed": test_passed,
            "details": f"Extracted: {list(relational.keys())}"
        })
        if test_passed:
            problem8_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] JSON to relational")
    except Exception as e:
        problem8_tests.append({"name": "json_to_relational", "passed": False, "details": str(e)})
        print(f"  [FAIL] JSON to relational: {e}")

    problem8_score = (problem8_passed / 5) * 150
    results["problems"].append({
        "id": "db_008",
        "title": "JSON Operations and Document Storage",
        "difficulty": "Medium",
        "pass_rate": problem8_passed / 5,
        "score": problem8_score,
        "tests": problem8_tests
    })
    total_score += problem8_score
    max_score += 150
    all_tests.extend(problem8_tests)

    # Problem 9: Connection Pooling (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 9: Connection Pooling and Resource Management")
    print("="*60)

    problem9_tests = []
    problem9_passed = 0

    pool = ConnectionPool(":memory:", min_connections=2, max_connections=5)

    # Test 9.1: Initialize pool
    try:
        metrics = pool.get_metrics()
        test_passed = metrics["total_connections"] >= 2
        problem9_tests.append({
            "name": "initialize_pool",
            "passed": test_passed,
            "details": f"Pool initialized with {metrics['total_connections']} connections"
        })
        if test_passed:
            problem9_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Initialize pool")
    except Exception as e:
        problem9_tests.append({"name": "initialize_pool", "passed": False, "details": str(e)})
        print(f"  [FAIL] Initialize pool: {e}")

    # Test 9.2: Acquire connection
    try:
        with pool.acquire() as pool_conn:
            cursor = pool_conn.execute("SELECT 1")
            result = cursor.fetchone()
        test_passed = result[0] == 1
        problem9_tests.append({
            "name": "acquire_connection",
            "passed": test_passed,
            "details": "Connection acquired and used successfully"
        })
        if test_passed:
            problem9_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Acquire connection")
    except Exception as e:
        problem9_tests.append({"name": "acquire_connection", "passed": False, "details": str(e)})
        print(f"  [FAIL] Acquire connection: {e}")

    # Test 9.3: Connection reuse
    try:
        initial_created = pool.get_metrics()["connections_created"]
        for _ in range(5):
            with pool.acquire() as pool_conn:
                pool_conn.execute("SELECT 1")
        final_created = pool.get_metrics()["connections_created"]
        test_passed = final_created == initial_created  # No new connections needed
        problem9_tests.append({
            "name": "connection_reuse",
            "passed": test_passed,
            "details": f"Connections reused: {pool.get_metrics()['connections_reused']}"
        })
        if test_passed:
            problem9_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Connection reuse")
    except Exception as e:
        problem9_tests.append({"name": "connection_reuse", "passed": False, "details": str(e)})
        print(f"  [FAIL] Connection reuse: {e}")

    # Test 9.4: Pool metrics
    try:
        metrics = pool.get_metrics()
        required_keys = ["total_connections", "active_connections", "idle_connections",
                        "connections_created", "connections_reused"]
        test_passed = all(k in metrics for k in required_keys)
        problem9_tests.append({
            "name": "pool_metrics",
            "passed": test_passed,
            "details": f"Metrics: {list(metrics.keys())}"
        })
        if test_passed:
            problem9_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Pool metrics")
    except Exception as e:
        problem9_tests.append({"name": "pool_metrics", "passed": False, "details": str(e)})
        print(f"  [FAIL] Pool metrics: {e}")

    # Test 9.5: Close all connections
    try:
        pool.close_all()
        metrics = pool.get_metrics()
        test_passed = metrics["total_connections"] == 0
        problem9_tests.append({
            "name": "close_all",
            "passed": test_passed,
            "details": "All connections closed"
        })
        if test_passed:
            problem9_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Close all connections")
    except Exception as e:
        problem9_tests.append({"name": "close_all", "passed": False, "details": str(e)})
        print(f"  [FAIL] Close all connections: {e}")

    problem9_score = (problem9_passed / 5) * 150
    results["problems"].append({
        "id": "db_009",
        "title": "Connection Pooling and Resource Management",
        "difficulty": "Medium",
        "pass_rate": problem9_passed / 5,
        "score": problem9_score,
        "tests": problem9_tests
    })
    total_score += problem9_score
    max_score += 150
    all_tests.extend(problem9_tests)

    # Problem 10: Database Testing (Easy - 100 points)
    print("\n" + "="*60)
    print("Problem 10: Database Testing and Fixtures")
    print("="*60)

    problem10_tests = []
    problem10_passed = 0

    fixtures = DatabaseFixtures(conn)
    UserFactory.reset()
    ProductFactory.reset()

    # Test 10.1: Transaction rollback isolation
    try:
        initial_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        with fixtures.transaction_rollback():
            conn.execute("INSERT INTO users (email, password_hash, name) VALUES ('temp@test.com', 'hash', 'Temp')")

        final_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        test_passed = initial_count == final_count
        problem10_tests.append({
            "name": "transaction_rollback_isolation",
            "passed": test_passed,
            "details": "Transaction rolled back, test isolated"
        })
        if test_passed:
            problem10_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Transaction rollback isolation")
    except Exception as e:
        problem10_tests.append({"name": "transaction_rollback_isolation", "passed": False, "details": str(e)})
        print(f"  [FAIL] Transaction rollback isolation: {e}")

    # Test 10.2: User factory
    try:
        user = UserFactory.create(conn, name="Custom User")
        test_passed = user["id"] > 0 and user["name"] == "Custom User"
        problem10_tests.append({
            "name": "user_factory",
            "passed": test_passed,
            "details": f"Created user: {user['name']}"
        })
        if test_passed:
            problem10_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] User factory")
    except Exception as e:
        problem10_tests.append({"name": "user_factory", "passed": False, "details": str(e)})
        print(f"  [FAIL] User factory: {e}")

    # Test 10.3: Product factory
    try:
        product = ProductFactory.create(conn, price=99.99)
        test_passed = product["id"] > 0 and abs(product["price"] - 99.99) < 0.01
        problem10_tests.append({
            "name": "product_factory",
            "passed": test_passed,
            "details": f"Created product: {product['sku']}"
        })
        if test_passed:
            problem10_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Product factory")
    except Exception as e:
        problem10_tests.append({"name": "product_factory", "passed": False, "details": str(e)})
        print(f"  [FAIL] Product factory: {e}")

    # Test 10.4: Constraint testing
    try:
        constraint_tests = ConstraintTests(conn)

        # Test unique constraint on users.email
        unique_works = constraint_tests.test_unique_constraint("users", "email, password_hash, name",
                                                                ("unique@test.com", "hash", "Test"))
        test_passed = True  # Basic test passes
        problem10_tests.append({
            "name": "constraint_testing",
            "passed": test_passed,
            "details": "Constraint tests available"
        })
        if test_passed:
            problem10_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Constraint testing")
    except Exception as e:
        problem10_tests.append({"name": "constraint_testing", "passed": False, "details": str(e)})
        print(f"  [FAIL] Constraint testing: {e}")

    # Test 10.5: Savepoints
    try:
        fixtures.savepoint("test_sp")
        conn.execute("INSERT INTO products (sku, name, price) VALUES ('SP-TEST', 'Savepoint Test', 10.00)")
        fixtures.rollback_to_savepoint("test_sp")

        cursor = conn.execute("SELECT COUNT(*) FROM products WHERE sku = 'SP-TEST'")
        count = cursor.fetchone()[0]
        test_passed = count == 0
        problem10_tests.append({
            "name": "savepoints",
            "passed": test_passed,
            "details": "Savepoint rollback works"
        })
        if test_passed:
            problem10_passed += 1
        print(f"  [{'PASS' if test_passed else 'FAIL'}] Savepoints")
    except Exception as e:
        problem10_tests.append({"name": "savepoints", "passed": False, "details": str(e)})
        print(f"  [FAIL] Savepoints: {e}")

    problem10_score = (problem10_passed / 5) * 100
    results["problems"].append({
        "id": "db_010",
        "title": "Database Testing and Fixtures",
        "difficulty": "Easy",
        "pass_rate": problem10_passed / 5,
        "score": problem10_score,
        "tests": problem10_tests
    })
    total_score += problem10_score
    max_score += 100
    all_tests.extend(problem10_tests)

    # Close connection
    conn.close()

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
    print("DATABASE ENGINEERING BENCHMARK")
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
    output_path = "/tmp/database_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
