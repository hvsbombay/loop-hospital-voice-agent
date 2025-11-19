"""Loop AI Hospital Network Voice Agent - Part 1
Backend server for voice-based hospital search using FastAPI
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse, JSONResponse, Response
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
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twilio Configuration (set these via environment variables)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Initialize Twilio client if credentials are provided
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Twilio client: {e}")

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

@app.post("/twilio/voice")
async def twilio_voice_webhook(request: Request):
    """Handle incoming Twilio voice calls"""
    response = VoiceResponse()
    
    # Welcome message
    response.say(
        "Hello! I am Loop A I, your hospital network assistant. "
        "You can ask me about hospitals in our network. "
        "For example, tell me hospitals in Mumbai, or ask if a specific hospital is in our network.",
        voice='Polly.Joanna',
        language='en-US'
    )
    
    # Gather user input
    gather = Gather(
        input='speech',
        action='/twilio/process-speech',
        method='POST',
        speech_timeout='auto',
        language='en-US'
    )
    gather.say(
        "What would you like to know?",
        voice='Polly.Joanna',
        language='en-US'
    )
    response.append(gather)
    
    # Fallback if no input
    response.say(
        "I didn't hear anything. Please call again.",
        voice='Polly.Joanna',
        language='en-US'
    )
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/twilio/process-speech")
async def twilio_process_speech(request: Request, SpeechResult: str = Form(None), CallSid: str = Form(None)):
    """Process speech input from Twilio and return response"""
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say(
            "I didn't catch that. Please try again.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.redirect('/twilio/voice')
        return Response(content=str(response), media_type="application/xml")
    
    logger.info(f"Received speech: {SpeechResult} from CallSid: {CallSid}")
    
    # Use the existing converse endpoint logic
    session_id = CallSid  # Use CallSid as session_id for call continuity
    
    try:
        # Process the query through our conversation handler
        converse_request = ConverseRequest(text=SpeechResult, session_id=session_id)
        result = await converse(converse_request)
        
        bot_response = result.get('speech', 'I apologize, I encountered an error.')
        
        # Speak the response
        response.say(
            bot_response,
            voice='Polly.Joanna',
            language='en-US'
        )
        
        # Ask for follow-up
        gather = Gather(
            input='speech',
            action='/twilio/process-speech',
            method='POST',
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(
            "Is there anything else you'd like to know?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.append(gather)
        
        # Goodbye message
        response.say(
            "Thank you for using Loop A I. Goodbye!",
            voice='Polly.Joanna',
            language='en-US'
        )
        
    except Exception as e:
        logger.error(f"Error processing speech: {e}")
        response.say(
            "I apologize, I encountered an error processing your request. Please try again.",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    return Response(content=str(response), media_type="application/xml")


@app.get("/twilio/status")
async def twilio_status():
    """Check Twilio integration status"""
    status = {
        "twilio_configured": twilio_client is not None,
        "phone_number": TWILIO_PHONE_NUMBER if TWILIO_PHONE_NUMBER else "Not configured",
        "account_sid": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else "Not configured"
    }
    return status


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


def handle_general_conversation(query: str, intro: Optional[str] = None) -> Optional[str]:
    """Handle common general questions and greetings like a normal AI assistant."""
    q = query.lower().strip()
    
    # Greetings - use word boundaries to avoid false matches (e.g., "Delhi" contains "hi")
    import re
    greetings = [r'\bhello\b', r'\bhi\b', r'\bhey\b', r'\bgood morning\b', r'\bgood afternoon\b', r'\bgood evening\b']
    if any(re.search(greeting, q) for greeting in greetings):
        if intro:
            return intro + " How can I help you today?"
        responses = [
            "Hello! I'm Loop AI, your hospital network assistant. How can I help you today?",
            "Hi there! I'm here to help you find hospitals in our network. What can I do for you?",
            "Hey! I can help you find hospitals and answer healthcare queries. What would you like to know?"
        ]
        return responses[hash(q) % len(responses)]
    
    # How are you
    if any(phrase in q for phrase in ["how are you", "how are you doing", "how's it going"]):
        return "I'm doing great, thank you for asking! I'm here to help you find hospitals in our network. What can I assist you with?"
    
    # What can you do / help with
    if any(phrase in q for phrase in ["what can you do", "what can you help", "what do you do", "your capabilities", "what are your features"]):
        return "I can help you find hospitals in our network across India! You can ask me things like: 'Tell me hospitals in Mumbai', 'Is Manipal Hospital in Bangalore?', 'Show me 5 hospitals in Delhi', or 'Give me hospitals near my location'. What would you like to know?"
    
    # Who are you / what are you
    if any(phrase in q for phrase in ["who are you", "what are you", "tell me about yourself"]):
        return "I'm Loop AI, a voice-enabled assistant designed to help you find hospitals in the Loop Health network. I can search hospitals by city, check if specific hospitals are in our network, and provide details about healthcare facilities. How can I help you today?"
    
    # Time/Date questions
    if "what time" in q or "what's the time" in q:
        from datetime import datetime
        return f"The current time is {datetime.now().strftime('%I:%M %p')}. Is there anything else I can help you with regarding our hospital network?"
    
    if "what date" in q or "what's the date" in q or "today's date" in q:
        from datetime import datetime
        return f"Today is {datetime.now().strftime('%B %d, %Y')}. Would you like to search for hospitals or get healthcare information?"
    
    # Weather (polite deflection)
    if "weather" in q:
        return "I'm specialized in hospital information, so I don't have weather data. But I can help you find hospitals in any city! Which city are you interested in?"
    
    # Jokes
    if "joke" in q or "make me laugh" in q:
        jokes = [
            "Why did the doctor carry a red pen? In case they needed to draw blood! Now, would you like to find a hospital?",
            "What did the doctor say to the rocket ship? Time to get your booster shot! Anyway, how can I help you with hospital information?",
            "Why did the nurse always carry a red marker? For drawing blood samples! Now, what hospitals can I help you find?"
        ]
        return jokes[hash(q) % len(jokes)]
    
    # Thank you (already handled elsewhere, but adding here for completeness)
    if q in ["thank you", "thanks", "thank you very much"]:
        return "You're welcome! Let me know if you need anything else."
    
    return None


def is_in_scope(query: str, session_context=None) -> bool:
    """Detect if the user is asking about hospitals/network or continuing conversation."""
    if not query:
        return False
    q = query.lower()
    
    # Always in scope for general conversation
    general_keywords = [
        "hello", "hi", "hey", "how are you", "what can you", "who are you",
        "time", "date", "joke", "weather", "help", "capabilities"
    ]
    if any(keyword in q for keyword in general_keywords):
        return True
    
    # Conversational continuations
    continuations = [
        "yes", "no", "sure", "okay", "next", "more", "show me", "tell me more",
        "what about", "how about", "thanks", "thank you", "that's helpful",
        "tell me about", "any other", "another", "different", "else",
        "yeah", "yep", "yup", "please"
    ]
    if any(cont in q for cont in continuations):
        return True
    
    # Hospital-related keywords (including medical facility types)
    keywords = [
        "hospital", "hospitals", "clinic", "clinics", "medical", "centre", "center",
        "network", "in my network", "around", "near", "location", "address",
        "kapoor", "manipal", "fortis", "apollo"  # Common hospital brand names
    ]
    return any(k in q for k in keywords)


def extract_quantity(text: str) -> Optional[int]:
    """Extract quantity/number from queries like 'give me 5 hospitals' or 'tell me three hospitals'"""
    # Number words mapping
    number_words = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    
    # Try to find numeric digits
    m = re.search(r'\b(\d+)\s+hospital', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    
    # Try to find number words
    for word, num in number_words.items():
        if re.search(r'\b' + word + r'\s+hospital', text, re.IGNORECASE):
            return num
    
    return None


def extract_city_from_text(text: str) -> Optional[str]:
    # match patterns like 'around Bangalore' or 'in Bangalore' or 'in Bengaluru'
    # Also match 'from Bangalore' pattern
    m = re.search(r"\b(?:around|in|near|from)\s+(?:the\s+)?([A-Za-z]{3,20})\b", text, re.IGNORECASE)
    if m:
        candidate = m.group(1)
        # Exclude non-city words
        excluded = ["database", "network", "my", "the", "this", "that", "these", "those"]
        if candidate.lower() not in excluded:
            return normalize_city(candidate)
    return None


def extract_hospital_name(text: str) -> Optional[str]:
    # Don't extract hospital name if this is a quantity-based query
    quantity_patterns = [
        r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+hospital',
        r'give me.*hospital',
        r'tell me.*hospital.*(?:in|from|around)',
        r'show me.*hospital'
    ]
    for pattern in quantity_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return None
    
    # Handle "is there any <hospital name>" pattern - stop before "in database/network"
    m = re.search(r"(?:is there any|there any|any)\s+((?:[A-Z][a-z]+\s*)+(?:Hospital|Centre|Center|Clinic|Medical)[A-Za-z\s]*?)(?:\s+in\s+(?:database|network|my network)|\?|$)", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    
    # Look for 'confirm if <name> in/at'
    m = re.search(r"confirm if\s+([A-Za-z0-9\s'\-]+?)\s+(?:in|at)\s+", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    
    # Look for 'is/are <name> in/at <city>'
    m = re.search(r"(?:is|are)\s+([A-Za-z0-9\s'\-]+?)\s+(?:in|at)\s+", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        if 'manipal' in candidate.lower():
            return 'Manipal'
        return candidate
    
    # Generic hospital name pattern (with medical keywords)
    m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Hospital|Centre|Center|Clinic|Medical))", text)
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
    if text_lower in ["yes", "sure", "okay", "ok", "yeah", "yep", "yup", "please"]:
        # Check if there are remaining hospitals to show
        if session_ctx.last_results and len(session_ctx.last_results) > 3:
            # Show the remaining hospitals
            remaining_hospitals = session_ctx.last_results[3:]  # Get hospitals after the first 3
            speech_lines = [f"Sure! Here are the remaining {len(remaining_hospitals)} locations:"]
            for idx, h in enumerate(remaining_hospitals, 4):  # Start from 4
                name = h.get('HOSPITAL NAME', 'Unknown')
                addr = h.get('Address', 'Address not available')
                city_name = h.get('CITY', '')
                if city_name:
                    speech_lines.append(f"{idx}. {name} at {addr}, {city_name}")
                else:
                    speech_lines.append(f"{idx}. {name} at {addr}")
            speech_lines.append("Is there anything else you'd like to know?")
            speech = ' '.join(speech_lines)
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": remaining_hospitals}
        
        # If awaiting clarification for city-based search
        if session_ctx.awaiting_clarification:
            speech = "Great! Could you tell me which city or area you're interested in?"
            session_ctx.awaiting_clarification = False
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech}
    
    # Handle general conversation (greetings, common questions, etc.)
    general_response = handle_general_conversation(text, intro)
    if general_response:
        speech = general_response
        session_ctx.turns.append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech}
    
    # Out-of-scope detection with context awareness
    if not is_in_scope(text, session_ctx):
        speech = "I'm sorry, I can't help with that. I am forwarding this to a human agent."
        session_ctx.turns.append({"user": text, "bot": speech, "out_of_scope": True})
        return {"session_id": session_id, "speech": speech, "out_of_scope": True}

    # Handle specific test queries heuristically
    # Extract components from query
    city = extract_city_from_text(text)
    hospital_name = extract_hospital_name(text)
    quantity = extract_quantity(text)

    # 1) Handle quantity-based city queries: "give me 5 hospitals from Bangalore"
    if city and not hospital_name and (quantity or any(word in text_lower for word in ['give me', 'show me', 'tell me'])):
        city_norm = city
        city_matches = get_hospitals_by_city_df(city_norm)
        total_count = len(city_matches)
        if total_count == 0:
            speech = f"I could not find hospitals in {city_norm}. Do you want to try another city?"
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

        if wants_all_hospitals(text) and total_count > 5:
            sampled = city_matches.head(5).to_dict('records')
            speech_lines = [
                f"There are {total_count} hospitals in {city_norm}, which is too many to list at once."
            ]
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

        # Use quantity if specified, otherwise default to 3
        num_results = quantity if quantity and quantity <= 10 else 3
        hospitals = city_matches.head(num_results).to_dict('records')
        speech_lines = [
            f"I found {len(hospitals)} hospitals in {city_norm}:"
        ]
        for idx, h in enumerate(hospitals, 1):
            name = h.get('HOSPITAL NAME', h.get('HOSPITAL_NAME', 'Unknown'))
            address = h.get('Address', 'Address not available')
            speech_lines.append(f"{idx}. {name}, located at {address}")
        if total_count > num_results:
            remaining = total_count - num_results
            speech_lines.append(f"I have {remaining} more results. Say 'next' to see more or ask about a specific neighbourhood.")
        speech = ' '.join(speech_lines)
        
        # Update session context
        session_ctx.update_context(city=city_norm, results=hospitals, total_count=total_count, topic='search')
        session_ctx.pagination_offset = num_results
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
                    speech_parts = [
                        f"Yes, {hospital_name} in {city} is in our network."
                    ]
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
            speech_parts = [
                f"Yes, {hospital_name} in {city} is in our network."
            ]
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
            
            # Provide helpful suggestions
            city_hospitals = get_hospitals_by_city_df(city)
            if len(city_hospitals) > 0:
                speech += f"However, I found {len(city_hospitals)} other hospitals in {city}. Would you like to hear about them?"
            else:
                speech += "Could you check the spelling or try a different hospital or city?"
            
            session_ctx.update_context(city=city, hospital_name=hospital_name)
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

    # 3) Handle hospital name query without city (search across all hospitals)
    if hospital_name and not city:
        res = await search_hospitals(query=hospital_name, city=None)
        if res.get('status') == 'success' and res.get('count', 0) > 0:
            hospitals = res['hospitals']
            cities = list(set([h.get('CITY', 'Unknown') for h in hospitals]))
            
            speech_parts = []
            
            if len(hospitals) == 1:
                h = hospitals[0]
                name = h.get('HOSPITAL NAME', 'Unknown')
                addr = h.get('Address', 'Address not available')
                city_name = h.get('CITY', 'Unknown')
                speech_parts.append(f"Yes, I found {name} in our network.")
                speech_parts.append(f"It is located at {addr} in {city_name}.")
            else:
                speech_parts.append(f"Yes, I found {len(hospitals)} locations with '{hospital_name}' in our network.")
                if len(cities) == 1:
                    speech_parts.append(f"All are in {cities[0]}:")
                else:
                    speech_parts.append(f"They are across {len(cities)} cities:")
                for idx, h in enumerate(hospitals[:3], 1):
                    name = h.get('HOSPITAL NAME', 'Unknown')
                    addr = h.get('Address', 'Address not available')
                    city_name = h.get('CITY', 'Unknown')
                    speech_parts.append(f"{idx}. {name} at {addr}, {city_name}")
                if len(hospitals) > 3:
                    speech_parts.append(f"And {len(hospitals) - 3} more locations. Would you like details about a specific city?")
            
            speech = ' '.join(speech_parts)
            session_ctx.update_context(hospital_name=hospital_name, results=hospitals, topic='confirm')
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": hospitals}
        else:
            speech_parts = [
                f"I'm sorry, I could not find '{hospital_name}' in our network database."
            ]
            speech_parts.append("Could you check the spelling or try a different hospital name?")
            speech = ' '.join(speech_parts)
            session_ctx.update_context(hospital_name=hospital_name)
            session_ctx.turns.append({"user": text, "bot": speech})
            return {"session_id": session_id, "speech": speech, "hospitals": []}

    # Fallback: do a generic search using the whole text as query
    res = await search_hospitals(query=text, city=city if city else None)
    if res.get('status') == 'success' and res.get('count', 0) > 0:
        names = [h.get('HOSPITAL NAME', '') for h in res['hospitals']]
        speech = f"I found the following hospitals: {', '.join(names)}. Would you like more details about any of these?"
        session_ctx.update_context(results=res['hospitals'], topic='search')
        session_ctx.turns.append({"user": text, "bot": speech})
        return {"session_id": session_id, "speech": speech, "hospitals": res['hospitals']}

    # Provide contextual help
    speech = "I couldn't find relevant hospitals. "
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
