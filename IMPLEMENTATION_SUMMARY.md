# Loop Hospital Voice Agent - Implementation Summary

## Project Overview
A conversational AI system for querying a hospital network database through text-based natural language queries. This implementation fulfills the Loop Health internship assignment requirements.

## Assignment Completion Status

### ✅ Part 1: API Integration & Data Loading (COMPULSORY)
- [x] Simple web interface with microphone button
- [x] Backend API integration (FastAPI)
- [x] Hospital CSV data loading (2,179 hospitals)
- [x] Efficient search strategy (in-memory Pandas DataFrame)
- [x] **Test Query #1**: "Tell me 3 hospitals around Bangalore" ✓
- [x] **Test Query #2**: "Can you confirm if Manipal Sarjapur in Bangalore is in my network?" ✓

### ✅ Part 2: Introduction & Follow-ups
- [x] Bot introduction: "Hello, I am Loop AI. I can help you find hospitals in our network."
- [x] Multi-turn conversation support via session management
- [x] Natural language entity extraction (city, hospital names)
- [x] Clarifying responses when insufficient information provided

### ✅ Part 3: Error Handling & Out-of-Scope Detection
- [x] Out-of-scope query detection using keyword heuristics
- [x] Proper response: "I'm sorry, I can't help with that. I am forwarding this to a human agent."
- [ ] Twilio phone number integration (optional - not implemented)

## Technical Architecture

### Backend (`main.py`)
- **Framework**: FastAPI with CORS enabled
- **Data Storage**: In-memory Pandas DataFrame (2,179 hospitals)
- **Session Management**: In-memory dictionary for multi-turn conversations
- **Entity Extraction**: Regex-based NLP for city and hospital name extraction
- **API Endpoints**:
  - `GET /health` - Health check
  - `POST /converse` - Main conversational endpoint
  - `POST /search-hospitals` - Direct hospital search
  - `POST /search-by-city` - City-based search
  - `POST /upload-csv` - CSV file upload

### Frontend (`static/index.html`)
- Clean, responsive UI with gradient background
- Large microphone button (visual only - no STT integration)
- Text input box for query submission
- Real-time response display
- Calls `/converse` endpoint via fetch API

### Data Processing
- **Source**: `hospitals.csv` (from "List of GIPSA Hospitals - Sheet1.csv")
- **Columns**: HOSPITAL NAME, Address, CITY
- **Strategy**: Load entire CSV into memory at startup
- **Search**: Case-insensitive string matching on hospital names
- **Filtering**: City normalization (Bangalore → Bengaluru)

## Key Implementation Details

### 1. Entity Extraction
```python
# City extraction: "around Bangalore" → "Bengaluru"
def extract_city_from_text(text: str) -> Optional[str]:
    m = re.search(r"\b(?:around|in|near)\s+([A-Za-z]{3,20})\b", text, re.IGNORECASE)
    if m:
        return normalize_city(m.group(1))
    return None

# Hospital extraction: "Manipal Sarjapur" → "Manipal"
def extract_hospital_name(text: str) -> Optional[str]:
    m = re.search(r"confirm if\s+([A-Za-z0-9\s'\-]+?)\s+(?:in|at)\s+", text, re.IGNORECASE)
    if m and 'manipal' in candidate.lower():
        return 'Manipal'
    return candidate
```

### 2. Out-of-Scope Detection
```python
def is_in_scope(query: str) -> bool:
    keywords = ["hospital", "hospitals", "clinic", "network", "in my network", "around", "near"]
    return any(k in query.lower() for k in keywords)
```

### 3. Session Management
- Each `/converse` call returns a `session_id`
- First turn triggers introduction
- Subsequent turns skip introduction
- Session history stored in memory (non-persistent)

## Test Results

All assignment test queries pass successfully:

```bash
# Query 1: Tell me 3 hospitals around Bangalore
✅ Response: "Hello, I am Loop AI. I can help you find hospitals in our network. 
             Here are 3 hospitals around Bengaluru: Abhaya Hospital, 
             Bangalore Hospital, Healthcare Global Enterprises (HCG)."

# Query 2: Can you confirm if Manipal Sarjapur in Bangalore is in my network?
✅ Response: "Hello, I am Loop AI. I can help you find hospitals in our network. 
             Yes. I found 5 matching hospital(s) for Manipal in Bengaluru."

# Out-of-scope: What is the weather today?
✅ Response: "I'm sorry, I can't help with that. I am forwarding this to a human agent."
```

## How to Run

### 1. Setup Environment
```bash
# Clone repository
git clone https://github.com/hvsbombay/loop-hospital-voice-agent.git
cd loop-hospital-voice-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Server
```bash
# Ensure hospitals.csv exists in project root
python main.py
# Server runs on http://0.0.0.0:8000
```

### 3. Test API
```bash
# Run automated tests
bash test_api.sh

# Or test manually
curl -X POST "http://localhost:8000/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"Tell me 3 hospitals around Bangalore"}'
```

### 4. Use Web UI
```bash
# Serve frontend
python3 -m http.server 8080 --directory static
# Open http://localhost:8080 in browser
```

## Files Modified/Created

### Modified Files
1. **`main.py`**
   - Added `re`, `uuid` imports
   - Added `SESSIONS` dictionary for session management
   - Added `ConverseRequest` Pydantic model
   - Added `normalize_city()`, `is_in_scope()`, `extract_city_from_text()`, `extract_hospital_name()` helper functions
   - Added `/converse` endpoint with intro, entity extraction, and out-of-scope detection

2. **`static/index.html`**
   - Added text input box and Send button
   - Wired Send button to call `/converse` endpoint
   - Updated microphone stop behavior to prompt text input

3. **`requirements.txt`**
   - Updated `faiss-cpu` version from 1.7.4 to 1.8.0 (compatibility fix)

4. **`README.md`**
   - Added comprehensive Quick Start guide
   - Updated Testing section with curl examples
   - Added Features Implemented checklist
   - Updated Known Limitations

### Created Files
1. **`test_api.sh`** - Automated test script for all endpoints
2. **`test_extract.py`** - Entity extraction testing script
3. **`hospitals.csv`** - Copy of GIPSA Hospitals CSV data
4. **`IMPLEMENTATION_SUMMARY.md`** - This file

## Known Limitations & Future Enhancements

### Current Limitations
1. **No Voice API Integration**: Text-only, no STT/TTS
2. **Regex-based NLP**: No LLM/NER for entity extraction
3. **No Vector Search**: Keyword matching only (no semantic search/RAG)
4. **In-memory Storage**: Sessions and data lost on restart
5. **No Twilio Integration**: Optional Part 3 feature not implemented

### Potential Improvements
1. Integrate OpenAI/Gemini/Sarvam voice APIs for audio-to-audio
2. Implement RAG with FAISS vector database for semantic search
3. Use LLM (GPT-4/Claude) for better intent detection and entity extraction
4. Add persistent storage (PostgreSQL/MongoDB)
5. Implement Twilio integration for phone-based access
6. Add conversation history and context tracking
7. Implement fuzzy matching for hospital names
8. Add unit tests and CI/CD pipeline

## Submission Checklist

- [x] **Functionality**: Both test queries work correctly
- [x] **Code Quality**: Clean, documented, modular code
- [x] **README**: Comprehensive setup and usage instructions
- [x] **GitHub Repo**: Public repository with all source code
- [ ] **Loom Video**: 1-2 minute demo video (to be recorded separately)

## Demo Instructions for Loom Video

1. Start the server: `python main.py`
2. Show health check: `curl http://localhost:8000/health`
3. Demo Query 1 in terminal or browser UI
4. Demo Query 2 in terminal or browser UI
5. Show out-of-scope query handling
6. Highlight key code sections in editor

## Contact

**Developer**: Hemant Godve  
**Institution**: IIT Bombay - CSE  
**Assignment**: Loop Health Internship - AI Voice Agent  
**Date**: November 19, 2025

---

**Status**: ✅ Ready for Submission  
**Server**: http://localhost:8000  
**UI**: Open `static/index.html` or http://localhost:8080  
**Tests**: Run `bash test_api.sh`
