"""
nl_to_sql.py
------------
Converts natural language questions to SQL using the Claude API.
Uses schema context for accurate, safe query generation.
"""

import os
import re
import anthropic
from schema_reader import get_schema_context
from database import DB_PATH

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
MODEL  = "claude-sonnet-4-20250514"

# Cache schema so we don't re-read on every query
_SCHEMA_CACHE: dict[str, str] = {}


def get_cached_schema(db_path: str = DB_PATH) -> str:
    if db_path not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[db_path] = get_schema_context(db_path)
    return _SCHEMA_CACHE[db_path]


SYSTEM_PROMPT = """You are an expert SQL analyst. Your job is to convert natural language questions into accurate SQLite SQL queries.

Rules:
1. Return ONLY the SQL query — no explanation, no markdown, no backticks, no preamble.
2. Use only tables and columns that exist in the schema provided.
3. Always use table aliases for clarity.
4. For revenue calculations use: quantity * unit_price * (1 - discount_pct)
5. Prefer views (v_order_revenue, v_customer_summary) when they simplify the query.
6. Always add LIMIT 100 unless the user asks for all data or an aggregation.
7. Use strftime('%Y-%m', order_date) for monthly grouping.
8. Use strftime('%Y', order_date) for yearly grouping.
9. "Last quarter" = last 90 days. "This year" = current year. "Last year" = previous year.
10. For rankings use ROW_NUMBER() or ORDER BY + LIMIT.
11. Never use DROP, DELETE, UPDATE, INSERT, or any DDL/DML — SELECT only.
12. If the question is unanswerable from the schema, return: SELECT 'Cannot answer: [reason]' AS error;
"""


def natural_language_to_sql(question: str, db_path: str = DB_PATH,
                              conversation_history: list = None) -> str:
    """
    Convert a natural language question to a SQL query.

    Args:
        question: Plain English question about the data
        db_path: Path to SQLite database
        conversation_history: Previous Q&A pairs for multi-turn context

    Returns:
        SQL query string
    """
    schema = get_cached_schema(db_path)

    # Build messages
    messages = []

    # Add conversation history for context
    if conversation_history:
        for turn in conversation_history[-4:]:  # last 4 turns for context
            messages.append({"role": "user",      "content": turn["question"]})
            messages.append({"role": "assistant", "content": turn["sql"]})

    # Current question
    messages.append({
        "role": "user",
        "content": f"""Database Schema:
{schema}

Question: {question}

Return only the SQL query."""
    })

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    sql = response.content[0].text.strip()

    # Clean up any accidental markdown
    sql = re.sub(r"```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```\s*",    "", sql)
    sql = sql.strip()

    return sql


def validate_sql(sql: str) -> tuple[bool, str]:
    """Basic safety validation — ensure read-only."""
    sql_upper = sql.upper()
    forbidden = ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ",
                 "CREATE ", "TRUNCATE ", "REPLACE ", "ATTACH "]
    for kw in forbidden:
        if kw in sql_upper:
            return False, f"Query contains forbidden keyword: {kw.strip()}"
    return True, "OK"


def explain_question(question: str) -> str:
    """
    Ask Claude to rephrase/clarify what data the question is asking for.
    Useful for the UI to show users what it understood.
    """
    response = client.messages.create(
        model=MODEL,
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": (
                f"In one sentence, what data is this question asking for: '{question}'? "
                "Be direct and specific. Start with 'This query retrieves...'"
            )
        }]
    )
    return response.content[0].text.strip()


# ── Suggested Questions ───────────────────────────────────────────────────────
SAMPLE_QUESTIONS = [
    "Show me the top 10 customers by total revenue",
    "What are total sales by region this year?",
    "Which products generate the most gross profit?",
    "Show monthly revenue trend for the last 12 months",
    "Which sales rep has the highest conversion rate?",
    "What is the average order value by customer segment?",
    "Show me all orders from Enterprise customers in the last 90 days",
    "Which customers haven't placed an order in over 6 months?",
    "What percentage of orders were cancelled by region?",
    "Show the top 5 products by units sold last quarter",
    "What is the revenue breakdown by payment method?",
    "Which customers have the highest lifetime value?",
    "Show me month-over-month revenue growth",
    "What is the gross margin percentage by product category?",
    "Which sales rep exceeded their quota this year?",
]


if __name__ == "__main__":
    from database import build
    build()

    questions = [
        "Show me the top 5 customers by revenue",
        "What is the monthly revenue trend for the last 6 months?",
        "Which product category has the highest gross margin?",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        sql = natural_language_to_sql(q)
        print(f"SQL:\n{sql}")
