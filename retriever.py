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
    except:
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
    remove = {"event","workshop","happen","when","what","where","who",
              "tell","me","about","the","a","an","of","in","on",
              "is","was","did","for"}
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
    except:
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
                LIMIT 10;
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
    ctx=[]
    for r in rows:
        ctx.append(
            f"Name: {r[0]}\nDomain: {r[1]}\nDate: {r[2]}\nTime: {r[3]}\nVenue: {r[4]}\nDetails: {r[5]}\n-----"
        )
    return ctx
