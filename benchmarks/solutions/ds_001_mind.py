"""
Benchmark Solution: DS_001 - Pandas Data Manipulation
Configuration: MIND (Claude Code + Mind MCP)

Context Retrieved from Mind MCP:
- "NumPy/Pandas for numerical operations (vectorize, don't loop)"
- "List/dict comprehensions over loops for simple transforms"

Enhancements over baseline:
1. Method chaining for cleaner, more Pythonic code
2. Explicit vectorized operations
3. Better error handling with informative messages
4. Performance optimizations (categorical dtype, query method)
"""

import pandas as pd
import numpy as np
from typing import Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_and_process_sales(
    csv_path: Union[str, Path],
    region: str = "North",
    year: int = 2024,
    top_n: int = 5,
    *,
    optimize_memory: bool = True
) -> pd.DataFrame:
    """
    Load sales data and return top products by revenue for a specific region and year.

    Uses vectorized operations and method chaining for optimal performance,
    following best practices from Mind MCP context.

    Args:
        csv_path: Path to the CSV file with sales data
        region: Region to filter (default: "North")
        year: Year to filter (default: 2024)
        top_n: Number of top products to return (default: 5)
        optimize_memory: Convert categorical columns for memory efficiency

    Returns:
        DataFrame with columns [product_id, total_revenue] sorted descending

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing or data is invalid

    Example:
        >>> df = load_and_process_sales("sales.csv", region="North", year=2024)
        >>> print(df.head())
           product_id  total_revenue
        0    PROD_042       131250.0
        1    PROD_002         1300.0
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Sales file not found: {csv_path}")

    # Load with optimized dtypes
    dtype_hints = {
        "product_id": "category" if optimize_memory else "object",
        "region": "category" if optimize_memory else "object",
    }

    try:
        df = pd.read_csv(path, dtype=dtype_hints, parse_dates=["date"])
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}") from e

    # Validate required columns (set operations are O(1) average)
    required_cols = {"date", "product_id", "quantity", "price", "region"}
    actual_cols = set(df.columns)
    if missing := required_cols - actual_cols:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Validate data types
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if df["date"].isna().any():
            logger.warning("Some dates could not be parsed")

    # VECTORIZED: Extract year without loop (Mind MCP best practice)
    # Using .dt accessor for vectorized datetime operations
    year_mask = df["date"].dt.year == year

    # VECTORIZED: Region filter using categorical comparison
    region_mask = df["region"] == region

    # Combine masks (vectorized boolean operations)
    combined_mask = year_mask & region_mask

    filtered = df.loc[combined_mask]

    if filtered.empty:
        logger.info(f"No data found for region={region}, year={year}")
        return pd.DataFrame(columns=["product_id", "total_revenue"])

    # VECTORIZED: Calculate revenue in single operation
    # This is much faster than iterating rows
    revenue = filtered["quantity"].values * filtered["price"].values

    # METHOD CHAINING: Clean, Pythonic aggregation (Mind MCP best practice)
    result = (
        filtered
        .assign(revenue=revenue)
        .groupby("product_id", as_index=False, observed=True)
        ["revenue"]
        .sum()
        .rename(columns={"revenue": "total_revenue"})
        .nlargest(top_n, "total_revenue")
        .reset_index(drop=True)
    )

    return result


def generate_sample_data(n_rows: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Generate sample sales data for testing."""
    np.random.seed(seed)

    products = [f"PROD_{i:03d}" for i in range(1, 51)]
    regions = ["North", "South", "East", "West"]

    dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_rows)

    return pd.DataFrame({
        "date": dates,
        "product_id": np.random.choice(products, n_rows),
        "quantity": np.random.randint(1, 100, n_rows),
        "price": np.random.uniform(10, 500, n_rows).round(2),
        "region": np.random.choice(regions, n_rows),
    })


if __name__ == "__main__":
    import time

    print("DS_001 Solution with Mind MCP Context")
    print("=" * 50)

    # Create test data
    test_path = Path("/tmp/test_sales_large.csv")
    sample_df = generate_sample_data(10000)
    sample_df.to_csv(test_path, index=False)

    # Benchmark
    start = time.perf_counter()
    result = load_and_process_sales(test_path, optimize_memory=True)
    elapsed = time.perf_counter() - start

    print(f"\nTop 5 Products by Revenue (North, 2024):")
    print(result)
    print(f"\nProcessed 10,000 rows in {elapsed*1000:.2f}ms")
    print(f"Memory optimization: enabled")

    # Verify with small sample
    print("\n" + "=" * 50)
    print("Verification with known data:")

    small_data = """date,product_id,quantity,price,region
2024-01-15,PROD_001,10,50.00,North
2024-02-20,PROD_042,100,1250.00,North
2024-03-10,PROD_001,15,50.00,North
"""
    small_path = Path("/tmp/test_small.csv")
    small_path.write_text(small_data)

    result_small = load_and_process_sales(small_path)
    print(result_small)
    assert result_small.iloc[0]["product_id"] == "PROD_042", "Top product should be PROD_042"
    print("\nVerification PASSED!")
