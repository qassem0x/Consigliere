EXCEL_BRAIN_PROMPT = """
Analyze Excel/CSV data and create a comprehensive analysis plan.

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

Analysis Plan Design:
Your goal is to FULLY ANSWER the user's question with actionable insights. Consider:
1. What dimensions (categorical breakdowns) make sense for the query?
2. What measures (quantities, revenues, counts) answer the core question?
3. How can we reveal patterns, trends, or preferences?
4. What actionable recommendations can we derive?

Step Guidelines:
- Create 2-5 steps based on query complexity
- Each step should reveal NEW insight, not repeat information
- Pattern should vary based on query type:
  * Comparison queries: overview → breakdown → comparison → insights
  * Trend queries: baseline → trend → pattern → forecast
  * Distribution queries: overall → segments → outliers → summary
  * Behavioral queries: who → what → why → recommendations
- Include at least one table with actionable details (top N with specific columns)
- Final step should synthesize findings into actionable insights

Rules:
- When mentioning entities or column names write it in the same way it written in the schema and wrap it with single quotes
- NO duplicate visualizations (don't chart a single metric)
- Each step shows different view (number → trend → details)
- Filter data (limit to top 10-20, avoid raw dumps)
- Use descriptive titles with emojis
- MUST start with metric or table to establish baseline
- Charts require supporting numbers in metric/table step
- Be specific: "Top 10 X by Y with Z%" not "Analyze X"

Step Description Guidelines:
Write detailed_description that:
- Describes WHAT THE STEP WILL DO, not what the data shows (data isn't retrieved yet)
- Example: "This step will calculate total revenue by product category"
- Example: "This will identify the top 10 performing products by sales volume"
- NEVER include specific numbers, percentages, or product names
- NEVER say "This reveals that Product X contributed 40%" - you don't have the data yet!
- Keep it descriptive of the analysis intent only

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
    "detailed_description": "Describe what this step will analyze. Example: 'This step will calculate total revenue by product category to identify top performers.' NEVER include specific numbers, percentages, or actual product names - data hasn't been retrieved yet.",
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
        OR formatted string (e.g., "$1,234.56", "45.2%")
        OR small dictionary with formatted values
    IMPORTANT: Return CONTEXTUAL value with label, not raw number
    Example: result = {{"total_revenue": 125000, "avg_order_value": 89.50, "formatted": "$125,000 total revenue, $89.50 avg per order"}}

IF step_type == 'table':
    result must be:
        - pandas DataFrame
        - limited to MAX 20 rows
    IMPORTANT: Include relevant columns for insights, not just numeric
    IMPORTANT - Column Priority:
    - Prioritize showing descriptive columns like 'name', 'title', 'description', 'email', 'address', 'phone' over 'id', 'uuid', 'created_at', 'updated_at'
    - If data has both 'id' and 'name', show 'name' and omit 'id' unless explicitly requested
    - Show columns that tell a story, not just technical identifiers
    - Reorder columns: most important descriptive columns first

IF step_type == 'chart':
    - Use plt.style.use('dark_background')
    - Add title and axis labels
    - Do NOT use plt.show()
    - Do NOT save file
    - result = plt.gcf()

IF step_type == 'summary':
    - result must be formatted string
    - Include specific insights from the data
    - ONLY use actual values from the data, never make up numbers or percentages
    - NEVER use placeholders like "Product 1", "Category A"
    - If mentioning a specific value, it must be from the actual data
    - Provide actionable recommendations based on actual findings
    - NO raw numbers, NO tables

7️⃣ CRITICAL RULES - VIOLATIONS WILL CAUSE FAILURE:

📌 RULE 1: OUTPUT TYPE MAPPING (MUST FOLLOW EXACTLY)
   - step_type "metric" → result MUST be number/dict/string, NEVER plt.gcf()
   - step_type "chart" → result MUST be plt.gcf()
   - step_type "table" → result MUST be DataFrame
   - step_type "summary" → result MUST be formatted text string

📌 RULE 2: ALWAYS FILTER BEFORE VISUALIZATION
   - If showing categories → MUST filter to top 10
   - NEVER plot all categories - unreadable
   - Example: top_10 = df.groupby('city')['sales'].sum().nlargest(10)
   - Example: top_10 = df['category'].value_counts().head(10)

📌 RULE 3: CORRECT METRIC FOR QUERY
   - For "purchasing behavior" or "sales" → calculate REVENUE (unit_price × quantity)
   - For "average" queries → use mean()
   - For "total" or "sum" queries → use sum()
   - Match metric calculation to query intent

📌 RULE 4: AGGREGATE BEFORE CHARTING
   - NEVER plot raw data points - ALWAYS aggregate first
   - Scatter: one point per category, not per row
   - Bar: use aggregated values, not raw values
   - Correct: city_avg = df.groupby('city')[['price','qty']].mean(); plt.scatter(city_avg['price'], city_avg['qty'])
   - Wrong: for city in cities: plt.scatter(df[df.city==city].price, df[df.city==city].qty)

📌 RULE 5: CHART TYPE SELECTION
   - Comparison/ranking (top 10 cities) → bar chart
   - Trend over time → line chart
   - Part-to-whole (category distribution) → pie chart (max 5 slices) OR stacked bar
   - Relationship between two numeric values → scatter

📌 RULE 6: SUMMARY MUST BE ACTIONABLE & FACTUAL
   - summary step output must be human-readable text
   - Include ONLY specific cities/products that actually appear in the data
   - Provide clear recommendations based on actual data
   - NEVER make up percentages like "12.3% of revenue" unless calculated from data
   - NEVER use placeholders like "Product 1", "Category A", "Item X"
   - If data is insufficient, say so explicitly
   - NO raw numbers, NO DataFrames

📌 RULE 7: NUMERIC FORMATTING
   - Round ALL float numbers to 2 decimal places
   - Use round(value, 2) or .round(2) for all numeric calculations
   - Displayed values must have max 2 decimal points (e.g., 123.45, not 123.456789)

8️⃣ Forbidden:
- os
- sys
- subprocess
- open
- exec
- eval
- __import__

9️⃣ Return ONLY executable Python code.
NO markdown.
NO explanations.
NO comments outside Python.

Generate code now.
"""
