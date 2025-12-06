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

def _is_report_query(text):
    t = text.lower()
    if "report" in t:
        return True
    if "all events" in t:
        return True
    if "list events" in t:
        return True
    if "list all" in t:
        return True
    if "summary of events" in t:
        return True
    return False

def _build_report(year):
    sql = f"""
        SELECT name_of_event, date_of_event, time_of_event, venue, event_domain
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event;
    """
    rows = R.query_relational_db(sql)
    if not rows or isinstance(rows[0][0], str) and rows[0][0].startswith("SQL error"):
        return "I couldn't generate a report because the database query failed."
    if len(rows) == 1 and rows[0][0] in ("No results", "Database connection error."):
        return "I couldn't find any events for that year in the database."
    lines = []
    for name, date, time, venue, domain in rows:
        lines.append(f"{name} — {date} — {time} — {venue} — {domain}")
    if not lines:
        return "I couldn't find any events for that year in the database."
    header = f"Report of events in {year}:\n"
    body = "\n".join(lines)
    return header + body

def _answer_from_context(question, context):
    if not context.strip():
        return "I couldn't find this information in the database."
    prompt = f"""
You are an assistant answering questions ONLY about events stored in an internal database of a college club.
Use ONLY the information given in the DATABASE block below.
If the database does not contain enough information to answer, say exactly:
"I couldn't find this information in the database."
QUESTION:
{question}
DATABASE:
{context}
Answer concisely:
"""
    resp = model.generate_content(prompt)
    return resp.text

def handle_user_query(user_question):
    if _is_report_query(user_question):
        year = _extract_year(user_question)
        return _build_report(year)

    ctx_list = R.query_vector_db(user_question)
    context = "\n".join(ctx_list)
    if ctx_list and ctx_list[0] in ("Connection error", "Embedding error", "No matches"):
        return "I couldn't find this information in the database."
    return _answer_from_context(user_question, context)
