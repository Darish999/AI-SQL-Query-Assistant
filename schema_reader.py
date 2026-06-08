"""
schema_reader.py
----------------
Extracts database schema and sample data to build rich context
for the LLM — enabling accurate SQL generation.
"""

import sqlite3
import pandas as pd
from database import DB_PATH


def get_schema_context(db_path: str = DB_PATH) -> str:
    """
    Builds a detailed schema description string for the LLM.
    Includes table definitions, column types, foreign keys,
    sample rows, and available views.
    """
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables and views
    cursor.execute("""
        SELECT name, type FROM sqlite_master
        WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
        ORDER BY type DESC, name
    """)
    objects = cursor.fetchall()

    parts = ["=== DATABASE SCHEMA ===\n"]

    for name, obj_type in objects:
        parts.append(f"\n{'TABLE' if obj_type=='table' else 'VIEW'}: {name}")
        parts.append("-" * 40)

        # Column info
        cursor.execute(f"PRAGMA table_info({name})")
        cols = cursor.fetchall()
        for col in cols:
            cid, cname, ctype, notnull, default, pk = col
            pk_str  = " [PRIMARY KEY]" if pk else ""
            nn_str  = " NOT NULL" if notnull else ""
            def_str = f" DEFAULT {default}" if default else ""
            parts.append(f"  {cname:25s} {ctype:10s}{pk_str}{nn_str}{def_str}")

        # Foreign keys (tables only)
        if obj_type == "table":
            cursor.execute(f"PRAGMA foreign_key_list({name})")
            fks = cursor.fetchall()
            if fks:
                parts.append("  Foreign Keys:")
                for fk in fks:
                    parts.append(f"    {fk[3]} → {fk[2]}.{fk[4]}")

        # Sample rows
        try:
            cursor.execute(f"SELECT * FROM {name} LIMIT 3")
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]
            if rows:
                parts.append(f"  Sample rows (first 3):")
                parts.append(f"  {' | '.join(col_names)}")
                for row in rows:
                    parts.append(f"  {' | '.join(str(v) for v in row)}")
        except Exception:
            pass

        # Row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {name}")
            count = cursor.fetchone()[0]
            parts.append(f"  Total rows: {count:,}")
        except Exception:
            pass

    conn.close()
    return "\n".join(parts)


def get_table_names(db_path: str = DB_PATH) -> list[str]:
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
    """)
    names = [r[0] for r in cursor.fetchall()]
    conn.close()
    return names


def get_column_names(table: str, db_path: str = DB_PATH) -> list[str]:
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]
    conn.close()
    return cols


def get_quick_stats(db_path: str = DB_PATH) -> dict:
    """High-level database stats for the dashboard sidebar."""
    conn = sqlite3.connect(db_path)
    stats = {}
    for table in ["customers", "orders", "products", "order_items"]:
        try:
            stats[table] = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn)["n"][0]
        except Exception:
            stats[table] = 0
    try:
        stats["total_revenue"] = pd.read_sql(
            "SELECT ROUND(SUM(revenue),2) as r FROM v_order_revenue", conn
        )["r"][0]
    except Exception:
        stats["total_revenue"] = 0
    conn.close()
    return stats


if __name__ == "__main__":
    from database import build
    build()
    print(get_schema_context())
    print("\nQuick stats:", get_quick_stats())
