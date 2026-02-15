ROUTER_PROMPT = """
You are a classification agent. Your ONLY job is to route the query based on the user's intent.

Query: "{query}"
History: "{history}"

DEFINITIONS:
1. "GENERAL_CHAT":
   - Questions about YOU (the AI), your identity, or your capabilities.
   - Greetings, compliments, or general small talk.
   - **CRITICAL**: If the question can be answered WITHOUT looking at the dataset, it is GENERAL_CHAT.
   - Examples: "Who are you?", "What is your name?", "Hello", "Thanks", "Help me".

2. "DATA_ACTION":
   - Questions that require reading, calculating, or analyzing the database.
   - Queries referencing specific tables, columns, values, or statistics.
   - Examples: "Show me sales", "Count customers", "What's the average revenue?".

3. "OFFENSIVE": Harmful or malicious content.

INSTRUCTIONS:
- Analyze the input.
- Return ONLY the raw JSON string.
- Do NOT use Markdown formatting (no ```json ... ```).

OUTPUT FORMAT:
{{ "intent": "..." }}
"""

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

SUMMARY_SYNTHESIS_PROMPT = """
Synthesize findings into executive insights.

User Query: {user_query}
Data: {context_str}
Instructions: {step_description}

Provide 3-5 sentence summary:
1. What was analyzed
2. Key findings with numbers
3. Business implications
4. 2-3 recommendations

Plain text only.
"""

CHART_GENERATOR_PROMPT = """
Generate matplotlib code for: {chart_type}

Query: {user_query}
Task: {step_description}
Data: {data_info}

Rules:
- DataFrame 'df' is loaded
- Dark theme already applied
- NO plt.savefig() or plt.show()
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

ANALYSIS_FORMAT_PROMPT = """
Synthesize data findings for executives.

Query: {user_query}
Data: {combined_summary}

Provide 3-5 sentences:
1. What was analyzed
2. Key findings with numbers
3. Business implications
4. Next steps

Professional tone, no headers.
"""

DOSSIER_PROMPT = """
Generate executive intelligence report for new database.

Schema: {schema}
Stats: {stats}
Preview: {preview}
Type: {source_type}

Return JSON:
{{
  "briefing": "## 1. Executive Summary\\n* **Scope:** [X] tables, [Y] records\\n* **Domain:** [Industry]\\n* **Value:** [Why valuable]\\n\\n## 2. Intelligence\\n* **Model:** Tracks [Process]\\n* **Entities:** [Table1, Table2, Table3]\\n* **Relationships:** [FK descriptions]\\n\\n## 3. Assessment\\n* **Strengths:** [Data quality, structure]\\n* **Limitations:** [Missing data, concerns]\\n* **Opportunities:** [Analysis types]",
  "key_entities": ["Table1", "Table2", "..."],
  "recommended_actions": ["Q1", "Q2", "Q3"]
}}
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

Return SQL only (no markdown).
"""

SQL_BRAIN_PROMPT = """
Design SQL analysis workflow.

Schema: {schema}
History: {history}
Query: "{query}"

Intent: GENERAL_CHAT | DATA_ACTION | OFFENSIVE

For DATA_ACTION:
- Phase 1: Data steps (metric/table/chart) - each adds unique insight
- Phase 2: Summary step (MANDATORY) - synthesizes findings

Step types:
- metric: single value
- table: multi-row data
- chart: visualization (bar/line/pie/scatter)
- summary: synthesis (ALWAYS FINAL STEP)

Chart when to use:
- bar: compare categories, rankings
- line: trends over time
- pie: proportions (max 5-7 slices)
- scatter: correlations

Title emojis: 💰 Revenue, 📈 Growth, 📉 Decline, 📊 Charts, 🎯 KPIs, 💡 Insights, 🏆 Winners, ⚠️ Risks, 👥 Customers, 📦 Products, 🌍 Location, ⏰ Time, 💼 Business, 📋 Lists, 🔍 Analysis

Complexity:
- Simple: 1-2 steps + summary
- Medium: 3-5 steps + summary
- Complex: 5-8 steps + summary

Anti-patterns: No summary, vague summaries, redundant steps, generic titles, charts duplicating metrics, >7 pie slices, line charts for non-sequential

Summary description must specify:
- Patterns to identify
- Metrics to compare
- Business implications
- Recommendations
- Specific questions to answer

JSON format:
{{
  "intent": "...",
  "reasoning": "Why these steps/charts?",
  "plan": [
    {{"step_number": 1, "type": "metric|table|chart", "title": "💰 Title", "description": "SQL instruction", "chart_type": "bar|line|pie|scatter|none"}},
    {{"step_number": N, "type": "summary", "title": "💡 Insights", "description": "Detailed synthesis instructions", "chart_type": "none"}}
  ]
}}

Example (sales analysis):
{{
  "intent": "DATA_ACTION",
  "reasoning": "Show total, trend chart, top products chart, detail table, synthesize",
  "plan": [
    {{"step_number": 1, "type": "metric", "title": "💰 Total Sales (YTD)", "description": "SUM sales_amount WHERE sale_date >= '2024-01-01'", "chart_type": "none"}},
    {{"step_number": 2, "type": "chart", "title": "📈 Monthly Trend", "description": "Monthly sales aggregated, line chart for patterns", "chart_type": "line"}},
    {{"step_number": 3, "type": "chart", "title": "🏆 Top 10 Products", "description": "Product revenue, bar chart for comparison", "chart_type": "bar"}},
    {{"step_number": 4, "type": "table", "title": "📋 Product Details", "description": "TOP 20 products with units, avg sale", "chart_type": "none"}},
    {{"step_number": 5, "type": "summary", "title": "💼 Executive Summary", "description": "Analyze: (1) YTD context vs benchmarks (2) trend acceleration/patterns (3) top 3 products % of revenue, diversification (4) biggest opportunity & risk (5) 3 recommendations", "chart_type": "none"}}
  ]
}}
"""

EXCEL_BRAIN_PROMPT = """
Design Excel/CSV analysis.

Schema: {schema}
History: {history}
Query: "{query}"

Intent: GENERAL_CHAT | DATA_ACTION | OFFENSIVE

For DATA_ACTION:
- Step 1: Headline metric
- Step 2: Context chart (NOT same as metric)
- Step 3: Drill-down table
- Only use needed steps

Rules:
- NO redundant charts (don't chart single metrics)
- Diverse views (metric → chart → table)
- Filter/aggregate (top 10-20, not raw dumps)
- Descriptive titles with emojis

JSON:
{{
  "intent": "...",
  "reasoning": "...",
  "plan": [{{"step_number": 1, "type": "metric|chart|table|summary", "title": "💰 Title", "description": "Task", "chart_type": "bar|line|scatter|pie|none"}}]
}}
"""

STEP_EXECUTOR_PROMPT = """
Execute step {step_number}.

Schema: {schema}
Query: {query}
Type: {step_type}
Task: {step_description}
Previous: {previous_results}

Generate Python code:
- Use df (loaded DataFrame)
- Assign to 'result'
- Charts: use plt, dark_background applied, NO savefig/show
- Tables: return filtered DataFrame
- Metrics: return number/string/dict
- Also assign 'description' string

Notes:
- Verify columns exist in schema
- Check semantic matches (revenue→sales_amount)
- Only pandas/matplotlib allowed
- NO os/sys/subprocess/open/exec/eval
- Set title, labels, legend for charts

Return code only.
"""
