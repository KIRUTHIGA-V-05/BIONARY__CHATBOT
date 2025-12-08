# backend/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables BEFORE importing your logic
load_dotenv()

# Import your existing logic
import query_pipeline
import frontend 

app = FastAPI()

# Allow Next.js (running on localhost:3000) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class ChatRequest(BaseModel):
    query: str

class EventData(BaseModel):
    name_of_event: str
    event_domain: str
    date_of_event: str
    description_insights: str
    # Optional fields with defaults (Matching your Schema)
    time_of_event: Optional[str] = "N/A"
    faculty_coordinators: Optional[str] = "N/A"
    student_coordinators: Optional[str] = "N/A"
    venue: Optional[str] = "N/A"
    mode_of_event: Optional[str] = "Offline"
    registration_fee: Optional[str] = "0"
    speakers: Optional[str] = "N/A"
    perks: Optional[str] = "N/A"
    event_highlights: Optional[str] = ""

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "Club Knowledge Agent is active"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    """
    Calls query_pipeline.handle_user_query
    """
    try:
        print(f"Received query: {request.query}")
        response = query_pipeline.handle_user_query(request.query)
        return {"answer": response}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-event")
def add_event_endpoint(event: EventData):
    """
    Calls frontend.add_new_event (Option B: Instant Embedding)
    """
    try:
        # Convert Pydantic model to dict for your existing function
        form_data = event.dict()
        
        # Call your existing logic
        result = frontend.add_new_event(form_data)
        
        if result.get("status") == "success":
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("message"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run with: uvicorn main:app --reload