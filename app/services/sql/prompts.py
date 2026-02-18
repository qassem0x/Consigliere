STRICT_SQL_RULES = """
CRITICAL SYNTAX RULES:
1. UNION/UNION ALL with LIMIT/ORDER BY needs parentheses: (SELECT * FROM a LIMIT 5) UNION ALL (SELECT * FROM b LIMIT 5)
2. Prefer CTEs (WITH clause) over nested subqueries
3. Match schema table/column names exactly
4. Use explicit JOINs with proper ON conditions
"""

SQL_FIX_PROMPT = """
Fix this failed SQL query for {target_db}.

Error: {error}
Failed Query: {query}
Schema: {schema}

Instructions:
1. Analyze the error (UNION needs parentheses, check column names/case)
2. Return ONLY the corrected SQL query (no markdown, no explanations)
"""

CHART_GENERATOR_PROMPT = """
Generate matplotlib code for: {chart_type}

Query: {user_query}
Task: {step_description}
Data: {data_info}

Rules:
- DataFrame 'df' is loaded
- Dark theme already applied
- NO plt.savefig() or plt show()
- Set figsize=(10,6), add labels, grid(alpha=0.3)
- Rotate long x-labels: xticks(rotation=45, ha='right')
- Aggregate/sort/limit data appropriately

Chart types:
- bar: plt.bar() or df.plot.bar()
- line: plt.plot() or df.plot.line()
- pie: plt.pie() or df.plot.pie()
- scatter: plt.scatter() or df.plot.scatter()

Return Python code only.
"""

SQL_GENERATOR_PROMPT = """
Convert to SQL for {target_db}.

Schema: {schema}
Request: "{query}"

Rules:
1. SELECT only (no INSERT/UPDATE/DELETE/DROP/ALTER)
2. Dialects: PostgreSQL ("), MySQL (`), SQL Server ([])
3. Cast dates: CAST('2023-01-01' AS DATE)
4. Use JOINs for multi-table queries
5. Add GROUP BY for aggregations
6. Default LIMIT 1000
7. If column missing, check schema or return error
8.Only return columns that provide meaningful, human-readable information. Omit internal identifiers, primary/foreign keys, and other technical fields unless explicitly requested.

Return SQL only (no markdown).
"""

SQL_BRAIN_PROMPT = """
You are an AI assistant for SQL databases. Your task is to:

1️⃣ **Understand and clean the user's query**  
   - Normalize messy input
   - Extract intent, entities, metrics, filters, aggregation level, time context
   - Map fuzzy terms to actual schema tables/columns

2️⃣ **Entity Extraction (REQUIRED)**
   Based on the schema above, identify which tables and columns are most relevant to the user's query:
   - Extract TABLES to query from (e.g., 'orders', 'customers', 'products')
   - Extract MEASURES (numeric columns for aggregation: sums, averages, counts)
   - Extract DIMENSIONS (categorical/text columns for grouping/filtering)
   - Extract TIME DIMENSIONS (date/datetime columns)
   - Extract PRIMARY/FOREIGN KEYS for joins if needed
   - Map user intent to actual schema table/column names

3️⃣ **Design the SQL analysis workflow (plan)**  
   - Decide which steps are needed: metric, table, chart, summary
   - Each step should be actionable with clear descriptions for SQL/code generation
   - Follow best practices: no redundant charts, CTEs over nested subqueries, joins correct
   - Use emojis for titles where relevant
   - Summary step must always exist as final step
   - Output JSON only

Database Schema:
{schema}

User Query: "{user_query}"
History: "{history}"  # optional previous context

Rules:
- Charts: bar, line, pie, scatter; avoid >7 slices; line charts for sequential data
- SQL: SELECT only; obey STRICT_SQL_RULES
- Enhance clarity: time periods, limits, aggregation hints
- Output must be fully JSON-parsable
- Always use exact table and column names from the schema

Return JSON with keys:
{{
  "enhanced_query": "Clean, structured query",
  "extracted_entities": {{
    "tables": ["table_name1"],
    "measures": ["column_name"],
    "dimensions": ["column_name"],
    "time_dimensions": ["date_column"],
    "joins": ["table1.column = table2.column"]
  }},
  "intent": "GENERAL_CHAT | DATA_ACTION | OFFENSIVE",
  "reasoning": "Why these steps were chosen",
  "plan": [
    {{
      "step_number": 1,
      "type": "metric|table|chart|summary",
      "title": "💰 Title",
      "detailed_description": "Write 2-5 sentences as a natural explanation. Skip 'This step does X'. Connect to previous steps naturally like 'Building on that, now we...' or 'Using those results, let's also look at...'. Be conversational, like explaining to a colleague.",
      "chart_type": "bar|line|pie|scatter|none"
    }},
    ...
  ]
}}
"""
