EXCEL_BRAIN_PROMPT = """
Analyze Excel/CSV data.

Schema: {schema}
History: {history}
Query: "{query}"

Intent: GENERAL_CHAT | DATA_ACTION | OFFENSIVE

Entity Extraction (REQUIRED):
Based on the schema above, identify which columns from the schema are most relevant to the user's query:
- Extract MEASURES (numeric columns for aggregation: sums, averages, counts)
- Extract DIMENSIONS (categorical/text columns for grouping/filtering)
- Extract TIME DIMENSIONS (date/datetime columns)
- Map user intent to actual schema column names

For example, if user says "sales by region", find the measure column (e.g., 'SalesAmount', 'Revenue') and dimension column (e.g., 'Region', 'City') from the schema.

For DATA_ACTION, create 1-3 steps:
1. Metric: Key number (total, average, etc.)
2. Chart: Trend/comparison (NOT the same as step 1)
3. Table: Detailed breakdown (top 10-20 rows)

Rules:
- When mentioning entities or column names write it in the same way it written in the schema and wrap it with single quotes
- NO duplicate visualizations (don't chart a single metric)
- Each step shows different view (number → trend → details)
- Filter data (limit to top 10-20, avoid raw dumps)
- Use descriptive titles with emojis
- MUST start with metric or table to establish baseline
- Charts require supporting numbers in metric/table step
- Be specific: "Top 10 X by Y with Z%" not "Analyze X"

Schema Fidelity (CRITICAL):
- Column names MUST match the schema EXACTLY (case-sensitive).
- Do NOT rename, lowercase, or infer variations.
- If schema has 'ColumnName', you MUST use 'ColumnName', NOT 'column name'.

Semantic Alignment:
- If user says "sales" but schema has 'SalesAmount', use 'SalesAmount'.
- Always map query meaning to schema fields correctly.

JSON format:
{{
  "intent": "...",
  "reasoning": "...",
  "extracted_entities": {{
    "measures": ["column_name1", "column_name2"],
    "dimensions": ["column_name1"],
    "time_dimensions": ["date_column"]
  }},
  "plan": [{{
    "step_number": 1,
    "type": "metric|chart|table|summary",
    "title": "💰 Descriptive Title",
    "detailed_description": "Write 2-5 sentences as a natural explanation. Skip 'This step does X'. Connect to previous steps naturally like 'Building on that, now we...' or 'Using those numbers, let's see...'. Be conversational, like explaining to a colleague.",
    "chart_type": "bar|line|scatter|pie|none"
  }}]
}}
"""

STEP_EXECUTOR_PROMPT = """
Execute step {step_number}.

Schema:
{schema}

User Query:
{query}

Step Type:
{step_type}

Task:
{step_description}

Previous Results:
{previous_results}

You are generating EXECUTABLE Python code.

STRICT EXECUTION RULES:

1️⃣ Use ONLY:
- pandas
- matplotlib.pyplot as plt

2️⃣ DataFrame:
- Use preloaded DataFrame named: df
- NEVER reload or recreate df

3️⃣ Schema Fidelity (CRITICAL):
- Column names MUST match schema EXACTLY (case-sensitive).
- DO NOT modify column casing.
- Before using any column:
    if 'ColumnName' not in df.columns:
        raise ValueError("Column 'ColumnName' not found in schema")

4️⃣ Defensive Data Handling:

For categorical columns used in groupby:
    df['ColumnName'] = df['ColumnName'].fillna('Unknown')

For numeric columns:
    df['ColumnName'] = pd.to_numeric(df['ColumnName'], errors='coerce')

5️⃣ No repeated transformations:
- If a derived column (like deck from 'Cabin') is needed:
    Only create it IF it does not already exist.

6️⃣ Output Contract (MANDATORY):

You MUST assign:
    result = ...
    description = "..."

IF step_type == 'metric':
    result must be:
        - single number
        OR formatted string
        OR small dictionary

IF step_type == 'table':
    result must be:
        - pandas DataFrame
        - limited to MAX 20 rows

IF step_type == 'chart':
    - Use plt.style.use('dark_background')
    - Add title and axis labels
    - Do NOT use plt.show()
    - Do NOT save file
    - result = plt.gcf()

7️⃣ Forbidden:
- os
- sys
- subprocess
- open
- exec
- eval
- __import__

8️⃣ Return ONLY executable Python code.
NO markdown.
NO explanations.
NO comments outside Python.

Generate code now.
"""
