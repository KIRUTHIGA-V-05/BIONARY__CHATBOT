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
        SELECT date_of_event, name_of_event, event_domain, venue, time_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event;
    """
    rows = R.query_relational_db(sql)
    if not rows or isinstance(rows[0][0], str) and rows[0][0].startswith("SQL error"):
        return "I couldn't generate a report because the database query failed."
    if len(rows) == 1 and rows[0][0] in ("No results", "Database connection error."):
        return "I couldn't find any events for that year in the database."

    header = f"# CLUB EVENTS ANNUAL ACTIVITY REPORT ({year})\n\n"
    table_header = "| Date | Event Name | Domain | Venue | Time |\n|------|-------------|--------|-------|------|\n"
    table_rows = ""

    for date, name, domain, venue, time in rows:
        table_rows += f"| {date} | {name} | {domain} | {venue} | {time} |\n"

    return header + table_header + table_rows

def _answer_from_context(question, context):
    if not context.strip():
        return "I couldn't find this information in the database."
    prompt = f"""
You answer ONLY using the database information below.
Do not use any knowledge beyond the database.
If the answer is not in the database, say:
"I couldn't find this information in the database."

Question:
{question}

Database:
{context}

Final Answer:
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
