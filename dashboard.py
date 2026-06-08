"""
dashboard.py
------------
Streamlit dashboard for the AI SQL Query Assistant.
Run with: streamlit run dashboard.py
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="AI SQL Query Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  [data-testid="stSidebar"]          { background: #161b22; border-right: 1px solid #21262d; }
  .stTextArea textarea {
    background: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #21262d !important; font-family: monospace;
    font-size: 15px !important;
  }
  .sql-box {
    background: #161b22; border: 1px solid #21262d; border-left: 3px solid #7c6af7;
    border-radius: 4px; padding: 14px 18px; font-family: monospace;
    font-size: 13px; color: #c9d1d9; line-height: 1.6; white-space: pre-wrap;
    margin: 10px 0;
  }
  .insight-box {
    background: #161b22; border-left: 3px solid #00d4aa;
    border-radius: 4px; padding: 14px 18px;
    font-size: 14px; color: #c9d1d9; line-height: 1.7; margin: 10px 0;
  }
  .followup-btn {
    background: #161b22; border: 1px solid #21262d; border-radius: 4px;
    padding: 8px 14px; color: #7d8590; font-size: 12px; cursor: pointer;
    margin: 4px; font-family: monospace;
  }
  .kpi-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 8px;
    padding: 20px; text-align: center;
  }
  .kpi-val   { font-size: 2rem; font-weight: 800; color: #00d4aa; font-family: monospace; }
  .kpi-label { font-size: 0.7rem; color: #7d8590; letter-spacing: 1px; text-transform: uppercase; }
  h1, h2, h3 { color: #e6edf3 !important; }
  .history-item {
    background: #161b22; border: 1px solid #21262d; border-radius: 4px;
    padding: 10px 14px; margin: 4px 0; cursor: pointer;
    font-family: monospace; font-size: 12px; color: #7d8590;
  }
</style>
""", unsafe_allow_html=True)

BG      = "#0d1117"
SURFACE = "#161b22"
BORDER  = "#21262d"
ACCENT  = "#00d4aa"
PURPLE  = "#7c6af7"
ORANGE  = "#f7a74a"
RED     = "#ff6b6b"
TEXT    = "#e6edf3"
MUTED   = "#7d8590"

CHART_COLORS = [ACCENT, PURPLE, ORANGE, RED, "#febc2e", "#28c840"]


# ── Init DB & session state ───────────────────────────────────────────────────
@st.cache_resource
def init_db():
    from database import build, DB_PATH
    if not os.path.exists(DB_PATH):
        build()
    return DB_PATH

db_path = init_db()

if "history"   not in st.session_state: st.session_state.history   = []
if "current_q" not in st.session_state: st.session_state.current_q = ""


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI SQL Assistant")
    st.markdown("*Ask questions in plain English*")
    st.divider()

    # DB stats
    from schema_reader import get_quick_stats
    stats = get_quick_stats(db_path)
    st.markdown("**Database Overview**")
    cols = st.columns(2)
    cols[0].metric("Customers", f"{stats.get('customers',0):,}")
    cols[1].metric("Orders",    f"{stats.get('orders',0):,}")
    cols[0].metric("Products",  f"{stats.get('products',0):,}")
    cols[1].metric("Revenue",   f"${stats.get('total_revenue',0)/1e6:.1f}M")

    st.divider()
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if has_key:
        st.success("AI Mode — Claude API active")
    else:
        st.warning("Demo Mode — Set ANTHROPIC_API_KEY for full AI")

    st.divider()
    st.markdown("**Query History**")
    if st.session_state.history:
        for i, h in enumerate(reversed(st.session_state.history[-8:])):
            if st.button(f"↩ {h['question'][:40]}...",
                         key=f"hist_{i}", use_container_width=True):
                st.session_state.current_q = h["question"]
    else:
        st.markdown("<span style='color:#7d8590;font-size:12px'>No queries yet</span>",
                    unsafe_allow_html=True)

    st.divider()
    st.markdown("*Built by [Darsh Jogani](https://www.linkedin.com/in/darsh-jogani-37b97218b)*")


# ── Main ─────────────────────────────────────────────────────────────────────
st.markdown("# AI-Powered SQL Query Assistant")
st.markdown("*Type a question in plain English — get SQL, results, and AI insights instantly*")
st.divider()

# ── Sample questions ──────────────────────────────────────────────────────────
from nl_to_sql import SAMPLE_QUESTIONS
st.markdown("**Try a sample question:**")
sample_cols = st.columns(3)
for i, q in enumerate(SAMPLE_QUESTIONS[:6]):
    if sample_cols[i % 3].button(q, key=f"sample_{i}", use_container_width=True):
        st.session_state.current_q = q

st.markdown("<br>", unsafe_allow_html=True)

# ── Query input ───────────────────────────────────────────────────────────────
question = st.text_area(
    "Your question:",
    value=st.session_state.current_q,
    height=80,
    placeholder="e.g. Show me the top 10 customers by total revenue this year",
    label_visibility="collapsed",
)

run_col, clr_col, schema_col = st.columns([2, 1, 1])
run_btn    = run_col.button("Run Query →", type="primary", use_container_width=True)
clear_btn  = clr_col.button("Clear", use_container_width=True)
schema_btn = schema_col.button("View Schema", use_container_width=True)

if clear_btn:
    st.session_state.current_q = ""
    st.rerun()

if schema_btn:
    from schema_reader import get_schema_context
    with st.expander("Database Schema", expanded=True):
        st.code(get_schema_context(db_path), language="sql")

# ── Execute ───────────────────────────────────────────────────────────────────
if run_btn and question.strip():
    with st.spinner("Generating SQL..."):
        if has_key:
            from nl_to_sql import natural_language_to_sql, explain_question
            history_ctx = st.session_state.history[-4:]
            sql = natural_language_to_sql(question, db_path, history_ctx)
            understood = explain_question(question)
        else:
            # Demo mode fallback
            sql = """SELECT customer_name, segment, region_name,
       ROUND(SUM(revenue),2) AS total_revenue, COUNT(*) AS orders
FROM v_order_revenue
GROUP BY customer_id, customer_name, segment, region_name
ORDER BY total_revenue DESC LIMIT 10"""
            understood = "This query retrieves the top 10 customers ranked by total completed revenue."

    # Show what AI understood
    st.markdown(f"<div class='insight-box'>🧠 <strong>Understood:</strong> {understood}</div>",
                unsafe_allow_html=True)

    # Show SQL
    st.markdown("**Generated SQL:**")
    st.markdown(f"<div class='sql-box'>{sql}</div>", unsafe_allow_html=True)

    # Execute
    with st.spinner("Running query..."):
        from query_engine import execute_query
        result = execute_query(sql, db_path)

    if not result.success:
        st.error(f"Query Error: {result.error}")
    else:
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"""<div class='kpi-card'>
            <div class='kpi-val'>{result.row_count:,}</div>
            <div class='kpi-label'>Rows Returned</div></div>""", unsafe_allow_html=True)
        m2.markdown(f"""<div class='kpi-card'>
            <div class='kpi-val'>{result.col_count}</div>
            <div class='kpi-label'>Columns</div></div>""", unsafe_allow_html=True)
        m3.markdown(f"""<div class='kpi-card'>
            <div class='kpi-val'>{result.execution_time:.3f}s</div>
            <div class='kpi-label'>Execution Time</div></div>""", unsafe_allow_html=True)
        m4.markdown(f"""<div class='kpi-card'>
            <div class='kpi-val'>{result.chart_suggestion or 'table'}</div>
            <div class='kpi-label'>Chart Type</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Chart + Table tabs
        chart_tab, table_tab, raw_tab = st.tabs(["📊 Chart", "📋 Results Table", "🔍 Raw SQL"])

        with chart_tab:
            df = result.df
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            str_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
            chart_type = result.chart_suggestion

            if chart_type == "kpi" and len(df) == 1 and len(df.columns) == 1:
                val = df.iloc[0, 0]
                st.markdown(f"""<div style='text-align:center;padding:40px'>
                    <div style='font-size:4rem;font-weight:800;color:{ACCENT};font-family:monospace'>{val:,.2f}</div>
                    <div style='color:{MUTED};font-size:1rem'>{df.columns[0]}</div>
                </div>""", unsafe_allow_html=True)

            elif chart_type == "line" and num_cols:
                time_col = str_cols[0] if str_cols else df.columns[0]
                fig = px.line(df, x=time_col, y=num_cols,
                              template="plotly_dark",
                              color_discrete_sequence=CHART_COLORS)
                fig.update_layout(paper_bgcolor=BG, plot_bgcolor=SURFACE,
                                  font_color=MUTED, margin=dict(t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)

            elif chart_type in ("bar", "bar_h") and num_cols and str_cols:
                x_col = str_cols[0]
                y_col = num_cols[0]
                if chart_type == "bar_h":
                    fig = px.bar(df, x=y_col, y=x_col, orientation="h",
                                 color=y_col, template="plotly_dark",
                                 color_continuous_scale=[[0, PURPLE], [1, ACCENT]])
                else:
                    fig = px.bar(df, x=x_col, y=y_col, template="plotly_dark",
                                 color_discrete_sequence=[ACCENT])
                fig.update_layout(paper_bgcolor=BG, plot_bgcolor=SURFACE,
                                  font_color=MUTED, showlegend=False,
                                  margin=dict(t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)

            else:
                if num_cols and str_cols:
                    fig = px.bar(df.head(25), x=str_cols[0], y=num_cols[0],
                                 template="plotly_dark",
                                 color_discrete_sequence=[ACCENT])
                    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=SURFACE,
                                      font_color=MUTED, margin=dict(t=20, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No suitable chart available for this result shape.")

        with table_tab:
            st.dataframe(result.to_display(), use_container_width=True, height=400)

        with raw_tab:
            st.code(sql, language="sql")

        # AI Interpretation
        if has_key:
            st.markdown("---")
            st.markdown("### AI Interpretation")
            with st.spinner("Generating insight..."):
                from result_interpreter import interpret_results, suggest_followups
                interpretation = interpret_results(question, sql, result.df)
                followups      = suggest_followups(question, result.df)

            st.markdown(f"<div class='insight-box'>{interpretation}</div>",
                        unsafe_allow_html=True)

            if followups:
                st.markdown("**Follow-up questions you might ask:**")
                fq_cols = st.columns(len(followups))
                for i, fq in enumerate(followups):
                    if fq_cols[i].button(f"→ {fq}", key=f"fq_{i}", use_container_width=True):
                        st.session_state.current_q = fq
                        st.rerun()

        # Save to history
        st.session_state.history.append({
            "question": question,
            "sql"     : sql,
            "rows"    : result.row_count,
        })
        st.session_state.current_q = ""

elif run_btn:
    st.warning("Please enter a question first.")
