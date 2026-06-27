import re
import os
import json
import sqlite3
import pandas as pd
import requests


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


def _call_groq(system: str, user: str, max_tokens: int = 500, temperature: float = 0) -> str:
    """Core Groq API call. Returns content string or raises."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env file.")

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

    choices = response.json().get("choices", [])
    if not choices:
        raise RuntimeError("Groq returned empty choices")

    return choices[0].get("message", {}).get("content", "").strip()


def generate_sql(natural_language: str, schema: str, table_name: str):
    """Convert NL to SQL. Returns (sql, error) tuple — never None."""
    system = f"""You are an expert SQLite SQL query generator.

DATABASE SCHEMA (use ONLY these exact column names):
{schema}

PRIMARY TABLE: {table_name}

STRICT RULES:
1. Use ONLY column names from the schema above — never invent columns
2. Use exact table name: {table_name}
3. For window functions (SUM OVER, LAG, RANK) — use real column names only
4. Output ONLY raw SQLite SQL — no markdown, no backticks, no explanation
5. Add LIMIT 100 unless the query is an aggregation
6. If a column does not exist, use the closest matching real column
7. For text filters use LIKE with % wildcards

Check every column name against the schema before writing SQL."""

    try:
        sql = _call_groq(system, f"Convert to SQL: {natural_language}")
        sql = re.sub(r"```sql\n?", "", sql)
        sql = re.sub(r"```\n?", "", sql)
        return sql.strip(), None
    except Exception as e:
        return None, str(e)


def explain_query(sql: str, results_summary: str, question: str) -> str:
    """Plain English explanation of what the query found."""
    system = "You are a concise data analyst. Explain SQL query results in 2-3 plain English sentences focused on the business insight. No technical jargon."
    user = f"Question: {question}\nSQL: {sql}\nResult: {results_summary}\n\nExplain the key insight in 2-3 sentences."
    try:
        return _call_groq(system, user, max_tokens=200, temperature=0.3)
    except Exception:
        return ""


def suggest_followups(question: str, schema: str, table_name: str) -> list:
    """Generate 3 follow-up question suggestions as a list."""
    system = 'You are a data analyst. Suggest 3 short follow-up questions the user might ask next. Return ONLY a JSON array of 3 strings. Example: ["question 1", "question 2", "question 3"]'
    user = f"Original question: {question}\nTable: {table_name}\nReturn 3 follow-up questions as a JSON array:"
    try:
        content = _call_groq(system, user, max_tokens=150, temperature=0.5)
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []
    except Exception:
        return []


def execute_query(db_path: str, sql: str):
    """Execute SQL on SQLite. Returns (dataframe, error) — never None."""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql, conn)
        conn.close()
        return df, None
    except Exception as e:
        return None, str(e)
