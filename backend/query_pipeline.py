import os
import re
import json
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
Classify the user's intent.
If the user asks about all events in a year, month, semester, or club-wide activities,
ALWAYS classify as: MULTI

Intent categories:
MULTI
SINGLE
ANALYTICS
FILTER
DESCRIBE
RECOMMEND

Examples of MULTI:
"list all the events this year"
"what all events happened in 2025"
"events this month"
"show club events"
"tell me all events"
"give a report on 2024 events"

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


def _safe(rows):
    if not rows: return []
    if isinstance(rows[0][0], str) and rows[0][0].startswith("SQL error"): return []
    if rows[0][0] in ("No results", "Connection error"): return []
    return rows


def _extract_fields(user_query):
    prompt = f"""
Determine what specific event attributes the user wants.

Allowed attribute keys:
["name", "domain", "date", "time", "venue", "details", "all"]

Examples:
"When was the event conducted?" -> ["date","time"]
"Return the date" -> ["date"]
"Where did it take place?" -> ["venue"]
"What was the event about?" -> ["details"]
"Intro to AI Agents" -> ["all"]

User Query: "{user_query}"
Return JSON list only.
"""
    try:
        resp = model.generate_content(prompt).text.strip()
        fields = json.loads(resp)
        if isinstance(fields, list) and fields:
            return fields
    except:
        pass
    return ["all"]


def _build_report(year):
    sql = f"""
        SELECT date_of_event, name_of_event, event_domain, venue, time_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event;
    """
    rows = _safe(R.query_relational_db(sql))
    if not rows:
        return f"No events found for {year}."

    dates = [r[0] for r in rows if r[0] is not None]
    total_events = len(rows)
    min_d = min(dates) if dates else year
    max_d = max(dates) if dates else year
    period = f"{min_d} – {max_d}" if dates else f"{year}"

    sql2 = f"""
        SELECT event_domain, COUNT(*)
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        GROUP BY event_domain;
    """
    domain_rows = _safe(R.query_relational_db(sql2))

    sql3 = f"""
        SELECT venue, COUNT(*)
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        GROUP BY venue;
    """
    venue_rows = _safe(R.query_relational_db(sql3))

    header = f"# CLUB EVENTS ANNUAL ACTIVITY REPORT ({year})\n\n"
    execu = f"## 0. Executive Summary\n\nTotal Events: {total_events}\nPeriod: {period}\n\n"
    
    table = "## 1. Chronological Event Overview\n\n| Date | Event | Domain | Venue | Time |\n|------|-------|--------|-------|------|\n"
    for d, n, dom, v, t in rows:
        table += f"| {d} | {n} | {dom} | {v} | {t} |\n"
    table += "\n"

    domain_sec = "## 2. Domain Distribution\n\n| Domain | Count |\n|--------|-------|\n"
    if domain_rows:
        for d, c in domain_rows:
            domain_sec += f"| {d} | {c} |\n"
    else:
        domain_sec += "| N/A | 0 |\n"
    domain_sec += "\n"

    venue_sec = "## 3. Venue Breakdown\n\n| Venue | Count |\n|-------|-------|\n"
    if venue_rows:
        for v, c in venue_rows:
            venue_sec += f"| {v} | {c} |\n"
    else:
        venue_sec += "| N/A | 0 |\n"
    venue_sec += "\n"

    return header + execu + table + domain_sec + venue_sec


def _build_analytics(q):
    y = _extract_year(q)
    sql = f"""
        SELECT event_domain, COUNT(*)
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {y}
        GROUP BY event_domain
        ORDER BY COUNT(*) DESC;
    """
    rows = _safe(R.query_relational_db(sql))
    if not rows: return "No data."
    o = f"Analytics for {y}:\n\n| Domain | Count |\n|--------|-------|\n"
    for d, c in rows: o += f"| {d} | {c} |\n"
    return o


def _build_filtered(q):
    ctx = R.query_vector_db(q)
    if not ctx or "No matches" in ctx[0]: return "No matches."
    return "\n".join(ctx)


def _build_description(q):
    ctx = R.query_vector_db(q)
    if not ctx or "No matches" in ctx[0]: return "No details found."
    return ctx[0]


def _build_recommend(q):
    ctx = R.query_vector_db(q)
    if not ctx or "No matches" in ctx[0]: return "No recommended events found."
    return "\n".join(ctx[:3])


def _single(q):
    ctx = R.query_vector_db(q)
    if not ctx or "No matches" in ctx[0]:
        return "Not found."

    event_block = ctx[0]
    fields = _extract_fields(q)

    if "all" in fields:
        return event_block

    filtered = []
    for line in event_block.split("\n"):
        l = line.lower()
        if "name:" in l and "name" in fields: filtered.append(line)
        if "domain:" in l and "domain" in fields: filtered.append(line)
        if "date:" in l and "date" in fields: filtered.append(line)
        if "time:" in l and "time" in fields: filtered.append(line)
        if "venue:" in l and "venue" in fields: filtered.append(line)
        if "details:" in l and "details" in fields: filtered.append(line)

    return "\n".join(filtered) if filtered else event_block


def handle_user_query(q):
    intent = _detect_intent(q)
    y = _extract_year(q)

    if intent == "MULTI": return _build_report(y)
    if intent == "FILTER": return _build_filtered(q)
    if intent == "ANALYTICS": return _build_analytics(q)
    if intent == "DESCRIBE": return _build_description(q)
    if intent == "RECOMMEND": return _build_recommend(q)

    return _single(q)
