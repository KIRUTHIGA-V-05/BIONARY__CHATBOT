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

def _safe_rows(rows):
    if not rows:
        return []
    if isinstance(rows[0][0], str) and rows[0][0].startswith("SQL error"):
        return []
    if rows[0][0] in ("No results", "Database connection error."):
        return []
    return rows

def _build_report(year):
    sql_chrono = f"""
        SELECT date_of_event, name_of_event, event_domain, venue, time_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY date_of_event;
    """
    chrono_rows = _safe_rows(R.query_relational_db(sql_chrono))

    if not chrono_rows:
        return f"I couldn't find any events for {year} in the database."

    dates = [r[0] for r in chrono_rows if r[0] is not None]
    min_date = min(dates) if dates else None
    max_date = max(dates) if dates else None
    total_events = len(chrono_rows)

    sql_domains = f"""
        SELECT event_domain, COUNT(*)
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        GROUP BY event_domain
        ORDER BY COUNT(*) DESC;
    """
    domain_rows = _safe_rows(R.query_relational_db(sql_domains))

    sql_domain_events = f"""
        SELECT event_domain, name_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year}
        ORDER BY event_domain, date_of_event;
    """
    domain_event_rows = _safe_rows(R.query_relational_db(sql_domain_events))

    domain_events_map = {}
    for dom, name in domain_event_rows:
        key = dom if dom else "Unspecified"
        if key not in domain_events_map:
            domain_events_map[key] = []
        domain_events_map[key].append(name)

    sql_venues = f"""
        SELECT venue, name_of_event
        FROM events
        WHERE EXTRACT(YEAR FROM date_of_event) = {year};
    """
    venue_rows = _safe_rows(R.query_relational_db(sql_venues))

    venue_groups = {}
    for venue, name in venue_rows:
        v = venue or ""
        vl = v.lower()
        if "team" in vl or "online" in vl:
            grp = "Online (MS Teams/General)"
        elif "auditorium" in vl or "hall" in vl:
            grp = "Physical (Auditorium/General Space)"
        elif "lab" in vl:
            grp = "Physical (Specialized Labs)"
        elif "stall" in vl or "expo" in vl:
            grp = "Outreach (On-Campus Stall)"
        elif v == "" or v == "N/A":
            grp = "Unspecified/General"
        else:
            grp = "Other Venues"
        if grp not in venue_groups:
            venue_groups[grp] = []
        venue_groups[grp].append(name)

    distinct_domains = [d[0] if d[0] else "Unspecified" for d in domain_rows] if domain_rows else []
    period_str = ""
    if min_date and max_date:
        period_str = f"{min_date} – {max_date}"
    elif min_date:
        period_str = str(min_date)
    else:
        period_str = f"{year}"

    header = f"# CLUB EVENTS ANNUAL ACTIVITY REPORT ({year})\n\n"

    metrics_table = "| Metric | Value |\n|--------|-------|\n"
    metrics_table += f"| Report Date | {datetime.date.today()} |\n"
    metrics_table += f"| Total Unique Events | {total_events} |\n"
    metrics_table += f"| Primary Domains Covered | {', '.join(distinct_domains) if distinct_domains else 'N/A'} |\n"
    metrics_table += f"| Event Period Covered | {period_str} |\n\n"

    chrono_table = "## 1. Chronological Event Overview\n\n"
    chrono_table += "| Date | Event Name | Domain | Venue/Format | Time |\n"
    chrono_table += "|------|------------|--------|--------------|------|\n"
    for date, name, domain, venue, time in chrono_rows:
        chrono_table += f"| {date} | {name} | {domain} | {venue} | {time} |\n"
    chrono_table += "\n"

    domain_section = "## 2. Domain Analysis and Focus Areas\n\n"
    domain_section += "| Domain | Number of Events | Event Names |\n"
    domain_section += "|--------|------------------|------------|\n"
    if domain_rows:
        for dom, count in domain_rows:
            key = dom if dom else "Unspecified"
            names = domain_events_map.get(key, [])
            names_str = ", ".join(names)
            domain_section += f"| {key} | {count} | {names_str} |\n"
    else:
        domain_section += "| N/A | 0 | N/A |\n"
    domain_section += "\n"

    venue_section = "## 3. Venue and Delivery Methodology\n\n"
    venue_section += "| Venue Type | Count | Representative Events |\n"
    venue_section += "|------------|-------|----------------------|\n"
    if venue_groups:
        for grp, names in venue_groups.items():
            count = len(names)
            rep = ", ".join(names[:4])
            if len(names) > 4:
                rep += " ..."
            venue_section += f"| {grp} | {count} | {rep} |\n"
    else:
        venue_section += "| N/A | 0 | N/A |\n"
    venue_section += "\n"

    executive = "## 0. Executive Summary\n\n"
    executive += f"The club organized {total_events} unique events in {year}, spanning key domains such as "
    executive += f"{', '.join(distinct_domains) if distinct_domains else 'N/A'}. "
    executive += f"Activities were conducted across a mix of online and physical venues, during the period {period_str}.\n\n"

    return header + metrics_table + executive + chrono_table + domain_section + venue_section

def _answer_from_context(question, context):
    if not context.strip():
        return "I couldn't find this information in the database."
    prompt = f"""
You answer ONLY using the database information below.
Do not use any outside knowledge.
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
