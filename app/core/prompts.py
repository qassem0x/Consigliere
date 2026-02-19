SUMMARY_SYNTHESIS_PROMPT = """
Synthesize findings into executive insights.

User Query: {user_query}
Data: {context_str}
Instructions: {step_description}
zero_leaks_mode: {zero_leaks_mode}

Provide 3-5 sentence summary:
1. What was analyzed
if zero_leaks_mode is false only do that:
  2. Key findings with numbers
  3. Business implications
  4. 2-3 recommendations

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
Provide 3-5 sentences:
1. What was analyzed
if zero_leaks_mode is false only do that:
  2. Key findings from data summary 
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
