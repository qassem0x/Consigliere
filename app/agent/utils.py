import re


def clean_sql_response(response: str) -> str:
    cleaned = response.replace("```sql", "").replace("```", "").strip()
    if not cleaned.lower().startswith("select") and not cleaned.lower().startswith("with"):
        match = re.search(r"(SELECT|WITH)\s", cleaned, re.IGNORECASE)
        if match:
            cleaned = cleaned[match.start():]
    return cleaned


def sanitize_sql(sql_query: str) -> bool:
    lowered = sql_query.lower()
    if "error:" in lowered:
        return False
    banned = [
        r"\binsert\b", r"\bupdate\b", r"\bdelete\b", r"\bdrop\b",
        r"\balter\b", r"\bgrant\b", r"\btruncate\b", r"\bcreate\b",
    ]
    return not any(re.search(p, lowered) for p in banned)