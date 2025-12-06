import os
import re
import json
import google.generativeai as genai
import retriever as R

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

def _parse(j):
    m = re.search(r"\{.*\}", j, re.DOTALL)
    if not m:
        return {"intent": "semantic", "query": j}
    try:
        return json.loads(m.group(0))
    except:
        return {"intent": "semantic", "query": j}

def _prompt(q,y):
    return f"""
{{"intent": "semantic", "query": "intro to ai agents"}}
{{"intent": "structured", "query": "SELECT name_of_event,date_of_event,venue,time_of_event FROM events WHERE EXTRACT(YEAR FROM date_of_event)={y};"}}
User:"{q}"
"""

def handle_user_query(q):
    y=2025
    r=model.generate_content(_prompt(q,y))
    p=_parse(r.text)
    i=p.get("intent")
    s=p.get("query")
    if i=="structured":
        rows=R.query_relational_db(s)
        c=""
        for row in rows:
            c+=" | ".join(str(x) for x in row)+"\n"
    else:
        ctx=R.query_vector_db(s or q)
        c="\n".join(ctx)
    fp=f"Q:{q}\n{c}"
    ans=model.generate_content(fp)
    return ans.text
