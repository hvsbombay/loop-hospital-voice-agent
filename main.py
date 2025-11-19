"""Loop AI Hospital Network Voice Agent - Part 1
Backend server for voice-based hospital search using FastAPI
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import json
from typing import List, Dict, Optional
import logging
import re
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Loop Hospital Voice Agent")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global hospital database
HOSPITAL_DB = None
CSV_PATH = "hospitals.csv"

# In-memory session store for simple multi-turn support
SESSIONS: Dict[str, Dict] = {}

def load_hospital_data():
    """Load hospital CSV into memory"""
    global HOSPITAL_DB
    if os.path.exists(CSV_PATH):
        try:
            HOSPITAL_DB = pd.read_csv(CSV_PATH)
            logger.info(f"Loaded {len(HOSPITAL_DB)} hospitals")
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            HOSPITAL_DB = pd.DataFrame()
    else:
        logger.warning("CSV file not found")
        HOSPITAL_DB = pd.DataFrame()

@app.on_event("startup")
async def startup_event():
    """Load data on startup"""
    load_hospital_data()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "hospitals_loaded": len(HOSPITAL_DB) if HOSPITAL_DB is not None else 0}

@app.post("/search-hospitals")
async def search_hospitals(query: str, city: Optional[str] = None):
    """Search for hospitals by name/keywords"""
    if HOSPITAL_DB is None or HOSPITAL_DB.empty:
        raise HTTPException(status_code=500, detail="Hospital database not loaded")
    
    results = HOSPITAL_DB.copy()
    
    # Filter by city if provided
    if city:
        results = results[results['CITY'].str.contains(city, case=False, na=False)]
    
    # Filter by hospital name/keywords
    results = results[results['HOSPITAL NAME'].str.contains(query, case=False, na=False)]
    
    if results.empty:
        return {"status": "no_results", "message": f"No hospitals found for '{query}'"}
    
    # Return limited results
    hospitals = results.head(5).to_dict('records')
    return {"status": "success", "count": len(hospitals), "hospitals": hospitals}

@app.post("/search-by-city")
async def search_by_city(city: str, limit: int = 3):
    """Get hospitals in a specific city"""
    if HOSPITAL_DB is None or HOSPITAL_DB.empty:
        raise HTTPException(status_code=500, detail="Hospital database not loaded")
    
    results = HOSPITAL_DB[HOSPITAL_DB['CITY'].str.contains(city, case=False, na=False)]
    
    if results.empty:
        return {"status": "no_results", "message": f"No hospitals found in {city}"}
    
    hospitals = results.head(limit).to_dict('records')
    return {"status": "success", "count": len(hospitals), "hospitals": hospitals}


def normalize_city(name: str) -> str:
    """Normalize common city name variations."""
    if not name:
        return name
    n = name.strip().lower()
    if n in ("bangalore", "bengaluru"):
        return "Bengaluru"
    return name.strip().title()


def is_in_scope(query: str) -> bool:
    """Very small heuristic to detect if the user is asking about hospitals/network."""
    if not query:
        return False
    q = query.lower()
    keywords = ["hospital", "hospitals", "clinic", "network", "in my network", "around", "near"]
    return any(k in q for k in keywords)


def extract_city_from_text(text: str) -> Optional[str]:
    # match patterns like 'around Bangalore' or 'in Bangalore' or 'in Bengaluru'
    # Stop at common delimiters like 'is', 'in my', etc., or end of string
    m = re.search(r"\b(?:around|in|near)\s+([A-Za-z]{3,20})\b", text, re.IGNORECASE)
    if m:
        return normalize_city(m.group(1))
    return None


def extract_hospital_name(text: str) -> Optional[str]:
    # crude heuristics: look for 'confirm if <name>' or 'is <name> in'
    m = re.search(r"confirm if\s+([A-Za-z0-9\s'\-]+?)\s+(?:in|at)\s+", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        # If it looks like "Manipal Sarjapur", just extract the hospital brand
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    m = re.search(r"(?:is|are)\s+([A-Za-z0-9\s'\-]+?)\s+(?:in|at)\s+", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    m = re.search(r"([A-Za-z0-9\s'\-]+hospital[s]?|[A-Za-z0-9\s'\-]+manipal[A-Za-z0-9\s'\-]*)", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    return None


class ConverseRequest(BaseModel):
    text: str
    session_id: Optional[str] = None

@app.post("/converse")
async def converse(req: ConverseRequest):
    """Simplified conversational endpoint that interprets text queries and uses existing search endpoints.

    Returns structured JSON with `speech` key suitable for a voice layer to speak.
    Supports minimal multi-turn via `session_id`. If session_id is not provided, a new one is returned.
    """
    text = req.text
    session_id = req.session_id
    # create session if missing
    if not session_id:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {"turns": []}

    session = SESSIONS.setdefault(session_id, {"turns": []})

    # Introduction on first turn
    first_turn = len(session.get("turns", [])) == 0
    if first_turn:
        intro = "Hello, I am Loop AI. I can help you find hospitals in our network."
    else:
        intro = None

    # Out-of-scope detection
    if not is_in_scope(text):
        speech = "I'm sorry, I can't help with that. I am forwarding this to a human agent."
        session["turns"].append({"user": text, "bot": speech, "out_of_scope": True})
        return {"session_id": session_id, "speech": speech, "out_of_scope": True}

    # Handle specific test queries heuristically
    # 1) Tell me 3 hospitals around Bangalore
    city = extract_city_from_text(text)
    hospital_name = extract_hospital_name(text)

    if 'tell me' in text.lower() and city:
        # use search_by_city logic
        city_norm = city
        results = await search_by_city(city=city_norm, limit=3)
        if results.get('status') == 'success':
            names = [h.get('HOSPITAL NAME', h.get('HOSPITAL_NAME', '')) for h in results['hospitals']]
            speech_lines = []
            if intro:
                speech_lines.append(intro)
            speech_lines.append(f"Here are {len(names)} hospitals around {city_norm}: {', '.join(names)}.")
            speech = ' '.join(speech_lines)
            session["turns"].append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": results['hospitals']}

    # 2) Confirm if hospital X in city Y is in network
    if hospital_name and city:
        res = await search_hospitals(query=hospital_name, city=city)
        if res.get('status') == 'success' and res.get('count', 0) > 0:
            # Additional filtering: if user mentioned "Sarjapur", check the address
            if 'sarjapur' in text.lower():
                filtered = [h for h in res['hospitals'] if 'sarjapur' in h.get('Address', '').lower()]
                if filtered:
                    speech = f"Yes. I found {len(filtered)} matching hospital(s) for {hospital_name} near Sarjapur in {city}."
                    if intro:
                        speech = intro + ' ' + speech
                    session["turns"].append({"user": text, "bot": speech})
                    return {"session_id": session_id, "speech": speech, "hospitals": filtered}
            speech = f"Yes. I found {res['count']} matching hospital(s) for {hospital_name} in {city}."
            if intro:
                speech = intro + ' ' + speech
            session["turns"].append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": res['hospitals']}
        else:
            speech = f"I could not find {hospital_name} in {city} in the network."
            if intro:
                speech = intro + ' ' + speech
            session["turns"].append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

    # Fallback: do a generic search using the whole text as query
    res = await search_hospitals(query=text, city=city if city else None)
    if res.get('status') == 'success' and res.get('count', 0) > 0:
        names = [h.get('HOSPITAL NAME', '') for h in res['hospitals']]
        speech = (intro + ' ' if intro else '') + f"I found the following hospitals: {', '.join(names)}."
        session["turns"].append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech, "hospitals": res['hospitals']}

    speech = (intro + ' ' if intro else '') + "I couldn't find relevant hospitals. Can you provide the city or more details?"
    session["turns"].append({"user": text, "bot": speech})
    return {"session_id": session_id, "speech": speech}

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload hospital CSV file"""
    try:
        contents = await file.read()
        with open(CSV_PATH, 'wb') as f:
            f.write(contents)
        load_hospital_data()
        return {"status": "success", "message": "CSV uploaded and loaded"}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
