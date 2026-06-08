"""
result_interpreter.py
---------------------
Uses Claude to generate plain-English interpretations of SQL query results.
Provides business narrative, key findings, and follow-up question suggestions.
"""

import os
import json
import anthropic
import pandas as pd

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
MODEL  = "claude-sonnet-4-20250514"


def interpret_results(question: str, sql: str, df: pd.DataFrame,
                       max_rows_to_show: int = 20) -> str:
    """
    Generate a business-friendly interpretation of query results.

    Args:
        question : Original natural language question
        sql      : The SQL that was executed
        df       : Result DataFrame
        max_rows_to_show: How many rows to include in context

    Returns:
        Plain English interpretation string
    """
    if df is None or df.empty:
        return "The query returned no results. This may mean no data matches the criteria."

    # Summarize data for the LLM
    sample   = df.head(max_rows_to_show).to_string(index=False)
    n_rows   = len(df)
    col_info = {col: str(df[col].dtype) for col in df.columns}

    # Compute basic stats for numeric columns
    numeric_stats = {}
    for col in df.select_dtypes(include="number").columns:
        numeric_stats[col] = {
            "min"  : round(float(df[col].min()), 2),
            "max"  : round(float(df[col].max()), 2),
            "mean" : round(float(df[col].mean()), 2),
            "sum"  : round(float(df[col].sum()), 2),
        }

    prompt = f"""You are a senior business analyst presenting data insights to a non-technical executive.

Original question: "{question}"

Query results ({n_rows} total rows):
{sample}

{"..." if n_rows > max_rows_to_show else ""}

Numeric column statistics:
{json.dumps(numeric_stats, indent=2)}

Write a concise business interpretation (3–5 sentences) that:
1. Directly answers the question with specific numbers
2. Highlights the most important finding or trend
3. Notes any anomaly or insight worth flagging
4. Uses plain business language, not technical SQL terms

Be direct and specific. Lead with the headline number or finding."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def suggest_followups(question: str, df: pd.DataFrame) -> list[str]:
    """
    Suggest 3 logical follow-up questions based on the current result.
    """
    if df is None or df.empty:
        return []

    cols_str = ", ".join(df.columns.tolist()[:10])

    prompt = f"""Based on this data analysis question: "{question}"
And the result columns: {cols_str}

Suggest exactly 3 concise follow-up questions a business analyst might ask next.
Return only the 3 questions, one per line, no numbering, no explanation."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    lines = [l.strip() for l in response.content[0].text.strip().split("\n")
             if l.strip() and not l.strip()[0].isdigit()]
    return lines[:3]


def generate_query_title(question: str) -> str:
    """Generate a short title for a query in history."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"Give a 3–5 word title for this data question: '{question}'. Return only the title."
        }]
    )
    return response.content[0].text.strip().strip('"\'')


if __name__ == "__main__":
    from database import build
    from query_engine import execute_query

    build()

    q   = "Show me the top 5 customers by revenue"
    sql = """
        SELECT customer_name, segment, ROUND(SUM(revenue),2) AS total_revenue, COUNT(*) AS orders
        FROM v_order_revenue
        GROUP BY customer_id, customer_name, segment
        ORDER BY total_revenue DESC LIMIT 5
    """
    res = execute_query(sql)

    if res.success:
        print("── Interpretation ──")
        print(interpret_results(q, sql, res.df))
        print("\n── Follow-up Questions ──")
        for fq in suggest_followups(q, res.df):
            print(f"  • {fq}")
