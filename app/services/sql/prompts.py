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

CRITICAL RULES:

📌 RULE 1: ALWAYS FILTER BEFORE VISUALIZATION
   - If showing categories → MUST filter to top 10
   - NEVER plot all categories  - unreadable
   - Example: data = data.nlargest(10, 'column')

📌 RULE 2: AGGREGATE BEFORE CHARTING
   - NEVER plot raw data points - ALWAYS aggregate first
   - Scatter: one point per category, not per row
   - Bar: use aggregated values, not raw values

📌 RULE 3: CHART TYPE SELECTION
   - Comparison/ranking (top 10) → bar chart
   - Trend over time → line chart
   - Part-to-whole → pie chart (max 5 slices) OR stacked bar
   - Relationship between two numeric → scatter

📌 RULE 4: OUTPUT FORMAT
   - DataFrame 'df' is loaded
   - Dark theme already applied
   - NO plt.savefig() or plt show()
   - Set figsize=(10,6), add labels, grid(alpha=0.3)
   - Rotate long x-labels: xticks(rotation=45, ha='right')
   - Aggregate/sort/limit data appropriately

📌 RULE 5: NUMERIC FORMATTING
   - Round ALL float numbers to 2 decimal places
   - Use round(value, 2) or .round(2) for all numeric calculations
   - Displayed values must have max 2 decimal points (e.g., 123.45, not 123.456789)

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
8. Only return columns that provide meaningful, human-readable information. Omit internal identifiers, primary/foreign keys, and other technical fields unless explicitly requested.

IMPORTANT - Column Priority:
- Prioritize showing descriptive columns like 'name', 'title', 'description', 'email', 'address', 'phone' over 'id', 'uuid', 'created_at', 'updated_at', 'modified_date'
- If a table has both 'id' and 'name', SELECT 'name' first and omit 'id' unless explicitly requested
- Show columns that tell a story, not just technical identifiers
- Order columns: most important descriptive columns first

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
   Your goal is to FULLY ANSWER the user's question with actionable insights. Consider:
   - What dimensions (categorical breakdowns) make sense for the query?
   - What measures (quantities, revenues, counts) answer the core question?
   - How can we reveal patterns, trends, or preferences?
   - What actionable recommendations can we derive?

4️⃣ **Step Guidelines**:
   - Create 2-5 steps based on query complexity
   - Each step should reveal NEW insight, not repeat information
   - Pattern should vary based on query type:
     * Comparison queries: overview → breakdown → comparison → insights
     * Trend queries: baseline → trend → pattern → forecast
     * Distribution queries: overall → segments → outliers → summary
     * Behavioral queries: who → what → why → recommendations
   - Include at least one table with actionable details (top N with specific columns)
   - Final step should synthesize findings into actionable insights
   - Use emojis for titles where relevant
   - Summary step must always exist as final step

5️⃣ **Step Description Guidelines**:
    Write detailed_description that:
    - Describes WHAT THE STEP WILL DO, not what the data shows (data isn't retrieved yet)
    - Example: "This step will calculate total revenue by product category"
    - Example: "This will identify the top 10 performing products by sales volume"
    - NEVER include specific numbers, percentages, or product names
    - NEVER say "This reveals that Product X contributed 40%" - you don't have the data yet!
    - Keep it descriptive of the analysis intent only

Database Schema:
{schema}

User Query: "{user_query}"
History: "{history}"  # optional previous context

Rules:
- Charts: bar, line, pie, scatter; avoid >7 slices; line charts for sequential data
- SQL: SELECT only; obey STRICT_SQL_RULES
- For "purchasing behavior" or "sales" → calculate REVENUE (price × quantity) if columns available
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
       "detailed_description": "Describe what this step will analyze. Example: 'This step will calculate total revenue by product category to identify top performers.' NEVER include specific numbers, percentages, or actual product names - data hasn't been retrieved yet.",
      "chart_type": "bar|line|pie|scatter|none"
    }},
    ...
  ]
}}
"""
