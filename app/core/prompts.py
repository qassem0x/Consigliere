SUMMARY_SYNTHESIS_PROMPT = """
Synthesize findings into executive insights.

User Query: {user_query}
Data: {context_str}
Instructions: {step_description}
zero_leaks_mode: {zero_leaks_mode}

CRITICAL ANTI-HALLUCINATION RULES:
1. ONLY cite numbers that appear in the Data section above
2. NEVER invent product names, categories, percentages, or trends
3. NEVER use placeholders like "Product 1", "Category A", "Item X"
4. Only mention specific values that are explicitly in the data
5. If data doesn't support a conclusion, don't state it
6. Use exact values from Data: section - no rounding or approximations unless specified
7. If data is limited, acknowledge: "Based on the available data showing [actual values]..."

Provide 3-5 sentence summary:
1. What was analyzed
if zero_leaks_mode is false only do that:
  2. Key findings with numbers (from Data only)
  3. Business implications (supported by data)
  4. 2-3 recommendations (based on actual findings)

if zero_leaks_mode is true do that:
  explain the analysis steps in simple way for user, don't dive in tech details

Professional tone, use markdown and separate sections with new line.
don't explicitly mention tech details like zero leaks mode 
"""

ANALYSIS_FORMAT_PROMPT = """
Synthesize data findings for executives.

Query: {user_query}
Data: {combined_summary}
zero_leaks_mode: {zero_leaks_mode}

CRITICAL ANTI-HALLUCINATION RULES:
1. ONLY use numbers and facts that appear in the Data section above
2. NEVER make up product names, categories, or percentages
3. NEVER use placeholders like "Product 1", "Category 1", "Item A"
4. If a specific value isn't in the data, don't mention it
5. If you're unsure about a number, check the Data section again
6. It's better to say "The data shows..." with exact values than to generalize
7. If data is insufficient, explicitly state: "The available data shows [actual values], but additional information would be needed to..."

Provide 3-5 sentences:
1. What was analyzed
if zero_leaks_mode is false only do that:
  2. Key findings from data summary (cite exact numbers from Data)
  3. Suggest Next questions

if zero_leaks_mode is true do that:
  explain every step in combined summary, but in simple way for user don't dive in tech details

Professional tone, use markdown and separate sections with new line.
don't explicitly mention tech details like zero leaks mode 
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
