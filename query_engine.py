"""
query_engine.py
---------------
Safe SQL execution engine with error handling, timeout protection,
result formatting, and automatic chart-type detection.
"""

import sqlite3
import pandas as pd
import time
from database import DB_PATH
from nl_to_sql import validate_sql

MAX_ROWS    = 500
MAX_TIMEOUT = 10  # seconds


class QueryResult:
    """Structured result from query execution."""

    def __init__(self, sql: str, df: pd.DataFrame = None,
                 error: str = None, execution_time: float = 0):
        self.sql            = sql
        self.df             = df
        self.error          = error
        self.execution_time = execution_time
        self.row_count      = len(df) if df is not None else 0
        self.col_count      = len(df.columns) if df is not None else 0
        self.success        = error is None and df is not None

    @property
    def chart_suggestion(self) -> str | None:
        """Suggest a chart type based on the result shape."""
        if self.df is None or self.df.empty:
            return None

        cols      = list(self.df.columns)
        n_cols    = len(cols)
        n_rows    = len(self.df)
        col_lower = [c.lower() for c in cols]

        num_cols = [c for c in self.df.columns
                    if pd.api.types.is_numeric_dtype(self.df[c])]
        str_cols = [c for c in self.df.columns
                    if not pd.api.types.is_numeric_dtype(self.df[c])]

        # Time series
        time_keywords = ["month", "year", "date", "week", "quarter", "period"]
        if any(kw in " ".join(col_lower) for kw in time_keywords) and num_cols:
            return "line"

        # Rankings / top N
        if n_rows <= 15 and len(num_cols) == 1 and len(str_cols) == 1:
            return "bar_h"

        # Single numeric — KPI
        if n_cols == 1 and n_rows == 1:
            return "kpi"

        # Multi-numeric comparison
        if len(str_cols) == 1 and len(num_cols) >= 1 and n_rows <= 20:
            return "bar"

        # Distribution
        if n_cols == 2 and len(num_cols) == 1 and n_rows > 20:
            return "scatter"

        return "table"

    def to_display(self, max_rows: int = 100) -> pd.DataFrame:
        """Return display-ready DataFrame."""
        if self.df is None:
            return pd.DataFrame()
        df = self.df.head(max_rows).copy()
        # Format float columns
        for col in df.select_dtypes(include="float").columns:
            if any(kw in col.lower() for kw in ["revenue", "price", "cost",
                                                  "profit", "value", "amount"]):
                df[col] = df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
            elif any(kw in col.lower() for kw in ["pct", "percent", "rate", "margin"]):
                df[col] = df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            else:
                df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
        return df


def execute_query(sql: str, db_path: str = DB_PATH) -> QueryResult:
    """
    Execute a SQL query safely and return a QueryResult.
    Enforces read-only, row limits, and timeout.
    """
    # Validate
    valid, msg = validate_sql(sql)
    if not valid:
        return QueryResult(sql=sql, error=f"Security validation failed: {msg}")

    start = time.time()
    try:
        conn = sqlite3.connect(db_path, timeout=MAX_TIMEOUT)
        conn.execute("PRAGMA query_only = ON")

        df = pd.read_sql_query(sql, conn)
        elapsed = round(time.time() - start, 4)
        conn.close()

        if len(df) > MAX_ROWS:
            df = df.head(MAX_ROWS)

        return QueryResult(sql=sql, df=df, execution_time=elapsed)

    except sqlite3.OperationalError as e:
        return QueryResult(sql=sql, error=f"SQL Error: {str(e)}")
    except pd.errors.DatabaseError as e:
        return QueryResult(sql=sql, error=f"Database Error: {str(e)}")
    except Exception as e:
        return QueryResult(sql=sql, error=f"Unexpected Error: {str(e)}")


def run_example_queries(db_path: str = DB_PATH) -> dict[str, QueryResult]:
    """Run a set of example queries and return results."""
    examples = {
        "Top 10 Customers by Revenue": """
            SELECT customer_name, segment, region_name,
                   ROUND(SUM(revenue), 2) AS total_revenue,
                   COUNT(*) AS orders
            FROM v_order_revenue
            GROUP BY customer_id, customer_name, segment, region_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """,
        "Monthly Revenue Trend": """
            SELECT strftime('%Y-%m', order_date) AS month,
                   ROUND(SUM(revenue), 2)         AS revenue,
                   COUNT(*)                        AS orders
            FROM v_order_revenue
            GROUP BY month
            ORDER BY month
        """,
        "Revenue by Segment": """
            SELECT segment,
                   ROUND(SUM(revenue), 2)        AS revenue,
                   COUNT(DISTINCT customer_id)   AS customers,
                   COUNT(*)                       AS orders
            FROM v_order_revenue
            GROUP BY segment
            ORDER BY revenue DESC
        """,
    }
    return {name: execute_query(sql.strip(), db_path)
            for name, sql in examples.items()}


if __name__ == "__main__":
    from database import build
    build()

    results = run_example_queries()
    for name, res in results.items():
        print(f"\n── {name} ──")
        if res.success:
            print(f"Rows: {res.row_count} | Time: {res.execution_time}s")
            print(f"Chart: {res.chart_suggestion}")
            print(res.df.head(5).to_string(index=False))
        else:
            print(f"Error: {res.error}")
