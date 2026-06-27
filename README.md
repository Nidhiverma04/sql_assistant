
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

**1. Install Ollama**
Download from https://ollama.com and install it.

**2. Pull the model (one time, ~2GB)**

```bash
ollama pull llama3.2
```

**3. Start Ollama**

```bash
ollama serve
```

**4. Install Python dependencies**

```bash
pip install -r requirements.txt
```

**5. Run the app**

```bash
streamlit run app.py
```

Opens at http://localhost:8501

## Low RAM? Use the smaller model

```bash
ollama pull llama3.2:1b
```

Then change `"model": "llama3.2"` to `"model": "llama3.2:1b"` in `utils/nl_to_sql.py`

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

## Resume bullet

> Built an AI-powered NL-to-SQL assistant using Ollama (llama3.2) and Streamlit — converts plain English to executable SQLite queries with schema-aware prompt engineering, auto-correction loop for failed queries, auto-generated charts, plain English result explanations, and follow-up question suggestions; supports multi-table CSV uploads with cross-table JOIN queries
