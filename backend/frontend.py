import os
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("BAAI/bge-base-en-v1.5", trust_remote_code=True)

def _connect_to_db():
    conn_string = os.environ.get("NEON_DB_URL")
    if not conn_string:
        return None
    try:
        return psycopg2.connect(conn_string)
    except:
        return None

def _make_search_text(form_data):
    desc = form_data.get("description_insights", "") or ""
    perks = form_data.get("perks", "") or ""
    merged_description = desc.strip()
    search_text = (
        f"Event: {form_data.get('name_of_event', '')}\n"
        f"Domain: {form_data.get('event_domain', '')}\n"
        f"Details: {merged_description}\n"
        f"Perks: {perks}"
    )
    return merged_description, search_text

def add_new_event(form_data):
    conn = _connect_to_db()
    if not conn:
        return False, "Database connection error."
    try:
        register_vector(conn)
        event_id = form_data.get("name_of_event")
        merged_description, search_text = _make_search_text(form_data)
        embedding_vector = model.encode(search_text)
        if isinstance(embedding_vector, np.ndarray):
            embedding_vector = embedding_vector.tolist()
        parms = (
            event_id,
            0,
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
            form_data.get("perks", "N/A"),
            merged_description,
            search_text,
            embedding_vector,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (
                    event_id, serial_no, name_of_event, event_domain,
                    date_of_event, time_of_event, faculty_coordinators,
                    student_coordinators, venue, mode_of_event,
                    registration_fee, speakers, perks,
                    description_insights, search_text, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                parms,
            )
            conn.commit()
        conn.close()
        return True, "Event added."
    except Exception as e:
        return False, str(e)
