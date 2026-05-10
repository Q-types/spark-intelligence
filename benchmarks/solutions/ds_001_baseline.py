"""
Benchmark Solution: DS_001 - Pandas Data Manipulation
Configuration: BASELINE (Claude Code only)

Problem: Filter North region 2024 sales, group by product, return top 5 by revenue
"""

import pandas as pd
from typing import Optional
from pathlib import Path


def load_and_process_sales(
    csv_path: str,
    region: str = "North",
    year: int = 2024,
    top_n: int = 5
) -> pd.DataFrame:
    """
    Load sales data and return top products by revenue for a specific region and year.

    Args:
        csv_path: Path to the CSV file with sales data
        region: Region to filter (default: "North")
        year: Year to filter (default: 2024)
        top_n: Number of top products to return (default: 5)

    Returns:
        DataFrame with columns [product_id, total_revenue] sorted descending

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If required columns are missing
    """
    # Load data
    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = {"date", "product_id", "quantity", "price", "region"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # Parse dates and extract year
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # Filter by region and year
    filtered = df[(df["region"] == region) & (df["year"] == year)]

    if filtered.empty:
        return pd.DataFrame(columns=["product_id", "total_revenue"])

    # Calculate revenue
    filtered = filtered.copy()
    filtered["revenue"] = filtered["quantity"] * filtered["price"]

    # Group by product and sum revenue
    grouped = (
        filtered
        .groupby("product_id", as_index=False)
        .agg(total_revenue=("revenue", "sum"))
    )

    # Sort and return top N
    result = (
        grouped
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return result


# Test with sample data
if __name__ == "__main__":
    # Create sample test data
    import io

    sample_data = """date,product_id,quantity,price,region
2024-01-15,PROD_001,10,50.00,North
2024-02-20,PROD_002,5,100.00,North
2024-03-10,PROD_001,15,50.00,North
2024-04-05,PROD_003,20,25.00,South
2024-05-15,PROD_002,8,100.00,North
2024-06-20,PROD_042,100,1250.00,North
2024-07-10,PROD_004,30,40.00,North
2024-08-05,PROD_042,5,1250.00,North
2024-09-15,PROD_001,20,50.00,East
2024-10-20,PROD_005,12,80.00,North
2023-11-10,PROD_001,100,50.00,North
"""

    # Save to temp file and process
    test_path = Path("/tmp/test_sales.csv")
    test_path.write_text(sample_data)

    result = load_and_process_sales(str(test_path))
    print("Top 5 Products by Revenue (North, 2024):")
    print(result)
    print(f"\nTop product: {result.iloc[0]['product_id']}")
    print(f"Top revenue: ${result.iloc[0]['total_revenue']:,.2f}")
