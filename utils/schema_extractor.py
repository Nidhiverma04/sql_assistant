import sqlite3


def extract_schema(db_path: str) -> str:
    """Extract rich schema string including sample values for prompt context."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    schema_lines = []

    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

        schema_lines.append(f"TABLE: {table_name} ({count:,} rows)")
        schema_lines.append("COLUMNS (name | type | sample values):")

        for col in columns:
            _, name, col_type, _, _, pk = col
            pk_marker = " [PK]" if pk else ""
            try:
                cursor.execute(
                    f'SELECT DISTINCT "{name}" FROM "{table_name}" '
                    f'WHERE "{name}" IS NOT NULL LIMIT 3'
                )
                samples = [str(r[0]) for r in cursor.fetchall()]
                sample_str = ", ".join(samples)
            except Exception:
                sample_str = "N/A"
            schema_lines.append(f"  {name} ({col_type}{pk_marker}) — e.g. {sample_str}")

        schema_lines.append("")

    conn.close()
    return "\n".join(schema_lines)


def get_table_names(db_path: str) -> list:
    """Return list of all table names in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables
