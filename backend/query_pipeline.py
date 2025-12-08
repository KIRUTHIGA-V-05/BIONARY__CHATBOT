import os
import json
import re
import sys
import google.generativeai as genai
import textwrap 

# --- Import Dependencies ---
try:
    from google.colab import userdata
    import retriever as retriever_module
except ImportError:
    # Fallback for local testing if not in Colab
    try:
        import retriever as retriever_module
    except ImportError:
        print("Error: Required modules not found.")
        sys.exit(1)

# --- Configuration ---
# Handle API Key from either Colab Secrets or Environment Variables
API_KEY = None
try:
    API_KEY = userdata.get('GEMINI_API_KEY')
except:
    API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("Error: GEMINI_API_KEY not found.")

genai.configure(api_key=API_KEY)
# Using the preview model as requested
generation_model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')

def parse_json_response(response_text):
    """Extracts JSON from the LLM's Markdown output."""
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        return {"intent": "error", "query": "No JSON found"}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"intent": "error", "query": "Invalid JSON"}

def handle_user_query(user_question):
    """Main Agent Loop."""
    
    # --- Step 1: Parse Intent (Gemini Call 1) ---
    # UPDATED SCHEMA: Matches 'events.csv' exactly now.
    parsing_prompt = textwrap.dedent(f"""
    You are a query parsing agent for a university club database.
    
    Tools Available:
    1. Relational DB (PostgreSQL): Use for structured facts (dates, names, counts, collaborations).
    2. Vector DB (Semantic Search): Use for concepts ("What is...", "Tell me about...").

    --- DATABASE SCHEMA (Table: 'events') ---
    Columns: [
        serial_no (INT),
        name_of_event (TEXT),
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
        collaboration (TEXT),  <-- NEW COLUMN ADDED
        description_insights (TEXT)
    ]
    
    OUTPUT FORMAT: {{"intent": "semantic", "query": "..."}} OR {{"intent": "structured", "query": "SELECT ..."}}

    RULES:
    1. For Domains (e.g., 'AI events'), query `event_domain`.
       * CRITICAL: Domains often have spaces around slashes (e.g., 'AI / ML').
       * Use ILIKE with % wildcards: `event_domain ILIKE '%AI%ML%'`.
    2. For Facts (Who, When, Count, Collaborations), use SQL.
       * Example: "List collaborative events" -> `SELECT name_of_event, collaboration FROM events WHERE collaboration IS NOT NULL AND collaboration != 'N/A'`
    3. For Semantic/Conceptual questions, set intent to 'semantic'.
       * IMPORTANT: Distill the query to keywords. 
       * Example: "Did any event mention RAG?" -> query: "RAG"
    4. SQL Syntax: Use `ILIKE` for text, `EXTRACT(YEAR FROM date_of_event)` for years.

    User Question: "{user_question}"
    JSON Output:
    """)

    try:
        parse_response = generation_model.generate_content(parsing_prompt)
        parsed_result = parse_json_response(parse_response.text)
    except Exception as e:
        return f"Error parsing query: {e}"

    # --- Step 2: Retrieve Context ---
    context_text = ""
    intent = parsed_result.get("intent")
    query_content = parsed_result.get("query")
    sql_used = None

    if intent == "semantic":
        results = retriever_module.query_vector_db(query_content)
        context_text = "\n\n".join(results)
    elif intent == "structured":
        sql_used = query_content
        results = retriever_module.query_relational_db(query_content)
        context_text = f"Database returned: {results}"
    else:
        context_text = "Error: Could not determine intent."

    # --- Step 3: Generate Answer (Gemini Call 2) ---
    final_prompt = textwrap.dedent(f"""
    You are the Club Knowledge Agent. Answer the user's question based ONLY on the context provided.

    User Question: {user_question}
    
    Context:
    {context_text}
    
    SQL Query Run (if any):
    {sql_used if sql_used else 'N/A'}

    Instructions:
    1. If the context is a Database Result (e.g., `[(8,)]`), turn it into a natural sentence.
       - If the result is empty or `[('',)]`, say "I do not have that information."
    2. If the context is text, be helpful and summarize.
    3. If the answer is not in the context, admit it. Do not hallucinate.

    Final Answer:
    """)

    try:
        final_response = generation_model.generate_content(final_prompt)
        return final_response.text
    except Exception as e:
        return f"Error generating response: {e}"

if __name__ == "__main__":
    print("--- Club Knowledge Agent Online ---")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break
        
        response = handle_user_query(user_input)
        print(f"Agent: {response}")