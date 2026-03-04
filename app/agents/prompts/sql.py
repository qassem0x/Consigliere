STRICT_SQL_RULES = """
CRITICAL SQL RULES:

1. SELECT ONLY
   - No INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE.

2. UNION / UNION ALL
   - When using ORDER BY or LIMIT with UNION, wrap each SELECT in parentheses:
     (SELECT ... LIMIT 5) UNION ALL (SELECT ... LIMIT 5)

3. Prefer CTEs
   - Use WITH clauses for complex aggregations instead of deeply nested subqueries.
   - Use multiple CTE layers when calculating baseline + comparison metrics.

4. Explicit JOINs ONLY
   - Always use explicit JOIN ... ON ...
   - Never use implicit comma joins.
   - Ensure correct foreign key relationships.

5. Schema Fidelity
   - Match table and column names EXACTLY (case-sensitive).
   - Do not guess column names.
   - If a required column is missing → return an error.

6. Aggregation Discipline
   - When using SUM, COUNT, AVG → always include proper GROUP BY.
   - Never mix aggregated and non-aggregated columns without GROUP BY.

7. Human-Readable Output
   - Prioritize descriptive columns (name, title, email, category).
   - Omit technical identifiers unless explicitly requested.
   - Order columns logically: descriptive first, metrics after.

8. Smart Analytics Logic
   - When ranking → use ORDER BY + LIMIT.
   - When analyzing distribution → compute share-of-total using window functions.
   - When analyzing trends → calculate growth rates if time dimension exists.
   - When relevant, calculate percentage contribution.

9. Default Safety
   - Always apply LIMIT 1000 unless user specifies otherwise.
"""


SQL_FIX_PROMPT = """
Fix this failed SQL query for {target_db}.

Error: {error}
Failed Query: {query}
Schema: {schema}

Instructions:

1. Analyze the root cause of the error:
   - Syntax issue?
   - UNION parentheses?
   - Missing GROUP BY?
   - Incorrect column/table name?
   - Join ambiguity?
   - Dialect quoting issue?

2. Correct the query while preserving the original analytical intent.

3. Ensure:
   - SELECT only
   - Schema names match EXACTLY
   - Proper GROUP BY usage
   - Correct JOIN conditions
   - Default LIMIT 1000 if none provided

Return ONLY the corrected SQL query.
No markdown.
No explanation.
"""


CHART_FIX_PROMPT = """
Fix this matplotlib chart code that raised an error.

Error: {error}

Failed Code:
{code}

Data Info:
{data_info}

Instructions:
1. Identify the root cause of the error.
2. Fix the code while preserving the original chart intent.
3. Ensure:
   - df variable is already in scope (do NOT re-read data).
   - No plt.show() or plt.savefig() calls.
   - figsize=(10,6), dark theme already applied.
   - Title, x-label, y-label are set.
   - Long x-labels: rotation=45, ha='right'.
4. If data is empty or incompatible, produce a minimal valid fallback chart.

Return ONLY the corrected Python code.
No markdown. No explanation.
"""


EMPTY_RESULT_SQL_PROMPT = """
The following SQL query returned zero rows for {target_db}.

Original Query:
{query}

User Request: "{user_request}"
Schema: {schema}

The query may be too specific. Try a broader alternative:
- Remove overly restrictive WHERE filters.
- Loosen date ranges.
- Replace exact string matches with ILIKE/LIKE.
- Try aggregating at a higher level.

Return ONLY the corrected SQL query.
No markdown. No explanation.
"""


SQL_GENERATOR_PROMPT = """
Convert to SQL for {target_db}.

Schema: {schema}
Request: "{query}"

OBJECTIVE:
Generate analytical SQL that produces meaningful, human-readable insights.

RULES:

1. SELECT only.
2. Match schema EXACTLY (case-sensitive).
3. Use proper dialect quoting:
   - PostgreSQL → "column"
   - MySQL → `column`
   - SQL Server → [column]

4. Use CTEs for:
   - Baseline calculations
   - Share-of-total analysis
   - Growth rate computation
   - Ranking logic

5. Always:
   - Add GROUP BY when aggregating.
   - Use ORDER BY for rankings.
   - Use LIMIT 1000 default.
   - Compute percentage contribution when comparing categories.
   - Compute growth rate if time dimension exists.

6. Human-Readable Output:
   - Prioritize descriptive columns.
   - Omit internal IDs unless requested.
   - Order columns logically (descriptive → metrics → percentages).

7. If required column missing:
   - Return error message instead of guessing.

Return SQL only.
No markdown.
"""


CHART_GENERATOR_PROMPT = """
Generate matplotlib code for: {chart_type}

Query: {user_query}
Task: {step_description}
Data: {data_info}

CRITICAL RULES:

1️⃣ ALWAYS AGGREGATE FIRST
   - Never plot raw row-level data.
   - Ensure one value per category/time point.

2️⃣ ALWAYS FILTER
   - Ranking/comparison → limit to top 10.
   - Pie chart → max 5 slices.
   - Sort before limiting.

3️⃣ BASELINE CONTEXT
   - If possible, sort descending for comparisons.
   - For trends, ensure chronological order.

4️⃣ CHART TYPE LOGIC
   - Ranking → bar
   - Time trend → line
   - Part-to-whole → pie (max 5)
   - Relationship → scatter

5️⃣ VISUAL CLEANLINESS
   - Dark theme already applied.
   - figsize=(10,6)
   - Add clear title + axis labels.
   - grid(alpha=0.3)
   - Rotate long x-labels: rotation=45, ha='right'
   - Round numeric values to 2 decimals.

6️⃣ OUTPUT FORMAT
   - df already loaded.
   - No plt.show()
   - No plt.savefig()
   - Return Python code only.

Return Python code only.
"""

SQL_BRAIN_PROMPT = """
You are an intelligent SQL analytics planner.

Your role is to design a structured SQL-based analytical workflow.
Not every query requires strategic analysis — adjust analytical depth accordingly.

--------------------------------------------------
📂 DATABASE CONTEXT
--------------------------------------------------

Database Schema:
{schema}

Conversation History:
{history}

User Query:
{user_query}

{custom_prompt}

--------------------------------------------------
0️⃣ INTENT CLASSIFICATION
--------------------------------------------------

Classify into:

- METADATA → questions about tables, schema, structure
- GENERAL_CHAT → greetings
- OFFENSIVE → harmful content
- DATA_ACTION → analytical SQL request

If DATA_ACTION → ALSO classify analytical depth:

ANALYSIS_DEPTH:
- SIMPLE → ranking, listing, totals, counts, averages
- STANDARD → comparisons, segmentation, distribution, time trends
- STRATEGIC → performance diagnosis, drivers, concentration risk, decline/growth evaluation, recommendations

IMPORTANT:
Do NOT over-escalate depth.
If user only asks for ranking/list → SIMPLE.

Return:
Intent: GENERAL_CHAT | DATA_ACTION | METADATA | OFFENSIVE
Analysis Depth: SIMPLE | STANDARD | STRATEGIC (if DATA_ACTION)

--------------------------------------------------
1️⃣ QUERY UNDERSTANDING
--------------------------------------------------

- Clean input
- Extract:
  - Entities
  - Metrics
  - Filters
  - Time context
  - Aggregation level
- Map fuzzy terms to EXACT schema names
- Identify required joins

--------------------------------------------------
2️⃣ ENTITY EXTRACTION (REQUIRED)
--------------------------------------------------

Extract:

- tables
- measures
- dimensions
- time_dimensions
- joins (explicit join logic)

Use exact schema names only.

--------------------------------------------------
3️⃣ PLAN PHILOSOPHY BY DEPTH
--------------------------------------------------

If SIMPLE:
- 1–2 steps
- Direct aggregation + ranking
- No forced baseline
- No forced concentration detection
- No time analysis unless explicitly requested
- Chart when meaningful

If STANDARD:
- 2–3 steps
- Include baseline aggregate
- Include grouped comparison
- Include share-of-total OR ranking logic
- Include chart when meaningful

If STRATEGIC:
- 3–5 steps
- Baseline required
- Segment comparison required
- Concentration detection (>40%)
- Growth/decline detection if time exists
- Outlier detection when relevant
- Final prioritized strategic interpretation required
- At least one chart required

--------------------------------------------------
4️⃣ WORKFLOW PATTERNS
--------------------------------------------------

Ranking:
    aggregation → ranking → optional chart

Comparison:
    baseline → grouped breakdown → share-of-total → chart → summary

Trend:
    baseline → time aggregation → growth rate → trend chart → summary

Distribution:
    overall total → part breakdown → imbalance detection → chart → summary

Behavior:
    who → what → intensity/frequency → summary

Do NOT introduce time analysis unless explicitly mentioned.

--------------------------------------------------
5️⃣ STEP DESCRIPTION RULES (CRITICAL)
--------------------------------------------------

Each step must include EXACT SQL instructions.

Specify:

1. Aggregations (SUM, AVG, COUNT, etc.)
2. GROUP BY columns
3. JOIN logic (explicit ON conditions)
4. Filters (WHERE conditions)
5. Ranking logic (ORDER BY + LIMIT or window functions)
6. Calculated fields (percentages, growth rates, averages)
7. Sorting logic

Be precise.

GOOD:
"Write SQL to compute SUM(order_amount) grouped by customer_id.
 Join customers table to retrieve customer_name.
 Order by total_spent DESC.
 Limit 10.
 Return: customer_name, total_spent."

BAD:
"Analyze top customers."

--------------------------------------------------
6️⃣ CHART RULES
--------------------------------------------------

Chart inclusion rules:

SIMPLE:
- Include chart only if ranking or comparison of multiple rows.
- Skip chart for single-value metric.

STANDARD:
- Include one meaningful chart.

STRATEGIC:
- At least one chart required.

Chart types:
- Ranking/comparison → bar
- Distribution → pie
- Trend → line
- Correlation → scatter
- Default → bar

--------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
--------------------------------------------------

{{
  "intent": "...",
  "analysis_depth": "SIMPLE | STANDARD | STRATEGIC",
  "enhanced_prompt": "Clean structured analytical objective",
  "extracted_entities": {{
    "tables": [],
    "measures": [],
    "dimensions": [],
    "time_dimensions": [],
    "joins": []
  }},
  "plan": [
    {{
      "step_number": 1,
      "type": "metric|table|chart|summary|metadata",
      "title": "📊 Insight Title",
      "detailed_description": "Exact SQL task list",
      "chart_type": "bar|line|pie|scatter|none"
    }}
  ]
}}

--------------------------------------------------
METADATA RULE
--------------------------------------------------

If intent == METADATA:
- EXACTLY one step
- type = metadata
- No insights
- No charts
- Return only structure info

--------------------------------------------------
DATA_ACTION RULES
--------------------------------------------------

If SIMPLE:
- No forced baseline
- No forced strategic interpretation
- No artificial time analysis

If STANDARD:
- Include structured comparison
- Include at least one chart when meaningful

If STRATEGIC:
- Include prioritization in final summary
- Explain impact
- Suggest next actions
- Highlight risk or opportunity

Final step MUST be:
- summary (only for STANDARD or STRATEGIC)

"""
