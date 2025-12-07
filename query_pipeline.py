import os
import re
import datetime
import google.generativeai as genai
import retriever as R

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

def _extract_year(text):
    m = re.search(r"(20\d{2})", text)
    if m:
        return int(m.group(1))
    return datetime.date.today().year

def _detect_intent(question):
    prompt = f"""
Classify the user's intent into one of these:
MULTI
SINGLE
ANALYTICS
FILTER
DESCRIBE
RECOMMEND

User question: "{question}"
Respond ONLY with: MULTI, SINGLE, ANALYTICS, FILTER, DESCRIBE, or RECOMMEND
"""
    resp = model.generate_content(prompt).text.strip().upper()
    if "MULTI" in resp: return "MULTI"
    if "ANALYTICS" in resp: return "ANALYTICS"
    if "FILTER" in resp: return "FILTER"
    if "DESCRIBE" in resp: return "DESCRIBE"
    if "RECOMMEND" in resp: return "RECOMMEND"
    return "SINGLE"

def _safe_rows(rows):
    if not rows:
        return []
    if isinstance(rows[0][0], str) and rows[0][0].startswith("SQL error"):
        return []
    if rows[0][0] in ("No results", "Connection error"):
        return []
    return rows

def _build_report(year):
    sql = f"""
        SELECT date_of_event, name_of_event, event_domain, venue, time_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event;
    """
    rows = _safe_rows(R.query_relational_db(sql))
    if not rows:
        return f"No events found for {year}."

    table = "| Date | Event | Domain | Venue | Time |\n|------|-------|--------|-------|------|\n"
    for d, n, dom, v, t in rows:
        table += f"| {d} | {n} | {dom} | {v} | {t} |\n"

    return f"Events in {year}:\n\n{table}"

def _build_partial_summary(question):
    ctx = R.query_vector_db(question)
    if not ctx or "No matches" in ctx[0]:
        return "No related events found."
    text = ""
    for c in ctx:
        text += c + "\n"
    return text

def _build_filtered_table(question):
    ctx = R.query_vector_db(question)
    if not ctx or "No matches" in ctx[0]:
        return "No matches."
    return "\n".join(ctx)

def _build_analytics(question):
    year = _extract_year(question)
    sql = f"""
        SELECT event_domain, COUNT(*)
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        GROUP BY event_domain
        ORDER BY COUNT(*) DESC;
    """
    rows = _safe_rows(R.query_relational_db(sql))
    if not rows:
        return "No data."
    out = f"Analytics for {year}:\n\n| Domain | Count |\n|--------|-------|\n"
    for d, c in rows:
        out += f"| {d} | {c} |\n"
    return out

def _build_description(question):
    ctx = R.query_vector_db(question)
    if not ctx or "No matches" in ctx[0]:
        return "No details found."
    return ctx[0]

def _build_recommendations(question):
    ctx = R.query_vector_db(question)
    if not ctx or "No matches" in ctx[0]:
        return "No recommended events found."
    return "\n".join(ctx[:3])

def _single_event_answer(question):
    ctx = R.query_vector_db(question)
    if not ctx or "No matches" in ctx[0]:
        return "Not found."
    return ctx[0]

def handle_user_query(question):
    intent = _detect_intent(question)
    year = _extract_year(question)
    if intent == "MULTI":
        if str(year) in question:
            return _build_report(year)
        return _build_partial_summary(question)
    if intent == "FILTER":
        return _build_filtered_table(question)
    if intent == "ANALYTICS":
        return _build_analytics(question)
    if intent == "DESCRIBE":
        return _build_description(question)
    if intent == "RECOMMEND":
        return _build_recommendations(question)
    return _single_event_answer(question)
