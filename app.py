from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
import json
from utils.nl_to_sql import generate_sql, execute_query, explain_query, suggest_followups
from utils.schema_extractor import extract_schema, get_table_names

st.set_page_config(page_title="AI SQL Assistant", page_icon="", layout="wide")

# ── Styling ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .hero {
        background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
        border: 1px solid #2d3561;
        border-radius: 12px;
        padding: 1.75rem 2.5rem;
        margin-bottom: 1.5rem;
    }
    .hero h1 { font-size: 1.85rem; font-weight: 600; color: #e2e8f0; margin: 0 0 0.4rem; }
    .hero p { color: #94a3b8; margin: 0; font-size: 0.9rem; }
    .hero span { color: #6366f1; font-weight: 600; }
    .schema-box {
        background: #1e2130; border: 1px solid #2d3561; border-radius: 8px;
        padding: 1rem 1.25rem; font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem; color: #94a3b8; max-height: 280px; overflow-y: auto;
    }
    .step-label {
        font-size: 0.9rem; font-weight: 600; color: #6366f1;
        text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem;
    }
    .explain-box {
        background: #1a2e1a; border: 1px solid #166534; border-left: 3px solid #22c55e;
        border-radius: 8px; padding: 0.9rem 1.25rem; color: #86efac;
        font-size: 0.9rem; line-height: 1.6; margin: 0.75rem 0;
    }
    .followup-btn {
        background: #1e2130 !important; border: 1px solid #2d3561 !important;
        color: #94a3b8 !important; border-radius: 8px !important;
        font-size: 0.82rem !important; padding: 0.4rem 0.9rem !important;
        margin: 3px !important; cursor: pointer !important;
    }
    .chart-section {
        background: #1e2130; border: 1px solid #2d3561;
        border-radius: 8px; padding: 1rem; margin-top: 0.75rem;
    }
    .success-badge {
        display: inline-block; background: #064e3b; color: #6ee7b7;
        padding: 2px 10px; border-radius: 99px; font-size: 0.75rem;
        font-weight: 500; margin-bottom: 0.75rem;
    }
    .error-badge {
        display: inline-block; background: #450a0a; color: #fca5a5;
        padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 500;
    }
    .stButton > button {
        background: #6366f1 !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        font-weight: 500 !important; font-size: 0.9rem !important;
    }
    .stButton > button:hover { background: #4f46e5 !important; }
    .stTextArea textarea {
        font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important;
        background: #1e2130 !important; border: 1px solid #2d3561 !important;
        color: #e2e8f0 !important; border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ──
for key, default in [
    ("db_path", None), ("schema", None), ("history", []),
    ("tables", []), ("last_results", None), ("last_sql", None),
    ("last_question", None), ("followups", [])
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Hero ──
st.markdown("""
<div class="hero">
    <h1>AI SQL Query Assistant</h1>
    <p>Upload any CSV, ask questions in plain English — get <span>SQL + results + insights</span> instantly.</p>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 2], gap="large")

# ─────────────────────────────────────
# LEFT — Upload + Multi-table + Schema
# ─────────────────────────────────────
with left:
    st.markdown('<div class="step-label">Step 1 — Upload CSV Files</div>', unsafe_allow_html=True)
    st.caption("Upload one or more CSV files — each becomes a table you can query and JOIN across.")

    uploaded_files = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            conn = sqlite3.connect(tmp.name)
            loaded = []

            for f in uploaded_files:
                df = pd.read_csv(f)
                df.columns = (
                    df.columns.str.strip().str.replace(" ", "_")
                    .str.replace("/", "_").str.replace("-", "_").str.lower()
                )
                tname = f.name.replace(".csv", "").replace(" ", "_").lower()
                df.to_sql(tname, conn, if_exists="replace", index=False)
                loaded.append((tname, len(df), len(df.columns)))

            conn.close()
            st.session_state.db_path = tmp.name
            st.session_state.schema = extract_schema(tmp.name)
            st.session_state.tables = get_table_names(tmp.name)
            # Default table = first uploaded
            st.session_state.table_name = loaded[0][0]

            for tname, rows, cols in loaded:
                st.success(f"✓ `{tname}` — {rows:,} rows × {cols} cols")

        except Exception as e:
            st.error(f"Failed to load: {e}")

    # Table selector (if multiple)
    if len(st.session_state.tables) > 1:
        st.markdown('<div class="step-label" style="margin-top:1rem">Primary Table</div>', unsafe_allow_html=True)
        st.session_state.table_name = st.selectbox(
            "Default table for queries",
            st.session_state.tables,
            label_visibility="collapsed"
        )
        st.caption("You can also JOIN tables in your questions.")

    # Schema
    if st.session_state.schema:
        st.markdown('<div class="step-label" style="margin-top:1.25rem">Schema</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="schema-box">{st.session_state.schema}</div>', unsafe_allow_html=True)

        with st.expander("Preview first table (5 rows)"):
            try:
                conn = sqlite3.connect(st.session_state.db_path)
                preview = pd.read_sql(f"SELECT * FROM {st.session_state.table_name} LIMIT 5", conn)
                conn.close()
                st.dataframe(preview, use_container_width=True)
            except Exception:
                pass

# ─────────────────────────────────────
# RIGHT — Query Interface
# ─────────────────────────────────────
with right:
    st.markdown('<div class="step-label">Step 2 — Ask a Question</div>', unsafe_allow_html=True)

    examples = [
        "Show me the top 10 most expensive properties",
        "What is the average price by city?",
        "How many luxury properties are there in each zip code?",
        "Show year over year price trend",
        "Which areas have the highest school ratings?",
        "Show properties with more than 4 bedrooms under $600,000",
        "What percentage of homes are luxury properties?",
    ]

    selected = st.selectbox(
        "Try an example",
        ["— pick an example or type below —"] + examples,
        label_visibility="collapsed"
    )

    # Handle follow-up click via query param
    prefill = ""
    if selected != "— pick an example or type below —":
        prefill = selected
    if st.session_state.get("followup_clicked"):
        prefill = st.session_state.followup_clicked
        st.session_state.followup_clicked = None

    nl_query = st.text_area(
        "Your question",
        value=prefill,
        height=90,
        placeholder="e.g. What are the top 5 cities by average price per sqft?",
        label_visibility="collapsed"
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run = st.button("▶ Run Query", disabled=not st.session_state.db_path, use_container_width=True)
    with col_info:
        if not st.session_state.db_path:
            st.caption("⬅ Upload a CSV file first")
        else:
            st.caption(f"Querying `{st.session_state.get('table_name', '')}` via Ollama (llama3.2)")

    # ── Follow-up suggestions (shown before new query) ──
    if st.session_state.followups and not run:
        st.markdown('<div class="step-label" style="margin-top:0.5rem">You could also ask</div>', unsafe_allow_html=True)
        cols = st.columns(len(st.session_state.followups))
        for i, (col, q) in enumerate(zip(cols, st.session_state.followups)):
            with col:
                if st.button(f"💬 {q}", key=f"followup_{i}", use_container_width=True):
                    st.session_state.followup_clicked = q
                    st.rerun()

    # ── Main query execution ──
    if run and nl_query.strip():
        st.session_state.followups = []

        # 1. Generate SQL
        with st.spinner("Generating SQL..."):
            result = generate_sql(nl_query, st.session_state.schema, st.session_state.table_name)
            sql, gen_error = result if result else (None, "generate_sql returned None")

        if gen_error:
            st.markdown('<span class="error-badge">✗ Generation failed</span>', unsafe_allow_html=True)
            st.error(gen_error)
        else:
            st.markdown('<div class="step-label" style="margin-top:1rem">Generated SQL</div>', unsafe_allow_html=True)
            st.code(sql, language="sql")

            # 2. Execute
            with st.spinner("Running query..."):
                results, exec_error = execute_query(st.session_state.db_path, sql)

            # 3. Auto-fix if failed
            if exec_error:
                st.markdown('<span class="error-badge">✗ Execution failed</span>', unsafe_allow_html=True)
                st.error(exec_error)
                st.info("Auto-fixing query...")

                with st.spinner("Fixing..."):
                    fix_result = generate_sql(
                        f"{nl_query}\n\nPrevious SQL:\n{sql}\nFailed with: {exec_error}\nFix the SQL.",
                        st.session_state.schema,
                        st.session_state.table_name
                    )
                    fixed_sql, fix_err = fix_result if fix_result else (None, "Fix failed")

                if not fix_err:
                    results, exec_error2 = execute_query(st.session_state.db_path, fixed_sql)
                    if not exec_error2:
                        st.success("✓ Auto-fixed!")
                        st.code(fixed_sql, language="sql")
                        sql = fixed_sql
                        exec_error = None

            # 4. Show results
            if results is not None and not results.empty:
                st.markdown('<span class="success-badge">✓ Query successful</span>', unsafe_allow_html=True)
                st.dataframe(results, use_container_width=True)
                st.caption(f"{len(results):,} row(s) returned")

                st.session_state.last_results = results
                st.session_state.last_sql = sql
                st.session_state.last_question = nl_query

                # Download
                st.download_button(
                    "⬇ Download results as CSV",
                    results.to_csv(index=False),
                    file_name="query_results.csv",
                    mime="text/csv"
                )

                # ── 5. Auto Chart ──
                numeric_cols = results.select_dtypes(include="number").columns.tolist()
                text_cols = results.select_dtypes(include="object").columns.tolist()

                if numeric_cols:
                    st.markdown('<div class="step-label" style="margin-top:1.25rem">Auto Chart</div>', unsafe_allow_html=True)
                    with st.container():
                        chart_col1, chart_col2, chart_col3 = st.columns(3)
                        with chart_col1:
                            chart_type = st.selectbox("Chart type", ["Bar", "Line", "Area"], key="chart_type", label_visibility="collapsed")
                        with chart_col2:
                            x_col = st.selectbox("X axis", results.columns.tolist(), key="x_col", label_visibility="collapsed")
                        with chart_col3:
                            y_col = st.selectbox("Y axis", numeric_cols, key="y_col", label_visibility="collapsed")

                        chart_data = results[[x_col, y_col]].set_index(x_col)
                        if chart_type == "Bar":
                            st.bar_chart(chart_data, use_container_width=True)
                        elif chart_type == "Line":
                            st.line_chart(chart_data, use_container_width=True)
                        elif chart_type == "Area":
                            st.area_chart(chart_data, use_container_width=True)

                # ── 6. Explain query ──
                st.markdown('<div class="step-label" style="margin-top:1.25rem">What this means</div>', unsafe_allow_html=True)
                with st.spinner("Generating insight..."):
                    summary = f"{len(results)} rows returned. " + \
                              f"Columns: {', '.join(results.columns[:5].tolist())}. " + \
                              f"First row: {results.iloc[0].to_dict() if len(results) > 0 else 'empty'}"
                    explanation = explain_query(sql, summary, nl_query)

                if explanation:
                    st.markdown(f'<div class="explain-box">💡 {explanation}</div>', unsafe_allow_html=True)

                # ── 7. Follow-up suggestions ──
                with st.spinner("Generating follow-up questions..."):
                    followups = suggest_followups(nl_query, st.session_state.schema, st.session_state.table_name)
                st.session_state.followups = followups[:3]

                # Save history
                st.session_state.history.append({
                    "question": nl_query, "sql": sql, "rows": len(results)
                })

                if followups:
                    st.markdown('<div class="step-label" style="margin-top:1rem">You could also ask</div>', unsafe_allow_html=True)
                    cols = st.columns(len(followups))
                    for i, (col, q) in enumerate(zip(cols, followups)):
                        with col:
                            if st.button(f"💬 {q}", key=f"fu_{i}", use_container_width=True):
                                st.session_state.followup_clicked = q
                                st.rerun()

            elif results is not None and results.empty:
                st.info("Query ran successfully but returned no rows.")

    # ── Query History ──
    if st.session_state.history:
        st.markdown("---")
        st.markdown('<div class="step-label">Query History</div>', unsafe_allow_html=True)
        for h in reversed(st.session_state.history[-5:]):
            with st.expander(f"❓ {h['question'][:70]} → {h['rows']} rows"):
                st.code(h["sql"], language="sql")
