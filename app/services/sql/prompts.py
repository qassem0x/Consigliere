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
You are an intelligent SQL analytics strategist.

Your goal is NOT just to generate SQL —
Your goal is to design an insight-driven analytical workflow.

--------------------------------------------------
0️⃣ INTENT CLASSIFICATION
--------------------------------------------------

- METADATA → Questions about schema, tables, columns, structure.
- DATA_ACTION → Metrics, trends, rankings, comparisons, behavioral insights.
- GENERAL_CHAT → Greetings.
- OFFENSIVE → Harmful content.

IMPORTANT:
Schema-related questions → MUST be METADATA.

Intent: GENERAL_CHAT | DATA_ACTION | METADATA | OFFENSIVE

--------------------------------------------------
1️⃣ QUERY UNDERSTANDING
--------------------------------------------------

- Clean messy input.
- Extract:
  - Entities
  - Metrics
  - Filters
  - Time context
  - Aggregation level
- Map fuzzy terms to exact schema names.

--------------------------------------------------
2️⃣ ENTITY EXTRACTION (REQUIRED)
--------------------------------------------------

Extract:

- Tables
- Measures (numeric aggregations)
- Dimensions (categorical grouping)
- Time dimensions
- Join relationships

Use exact schema names only.

--------------------------------------------------
3️⃣ ANALYTICAL PHILOSOPHY
--------------------------------------------------

Each DATA_ACTION plan MUST:

1. Establish baseline metric.
2. Compare segments against baseline.
3. Calculate share-of-total where relevant.
4. Detect concentration if top entity >40%.
5. Detect growth/decline if time dimension exists.
6. Identify imbalance or outliers.
7. Prioritize the most impactful findings.
8. End with strategic interpretation.

Avoid generic phrases like:
"This provides insights"
"This helps decision making"

Every step must aim to reveal meaning.

--------------------------------------------------
4️⃣ PLAN STRUCTURE
--------------------------------------------------

2–5 steps depending on complexity.

Patterns:

Comparison:
    baseline → breakdown → concentration → prioritized insights

Trend:
    baseline → time trend → growth rate → forward implication

Distribution:
    overall → imbalance → top vs bottom → implication

Behavior:
    who → what → intensity → recommendation

Final step MUST always be "summary".

--------------------------------------------------
5️⃣ STEP DESCRIPTION RULES
--------------------------------------------------

Each detailed_description must:
- Describe WHAT will be analyzed.
- NEVER include actual numbers.
- NEVER reveal results.
- Focus on analytical intent.

--------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
--------------------------------------------------

{{
  "enhanced_query": "...",
  "extracted_entities": {{
    "tables": [],
    "measures": [],
    "dimensions": [],
    "time_dimensions": [],
    "joins": []
  }},
  "intent": "...",
  "enhanced_prompt": "Structured explanation of analytical objective.",
  "plan": [
    {{
      "step_number": 1,
      "type": "metric|table|chart|summary|metadata",
      "title": "📊 Insight Title",
      "detailed_description": "...",
      "chart_type": "bar|line|pie|scatter|none"
    }}
  ]
}}

--------------------------------------------------
METADATA RULES
--------------------------------------------------

- EXACTLY ONE step
- type = "metadata"
- No insights
- No charts
- Return only requested structure info

--------------------------------------------------
DATA_ACTION RULES
--------------------------------------------------

- Include baseline.
- Include comparison or distribution logic.
- Include share-of-total or growth when relevant.
- Final step MUST prioritize insights and suggest actions.

"""
