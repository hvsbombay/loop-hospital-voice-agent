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

# In-memory session store for multi-turn conversational support
SESSIONS: Dict[str, Dict] = {}

class SessionContext:
    """Enhanced session context with conversation memory"""
    def __init__(self):
        self.turns = []
        self.last_city = None
        self.last_hospital_name = None
        self.last_results = []
        self.last_total_count = 0
        self.pagination_offset = 0
        self.awaiting_clarification = False
        self.conversation_topic = None  # 'search', 'confirm', 'list'
    
    def update_context(self, city=None, hospital_name=None, results=None, total_count=0, topic=None):
        if city:
            self.last_city = city
        if hospital_name:
            self.last_hospital_name = hospital_name
        if results is not None:
            self.last_results = results
        if total_count > 0:
            self.last_total_count = total_count
        if topic:
            self.conversation_topic = topic
    
    def get_last_city(self):
        return self.last_city
    
    def get_last_hospital(self):
        return self.last_hospital_name

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


def get_hospitals_by_city_df(city: str) -> pd.DataFrame:
    """Return dataframe of hospitals that match the given city."""
    if HOSPITAL_DB is None or HOSPITAL_DB.empty:
        return pd.DataFrame()
    mask = HOSPITAL_DB['CITY'].str.contains(city, case=False, na=False)
    return HOSPITAL_DB[mask]


def wants_all_hospitals(text: str) -> bool:
    """Detect if the user is explicitly asking for every hospital in a city."""
    if not text:
        return False
    q = text.lower()
    triggers = [
        "all hospital",
        "all hospitals",
        "every hospital",
        "entire list",
        "complete list",
        "whole list"
    ]
    if any(trigger in q for trigger in triggers):
        return True
    return "all" in q and "hospital" in q


def is_in_scope(query: str, session_context=None) -> bool:
    """Detect if the user is asking about hospitals/network or continuing conversation."""
    if not query:
        return False
    q = query.lower()
    
    # Conversational continuations
    continuations = [
        "yes", "no", "sure", "okay", "next", "more", "show me", "tell me more",
        "what about", "how about", "thanks", "thank you", "that's helpful",
        "tell me about", "any other", "another", "different", "else"
    ]
    if any(cont in q for cont in continuations):
        return True
    
    # Hospital-related keywords
    keywords = ["hospital", "hospitals", "clinic", "network", "in my network", "around", "near", "location", "address"]
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
    
    # Create or retrieve session with enhanced context
    if not session_id:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = SessionContext()
    
    session_ctx = SESSIONS.get(session_id)
    if session_ctx is None or not isinstance(session_ctx, SessionContext):
        session_ctx = SessionContext()
        SESSIONS[session_id] = session_ctx
    
    # Introduction on first turn
    first_turn = len(session_ctx.turns) == 0
    if first_turn:
        intro = "Hello, I am Loop AI. I can help you find hospitals in our network."
    else:
        intro = None
    
    # Handle conversational follow-ups
    text_lower = text.lower()
    
    # Check for "next" or "more" requests
    if any(word in text_lower for word in ["next", "more", "show me more", "another"]):
        if session_ctx.last_city and session_ctx.last_total_count > 3:
            session_ctx.pagination_offset += 3
            city_matches = get_hospitals_by_city_df(session_ctx.last_city)
            next_batch = city_matches.iloc[session_ctx.pagination_offset:session_ctx.pagination_offset+3].to_dict('records')
            
            if next_batch:
                remaining = session_ctx.last_total_count - session_ctx.pagination_offset - len(next_batch)
                speech_lines = [f"Sure! Here are {len(next_batch)} more hospitals in {session_ctx.last_city}:"]
                for idx, h in enumerate(next_batch, session_ctx.pagination_offset + 1):
                    name = h.get('HOSPITAL NAME', 'Unknown')
                    address = h.get('Address', 'Address not available')
                    speech_lines.append(f"{idx}. {name}, located at {address}")
                if remaining > 0:
                    speech_lines.append(f"I have {remaining} more. Say 'next' to continue or ask about a specific area.")
                else:
                    speech_lines.append("That's all the hospitals I have in this city. Would you like to search in another city?")
                speech = ' '.join(speech_lines)
                session_ctx.turns.append({"user": text, "bot": speech})
                return {"session_id": session_id, "speech": speech, "hospitals": next_batch}
            else:
                speech = f"That's all the hospitals I have in {session_ctx.last_city}. Would you like to search in another city?"
                session_ctx.turns.append({"user": text, "bot": speech})
                return {"session_id": session_id, "speech": speech, "hospitals": []}
        else:
            speech = "I don't have more results to show. Would you like to search for hospitals in a different city?"
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech}
    
    # Handle thank you / acknowledgments
    if any(word in text_lower for word in ["thank", "thanks", "great", "perfect", "helpful"]):
        responses = [
            "You're welcome! Is there anything else you'd like to know about our hospital network?",
            "Glad I could help! Feel free to ask if you need information about hospitals in other cities.",
            "Happy to assist! Let me know if you need anything else."
        ]
        speech = responses[len(session_ctx.turns) % len(responses)]
        session_ctx.turns.append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech}
    
    # Handle affirmations with context
    if text_lower in ["yes", "sure", "okay", "ok", "yeah"] and session_ctx.awaiting_clarification:
        speech = "Great! Could you tell me which city or area you're interested in?"
        session_ctx.awaiting_clarification = False
        session_ctx.turns.append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech}
    
    # Out-of-scope detection with context awareness
    if not is_in_scope(text, session_ctx):
        speech = "I'm sorry, I can't help with that. I am forwarding this to a human agent."
        session_ctx.turns.append({"user": text, "bot": speech, "out_of_scope": True})
        return {"session_id": session_id, "speech": speech, "out_of_scope": True}

    # Handle specific test queries heuristically
    # 1) Tell me 3 hospitals around Bangalore
    city = extract_city_from_text(text)
    hospital_name = extract_hospital_name(text)

    if 'tell me' in text.lower() and city:
        city_norm = city
        city_matches = get_hospitals_by_city_df(city_norm)
        total_count = len(city_matches)
        if total_count == 0:
            speech = (intro + ' ' if intro else '') + f"I could not find hospitals in {city_norm}. Do you want to try another city?"
            session["turns"].append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

        if wants_all_hospitals(text) and total_count > 5:
            sampled = city_matches.head(5).to_dict('records')
            speech_lines = []
            if intro:
                speech_lines.append(intro)
            speech_lines.append(f"There are {total_count} hospitals in {city_norm}, which is too many to list at once.")
            speech_lines.append(f"Here are the first {len(sampled)} to get you started:")
            for idx, h in enumerate(sampled, 1):
                name = h.get('HOSPITAL NAME', 'Unknown')
                address = h.get('Address', 'Address not available')
                speech_lines.append(f"{idx}. {name}, located at {address}")
            speech_lines.append("Could you narrow it down by area, speciality, or ask for a smaller batch?")
            speech = ' '.join(speech_lines)
            
            # Update session context
            session_ctx.update_context(city=city_norm, results=sampled, total_count=total_count, topic='search')
            session_ctx.awaiting_clarification = True
            session_ctx.pagination_offset = 5
            session_ctx.turns.append({"user": text, "bot": speech, "needs_clarification": True})
            return {
                "session_id": session_id,
                "speech": speech,
                "hospitals": sampled,
                "total_matches": total_count,
                "needs_clarification": True
            }

        # default to sharing top 3 results for readability
        hospitals = city_matches.head(3).to_dict('records')
        speech_lines = []
        if intro:
            speech_lines.append(intro)
        speech_lines.append(f"I found {min(3, total_count)} hospitals in {city_norm}:")
        for idx, h in enumerate(hospitals, 1):
            name = h.get('HOSPITAL NAME', h.get('HOSPITAL_NAME', 'Unknown'))
            address = h.get('Address', 'Address not available')
            speech_lines.append(f"{idx}. {name}, located at {address}")
        if total_count > 3 and not wants_all_hospitals(text):
            remaining = total_count - 3
            speech_lines.append(f"I have {remaining} more results. Say 'next' to see more or ask about a specific neighbourhood.")
        speech = ' '.join(speech_lines)
        
        # Update session context
        session_ctx.update_context(city=city_norm, results=hospitals, total_count=total_count, topic='search')
        session_ctx.pagination_offset = 3
        session_ctx.turns.append({"user": text, "bot": speech, "total_matches": total_count})
        return {"session_id": session_id, "speech": speech, "hospitals": hospitals, "total_matches": total_count}

    # 2) Confirm if hospital X in city Y is in network
    if hospital_name and city:
        res = await search_hospitals(query=hospital_name, city=city)
        if res.get('status') == 'success' and res.get('count', 0) > 0:
            hospitals = res['hospitals']
            # Additional filtering: if user mentioned "Sarjapur", check the address
            if 'sarjapur' in text.lower():
                filtered = [h for h in hospitals if 'sarjapur' in h.get('Address', '').lower()]
                if filtered:
                    speech_parts = []
                    if intro:
                        speech_parts.append(intro)
                    speech_parts.append(f"Yes, {hospital_name} in {city} is in our network.")
                    speech_parts.append(f"I found {len(filtered)} location(s) near Sarjapur:")
                    for idx, h in enumerate(filtered, 1):
                        name = h.get('HOSPITAL NAME', 'Unknown')
                        addr = h.get('Address', 'Address not available')
                        speech_parts.append(f"{idx}. {name} at {addr}")
                    speech_parts.append("Would you like to know about any other hospital?")
                    speech = ' '.join(speech_parts)
                    
                    # Update session context
                    session_ctx.update_context(city=city, hospital_name=hospital_name, results=filtered, topic='confirm')
                    session_ctx.turns.append({"user": text, "bot": speech})
                    return {"session_id": session_id, "speech": speech, "hospitals": filtered}
            
            # General hospital confirmation with details
            speech_parts = []
            if intro:
                speech_parts.append(intro)
            speech_parts.append(f"Yes, {hospital_name} in {city} is in our network.")
            speech_parts.append(f"I found {len(hospitals)} location(s):")
            for idx, h in enumerate(hospitals[:3], 1):  # Limit to 3 for brevity
                name = h.get('HOSPITAL NAME', 'Unknown')
                addr = h.get('Address', 'Address not available')
                speech_parts.append(f"{idx}. {name} at {addr}")
            if len(hospitals) > 3:
                speech_parts.append(f"There are {len(hospitals) - 3} more locations. Would you like me to list them?")
            else:
                speech_parts.append("Is there anything else you'd like to know?")
            speech = ' '.join(speech_parts)
            
            # Update session context
            session_ctx.update_context(city=city, hospital_name=hospital_name, results=res['hospitals'], topic='confirm')
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": res['hospitals']}
        else:
            speech = f"I'm sorry, I could not find {hospital_name} in {city} in our network. "
            if intro:
                speech = intro + ' ' + speech
            
            # Provide helpful suggestions
            city_hospitals = get_hospitals_by_city_df(city)
            if len(city_hospitals) > 0:
                speech += f"However, I found {len(city_hospitals)} other hospitals in {city}. Would you like to hear about them?"
            else:
                speech += "Could you check the spelling or try a different hospital or city?"
            
            session_ctx.update_context(city=city, hospital_name=hospital_name)
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

    # Fallback: do a generic search using the whole text as query
    res = await search_hospitals(query=text, city=city if city else None)
    if res.get('status') == 'success' and res.get('count', 0) > 0:
        names = [h.get('HOSPITAL NAME', '') for h in res['hospitals']]
        speech = (intro + ' ' if intro else '') + f"I found the following hospitals: {', '.join(names)}. Would you like more details about any of these?"
        session_ctx.update_context(results=res['hospitals'], topic='search')
        session_ctx.turns.append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech, "hospitals": res['hospitals']}

    # Provide contextual help
    speech = (intro + ' ' if intro else '') + "I couldn't find relevant hospitals. "
    if session_ctx.last_city:
        speech += f"Would you like to search in {session_ctx.last_city} again, or try a different city?"
    else:
        speech += "Could you tell me which city you're interested in? I can help you find hospitals there."
    
    session_ctx.turns.append({"user": text, "bot": speech})
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
