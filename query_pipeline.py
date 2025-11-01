import os, re, sys, json, textwrap
import google.generativeai as genai
from typing import Dict, Any

# --- Import retriever ---
try:
    import retriever as member3_retriever
except ImportError:
    print("=" * 50)
    print("ERROR: Could not import 'retriever.py'.")
    print("Make sure it's in the same directory.")
    print("=" * 50)
    sys.exit(1)

# --- API Key Setup ---
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY missing in environment variables.")
    sys.exit(1)

genai.configure(api_key=API_KEY)
generation_model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")

# --- JSON Extractor ---
def _parse_json_from_response(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"intent": "error", "query": "Could not parse."}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"intent": "error", "query": "Invalid JSON."}

# --- Main Handler ---
def handle_user_query(user_question: str) -> str:
    current_year = 2025
    parsing_prompt = textwrap.dedent(f"""
You are a query-parsing agent for a university club's knowledge base.
Convert the user's question into a JSON object with an 'intent' and a 'query'.

TOOLS:
1. "structured" intent → factual SQL questions (who, when, how many, list all)
2. "semantic" intent → descriptive / conceptual questions (what, tell me about, topic search)

DATABASE SCHEMA:
Table: events
Columns: [
    event_id (TEXT, PK),
    serial_no (INT),
    name_of_event (TEXT),
    club_name (TEXT),
    event_domain (TEXT),
    date_of_event (DATE),
    time_of_event (TEXT),
    faculty_coordinators (TEXT),
    student_coordinators (TEXT),
    venue (TEXT),
    mode_of_event (TEXT),
    registration_fee (TEXT),
    speakers (TEXT),
    perks (TEXT),
    description_insights (TEXT),
    event_highlights (TEXT)
]

Table: chunks
Columns: [
    event_id (TEXT),
    chunk_id (TEXT),
    text_chunk (TEXT),
    embedding (VECTOR)
]

RULES:
1. Always use the correct column names — especially 'name_of_event', NOT 'event_name'.
2. Use ILIKE for string matching (e.g., WHERE perks ILIKE '%linkedin premium%').
3. For year filters, use: EXTRACT(YEAR FROM date_of_event) = 2025.
4. Use single quotes only in SQL.
5. Output JSON only in this format:
   {{"intent": "structured", "query": "SELECT name_of_event FROM events WHERE ..."}}
   or
   {{"intent": "semantic", "query": "linkedin premium"}}

User question: "{user_question}"
JSON Output:
""")


    print(f"[Pipeline] Parsing query: {user_question}")
    try:
        parser_response = generation_model.generate_content(parsing_prompt)
        parsed = _parse_json_from_response(parser_response.text)
    except Exception as e:
        return f"Error parsing query: {e}"

    intent = parsed.get("intent")
    query = parsed.get("query")
    context = ""
    sql_query_for_prompt = None

    if intent == "semantic":
        context_docs = member3_retriever.query_vector_db(query)
        context = "\n".join(context_docs)

    elif intent == "structured":
        sql_query_for_prompt = query

        # --- Fix for unsafe SQL from Gemini ---
        try:
            if query:
                clean_query = (
                    query.replace('"', "'")
                    .replace("“", "'")
                    .replace("”", "'")
                    .replace("`", "'")
                )
                sql_results = member3_retriever.query_relational_db(clean_query)
                context = f"Database query returned: {sql_results}"
            else:
                context = "Parser error: Missing SQL query."
        except Exception as e:
            context = f"This information is unavailable because the database query returned an SQL syntax error: {e}"

    else:
        context = f"Unrecognized intent: {intent}"

    final_prompt = textwrap.dedent(
        f"""
        You are the Club Knowledge Search Agent.
        Use the given context to answer clearly and factually.

        ---
        User Question: {user_question}
        Context: {context}
        SQL Query: {sql_query_for_prompt if sql_query_for_prompt else 'N/A'}
        ---

        Write a concise, natural answer based only on the context.
        """
    )

    print("[Pipeline] Generating final response...")
    try:
        answer = generation_model.generate_content(final_prompt)
        return answer.text
    except Exception as e:
        return f"Error during response generation: {e}"

