import sys
import psycopg2
from typing import List, Tuple, Set
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer, CrossEncoder
import numpy as np
import os

# --- CONFIGURATION ---
MODEL_NAME = 'BAAI/bge-base-en-v1.5'
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RERANKER_MODEL = 'BAAI/bge-reranker-base'
TOP_K_RETRIEVE = 25
TOP_K_RERANK = 5

# --- Load Models ---
try:
    print(f"[Retriever] Loading sentence-transformer model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
    print("[Retriever] Embedding model loaded successfully.")
except Exception as e:
    print(f"ERROR: Could not load embedding model: {e}")
    model = None

try:
    print(f"[Retriever] Loading reranker model '{RERANKER_MODEL}'...")
    reranker = CrossEncoder(RERANKER_MODEL)
    print("[Retriever] Reranker model loaded successfully.")
except Exception as e:
    print(f"ERROR: Could not load reranker model: {e}")
    reranker = None

# --- Connect to Neon ---
def _connect_to_db():
    conn_string = os.environ.get("NEON_DB_URL")
    if not conn_string:
        print("ERROR: 'NEON_DB_URL' not found in environment variables.")
        return None
    try:
        conn = psycopg2.connect(conn_string)
        return conn
    except Exception as e:
        print(f"ERROR: [Retriever] Could not connect to database: {e}")
        return None

# --- Relational Query ---
def query_relational_db(sql_query: str) -> List[Tuple]:
    print(f"[Retriever] Running SQL query: {sql_query}")
    conn = _connect_to_db()
    if conn is None:
        return [("Database connection error.",)]
    results = []
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            if cur.description:
                results = cur.fetchall()
            else:
                results = []
    except Exception as e:
        print(f"ERROR: SQL query failed: {e}")
        results = [(f"SQL error: {e}",)]
    finally:
        conn.close()
    if not results:
        return [("No results found for that query.",)]
    return results

# --- Vector + Keyword Hybrid Search + Rerank ---
def query_vector_db(query_text: str) -> List[str]:
    if model is None or reranker is None:
        return ["Error: Retrieval or reranker model not loaded."]

    conn = _connect_to_db()
    if conn is None:
        return ["Database connection error."]

    candidate_chunks: Set[str] = set()

    # --- Vector Search ---
    print(f"[Retriever] Performing vector search for: '{query_text}'")
    try:
        query_with_prefix = QUERY_PREFIX + query_text
        query_embedding = model.encode(query_with_prefix)
        with conn.cursor() as cur:
            register_vector(cur)
            cur.execute(
                f"""
                SELECT text_chunk FROM chunks
                ORDER BY embedding <-> %s
                LIMIT {TOP_K_RETRIEVE};
                """,
                (query_embedding,)
            )
            rows = cur.fetchall()
            for r in rows:
                candidate_chunks.add(r[0])
            print(f"[Retriever] Vector search found {len(rows)} results.")
    except Exception as e:
        print(f"ERROR: Vector search failed: {e}")

    # --- Keyword Search ---
    print(f"[Retriever] Performing keyword search for: '{query_text}'")
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT text_chunk FROM chunks, plainto_tsquery('english', %s) query
                WHERE query @@ to_tsvector('english', text_chunk)
                ORDER BY ts_rank_cd(to_tsvector('english', text_chunk), query) DESC
                LIMIT {TOP_K_RETRIEVE};
                """,
                (query_text,)
            )
            rows = cur.fetchall()
            for r in rows:
                candidate_chunks.add(r[0])
            print(f"[Retriever] Keyword search found {len(rows)} results.")
    except Exception as e:
        print(f"ERROR: Keyword search failed: {e}")
    finally:
        conn.close()

    # --- Rerank Combined Results ---
    all_chunks = list(candidate_chunks)
    if not all_chunks:
        return ["No relevant documents found."]

    print(f"[Retriever] Reranking {len(all_chunks)} chunks...")
    try:
        pairs = [[query_text, c] for c in all_chunks]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(all_chunks, scores), key=lambda x: x[1], reverse=True)
        top_results = [chunk for chunk, _ in ranked[:TOP_K_RERANK]]
        print(f"[Retriever] Returning top {len(top_results)} results.")
        return top_results
    except Exception as e:
        print(f"ERROR: Reranking failed: {e}")
        return ["Error during reranking."]
