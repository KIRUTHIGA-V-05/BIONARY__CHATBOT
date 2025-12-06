import os
import threading
import traceback
import psycopg2
from typing import Dict, Any

try:
    import streamlit as st
    _HAS_ST = True
except Exception:
    st = None
    _HAS_ST = False

_MODEL = None
_MODEL_LOCK = threading.Lock()
_PROCESS_LOCK = threading.Lock()
MODEL_NAME = "BAAI/bge-base-en-v1.5"

def _get_db_url() -> str:
    if _HAS_ST:
        try:
            url = st.secrets["NEON_DB_URL"]
            if url:
                return url
        except Exception:
            pass
    url = os.environ.get("NEON_DB_URL")
    if not url:
        raise RuntimeError("NEON_DB_URL not found.")
    return url

def _get_db_connection():
    try:
        return psycopg2.connect(_get_db_url())
    except Exception as e:
        print(f"[frontend] DB connection error: {e}")
        return None

def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            try:
                from sentence_transformers import SentenceTransformer
                _MODEL = SentenceTransformer(MODEL_NAME)
            except Exception as e:
                print(f"[frontend] Failed to load model: {e}")
                _MODEL = None
        return _MODEL

def _make_search_text(form_data: Dict[str, Any]):
    desc = form_data.get("description_insights", "") or ""
    merged_description = desc.strip()
    search_text = (
        f"Event: {form_data.get('name_of_event', '')}\n"
        f"Domain: {form_data.get('event_domain', '')}\n"
        f"Description: {merged_description}\n"
        f"Perks: {form_data.get('perks', '')}"
    )
    return merged_description, search_text

def add_new_event(form_data: Dict[str, Any]) -> Dict[str, Any]:
    if not form_data.get("name_of_event") or not form_data.get("description_insights"):
        return {"status": "error", "message": "Missing required fields"}

    if not _PROCESS_LOCK.acquire(blocking=False):
        return {"status": "busy", "message": "Server busy, try again shortly."}

    try:
        merged_description, search_text = _make_search_text(form_data)
        model = _load_model()
        if model is None:
            return {"status": "error", "message": "Embedding model failed to load"}

        try:
            emb = model.encode(search_text)
            try:
                embedding_vector = emb.tolist()
            except Exception:
                embedding_vector = list(map(float, emb))
        except Exception as e:
            return {"status": "error", "message": f"Embedding error: {e}"}

        conn = _get_db_connection()
        if conn is None:
            return {"status": "error", "message": "DB connection failed"}

        try:
            with conn:
                with conn.cursor() as cur:
                    sql = """
                    INSERT INTO events (
                        event_id, serial_no, name_of_event, event_domain,
                        date_of_event, time_of_event, faculty_coordinators,
                        student_coordinators, venue, mode_of_event,
                        registration_fee, speakers, perks,
                        description_insights,
                        search_text, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    parms = (
                        form_data.get("name_of_event"),
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
                    cur.execute(sql, parms)
            return {"status": "success", "message": "Event saved and indexed", "event_id": form_data.get("name_of_event")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"DB insert failed: {e}"}
        finally:
            try:
                conn.close()
            except Exception:
                pass
    finally:
        _PROCESS_LOCK.release()
