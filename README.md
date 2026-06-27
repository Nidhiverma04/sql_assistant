
# AI SQL Query Assistant

Natural language → SQL → Results → Insights. Runs fully locally via Ollama — no API key needed.

## Features

- **NL to SQL** — type a question, get a SQL query instantly
- **Auto-execute** — query runs automatically, results shown as a table
- **Auto-fix** — if SQL fails, sends error back to model and retries
- **Auto chart** — numeric results get an instant bar/line/area chart
- **Query explanation** — plain English insight after every result
- **Follow-up suggestions** — 3 clickable next questions after each query
- **Multi-table support** — upload multiple CSVs and JOIN across them
- **Download results** — export any result as CSV

## Setup

**1. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**2. Run the app**

```bash
streamlit run app.py
```

Opens at http://localhost:8501


## Project structure

```
sql_assistant/
├── app.py                    # Main Streamlit app
├── utils/
│   ├── nl_to_sql.py          # Ollama API calls — SQL gen, explain, follow-ups
│   └── schema_extractor.py   # Extracts schema + sample values from SQLite
├── requirements.txt
└── README.md
```
