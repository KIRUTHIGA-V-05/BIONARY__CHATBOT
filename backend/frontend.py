import os
import threading
import traceback
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# --- Config ---
_MODEL = None
_MODEL_LOCK = threading.Lock()
MODEL_NAME = "BAAI/bge-base-en-v1.5"

def _get_db_connection():
    try:
        url = os.environ.get("NEON_DB_URL")
        if not url: return None
        return psycopg2.connect(url)
    except Exception as e:
        print(f"[frontend] DB Error: {e}")
        return None

def _load_model():
    global _MODEL
    if _MODEL: return _MODEL
    with _MODEL_LOCK:
        if not _MODEL:
            print(f"[frontend] Loading model '{MODEL_NAME}'...")
            _MODEL = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
    return _MODEL

def add_new_event(form_data):
    conn = _get_db_connection()
    if not conn: return {"status": "error", "message": "Database connection failed"}

    try:
        model = _load_model()
        
        # 1. Prepare Text Fields (Handle Defaults)
        name = form_data.get("name_of_event", "Unknown")
        desc = form_data.get("description_insights", "") or ""
        # Remove highlights merger if you aren't collecting highlights separately anymore
        # based on your csv, description_insights seems to be the main body.
        
        collab = form_data.get("collaboration", "N/A")
        
        # 2. Create Search Text (Context for the AI)
        # We include Collaboration here so users can ask "Show collaborative events"
        search_text = (
            f"Event: {name}\n"
            f"Domain: {form_data.get('event_domain', 'General')}\n"
            f"Description: {desc}\n"
            f"Perks: {form_data.get('perks', 'N/A')}\n"
            f"Collaboration: {collab}"
        )
        
        print(f"[frontend] Embedding: {name}")
        embedding_vector = model.encode(search_text).tolist()

        # 3. Insert into Database (Full Schema)
        with conn.cursor() as cur:
            register_vector(cur)
            sql = """
                INSERT INTO events (
                    event_id, serial_no, name_of_event, event_domain,
                    date_of_event, time_of_event, faculty_coordinators,
                    student_coordinators, venue, mode_of_event,
                    registration_fee, speakers, perks, collaboration,
                    description_insights, search_text, embedding
                )
                VALUES (%s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Map params strictly to the order above
            params = (
                name,                                           # event_id (using name)
                name,                                           # name_of_event
                form_data.get("event_domain"),                  # event_domain
                form_data.get("date_of_event"),                 # date_of_event
                form_data.get("time_of_event", "N/A"),
                form_data.get("faculty_coordinators", "N/A"),
                form_data.get("student_coordinators", "N/A"),
                form_data.get("venue", "N/A"),
                form_data.get("mode_of_event", "Offline"),
                form_data.get("registration_fee", "0"),
                form_data.get("speakers", "N/A"),
                form_data.get("perks", "N/A"),
                collab,                                         # collaboration
                desc,                                           # description_insights
                search_text,                                    # search_text
                embedding_vector                                # embedding
            )
            cur.execute(sql, params)
            
        conn.commit()
        return {"status": "success", "message": "Event saved successfully."}

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn: conn.close()