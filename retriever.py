import os
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("BAAI/bge-base-en-v1.5", trust_remote_code=True)

def _connect_to_db():
    url = os.environ.get("NEON_DB_URL")
    if not url:
        return None
    try:
        return psycopg2.connect(url)
    except Exception:
        return None


def query_relational_db(sql):
    conn = _connect_to_db()
    if not conn:
        return [("Connection error",)]
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception as e:
        rows = [(f"SQL error: {e}",)]
    conn.close()
    if not rows:
        return [("No results",)]
    return rows


def _clean(q):
    import re
    remove = {
        "event","workshop","happen","when","what","where","who","tell",
        "me","about","the","a","an","of","in","on","is","was","did","for"
    }
    q = re.sub(r"[^\w\s]", " ", q.lower())
    parts = [w for w in q.split() if w not in remove]
    return " ".join(parts) if parts else q


def query_vector_db(text):
    conn = _connect_to_db()
    if not conn:
        return ["Connection error"]
    
    q = _clean(text)
    
    try:
        emb = model.encode(q)
        if isinstance(emb, np.ndarray):
            emb = emb.tolist()
    except Exception:
        conn.close()
        return ["Embedding error"]

    try:
        with conn.cursor() as cur:
            register_vector(cur)
            cur.execute(
                """
                SELECT name_of_event, event_domain, date_of_event, time_of_event,
                       venue, description_insights,
                       1 - (embedding <=> %s::vector) AS sim
                FROM events
                ORDER BY embedding <-> %s::vector
                LIMIT 5;
                """,
                (emb, emb),
            )
            rows = cur.fetchall()
    except Exception as e:
        conn.close()
        return [f"Error {e}"]

    conn.close()

    if not rows:
        return ["No matches"]

    ctx = []
    for r in rows:
        ctx.append(
            f"Name: {r[0]}\n"
            f"Domain: {r[1]}\n"
            f"Date: {r[2]}\n"
            f"Time: {r[3]}\n"
            f"Venue: {r[4]}\n"
            f"Details: {r[5]}"
        )
    return ctx


def add_new_event(form_data):
    conn = _connect_to_db()
    if not conn:
        return False, "Database connection error."

    try:
        desc = (form_data.get("description_insights", "") or "").strip()
        perks = (form_data.get("perks", "") or "").strip()
        collab = (form_data.get("collaboration", "") or "").strip()

        search_text = (
            f"Event: {form_data.get('name_of_event', '')}\n"
            f"Domain: {form_data.get('event_domain', '')}\n"
            f"Details: {desc}\n"
            f"Perks: {perks}"
        )

        emb = model.encode(search_text)
        if isinstance(emb, np.ndarray):
            emb = emb.tolist()

        parms = (
            form_data.get("serial_no", 0),
            form_data.get("name_of_event"),
            form_data.get("event_domain"),
            form_data.get("date_of_event"),
            form_data.get("time_of_event", "N/A"),
            form_data.get("faculty_coordinators", "N/A"),
            form_data.get("student_coordinators", "N/A"),
            form_data.get("venue", "N/A"),
            form_data.get("mode_of_event", "N/A"),
            form_data.get("registration_fee", "0"),
            form_data.get("speakers", "N/A"),
            perks,
            collab,
            desc,
            search_text,
            emb,
        )

        with conn.cursor() as cur:
            register_vector(cur)
            cur.execute(
                """
                INSERT INTO events (
                    serial_no,
                    name_of_event,
                    event_domain,
                    date_of_event,
                    time_of_event,
                    faculty_coordinators,
                    student_coordinators,
                    venue,
                    mode_of_event,
                    registration_fee,
                    speakers,
                    perks,
                    collaboration,
                    description_insights,
                    search_text,
                    embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                parms,
            )

        conn.commit()
        conn.close()
        return True, "Event added successfully."

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)
