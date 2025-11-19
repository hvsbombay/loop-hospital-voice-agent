# Loop AI - Hospital Network Voice Agent 🏥

> AI-powered voice assistant for querying hospital networks - Part 1: API Integration, Data Loading & Hospital Search

## Overview

This project implements an intelligent voice-based hospital search system that enables users to query a large network of hospitals through conversational voice commands. Part 1 focuses on the core infrastructure including:

- ✅ FastAPI backend with efficient hospital database
- ✅ Responsive web UI with microphone recording
- ✅ Keyword-based hospital search functionality
- ✅ CSV data loading and parsing
- ✅ RESTful API endpoints

## Part 1: Requirements Met

### 1. API Integration & Data Loading ✓
- **Backend**: FastAPI server (`main.py`)
- **Data Handling**: Pandas-based CSV loading with efficient in-memory storage
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /search-hospitals` - Search by name/keywords
  - `POST /search-by-city` - City-based search
  - `POST /upload-csv` - Upload hospital CSV data

### 2. Hospital Search Strategy ✓

Implemented efficient search without sending entire CSV to AI models:

```python
# String matching for hospital names
results = df[df['HOSPITAL NAME'].str.contains(query, case=False, na=False)]

# City filtering
results = results[results['CITY'].str.contains(city, case=False, na=False)]
```

### 3. Frontend UI ✓
- Clean, responsive design with gradient background
- Large microphone button (emoji-based)
- Audio recording capability using Web Audio API
- Real-time response display
- Mobile-friendly interface

## Project Structure

```
loop-hospital-voice-agent/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── static/
│   └── index.html         # Frontend UI
├── README.md              # This file
└── hospitals.csv          # Hospital database (to be added)
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip
- Modern web browser (Chrome, Firefox, Edge)

### Backend Setup

```bash
# Clone repository
git clone https://github.com/hvsbombay/loop-hospital-voice-agent.git
cd loop-hospital-voice-agent

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

Server runs on `http://localhost:8000`

### Frontend

Open `static/index.html` in your browser or serve via:

```bash
# Using Python's built-in server
python -m http.server 8080 --directory static
```

Access at `http://localhost:8080`

## API Usage

### Converse Endpoint (text)

You can make conversational queries (used by the frontend text box) to the `/converse` endpoint. It returns a JSON object with a `speech` field suitable for a voice layer to speak.

Example:

```bash
curl -X POST "http://localhost:8000/converse" -H "Content-Type: application/json" -d '{"text":"Tell me 3 hospitals around Bangalore"}'
```

The frontend at `static/index.html` also includes a text input and `Send` button that calls this endpoint for quick manual testing.

### Test Queries (Part 1 Requirements)

#### Query 1: "Tell me 3 hospitals around Bangalore"
```bash
curl -X POST "http://localhost:8000/search-by-city?city=Bangalore&limit=3"
```

**Expected Response:**
```json
{
  "status": "success",
  "count": 3,
  "hospitals": [
    {
      "HOSPITAL NAME": "Manipal Hospitals",
      "Address": "...",
      "CITY": "Bengaluru"
    },
    ...
  ]
}
```

#### Query 2: "Can you confirm if Manipal Sarjapur in Bangalore is in my network?"
```bash
curl -X POST "http://localhost:8000/search-hospitals?query=Manipal%20Sarjapur&city=Bangalore"
```

**Expected Response:**
```json
{
  "status": "success",
  "count": 1,
  "hospitals": [
    {
      "HOSPITAL NAME": "Manipal Hospitals originally incorporated with the name of Columbia Asia Hospital group",
      "Address": "Sy. No. 10p 12p, Ramagondanahalli Village...",
      "CITY": "Bengaluru"
    }
  ]
}
```

## Data Format

Expected CSV columns:
```
HOSPITAL NAME | Address | CITY
```

Example row:
```
Manipal Hospitals | Sy. No. 10p 12p, Ramagondanahalli Village | Bengaluru
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, Python 3.8+ |
| **Data Processing** | Pandas, NumPy |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Audio** | Web Audio API, MediaRecorder |
| **Database** | CSV (in-memory with Pandas) |

## Performance Optimization

- **In-Memory Storage**: All hospitals loaded into DataFrame at startup
- **Efficient Filtering**: Vectorized string operations with Pandas
- **Limit Results**: Returns max 5 results per query to reduce payload
- **Case-Insensitive Search**: Prevents duplicate matches

## Future Enhancements (Parts 2 & 3)

### Part 2: Voice Integration & Follow-ups
- [ ] Integrate Gemini/OpenAI/Sarvam voice API
- [ ] Implement bot introduction: "I am Loop AI"
- [ ] Add follow-up question handling
- [ ] Multi-turn conversation support

### Part 3: Advanced Features
- [ ] Out-of-scope query detection
- [ ] Error handling & fallbacks
- [ ] Twilio integration for phone numbers
- [ ] RAG vector database (FAISS)
- [ ] Semantic search capabilities

## Quick Start

### 1. Clone and Install
```bash
git clone https://github.com/hvsbombay/loop-hospital-voice-agent.git
cd loop-hospital-voice-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Prepare Data
```bash
# The CSV file should be named 'hospitals.csv' in the project root
# If you have a different name, rename it:
cp "List of GIPSA Hospitals - Sheet1.csv" hospitals.csv
```

### 3. Start the Server
```bash
python main.py
# Server starts on http://0.0.0.0:8000
```

### 4. Test the API
Open another terminal and run:
```bash
# Test query #1
curl -X POST "http://localhost:8000/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"Tell me 3 hospitals around Bangalore"}'

# Test query #2
curl -X POST "http://localhost:8000/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"Can you confirm if Manipal Sarjapur in Bangalore is in my network?"}'

# Test out-of-scope
curl -X POST "http://localhost:8000/converse" \
  -H "Content-Type: application/json" \
  -d '{"text":"What is the weather today?"}'
```

### 5. Use the Web UI
Open `static/index.html` in your browser or:
```bash
# Serve the frontend
python3 -m http.server 8080 --directory static
# Then visit http://localhost:8080
```

Type your query in the text box and click **Send** to get a response from Loop AI.

## Testing

### Manual Testing Steps

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status":"healthy","hospitals_loaded":2179}
   ```

2. **Test Assignment Queries**:
   ```bash
   # Query 1: Tell me 3 hospitals around Bangalore
   curl -X POST "http://localhost:8000/converse" \
     -H "Content-Type: application/json" \
     -d '{"text":"Tell me 3 hospitals around Bangalore"}'
   
   # Query 2: Confirm Manipal Sarjapur in Bangalore
   curl -X POST "http://localhost:8000/converse" \
     -H "Content-Type: application/json" \
     -d '{"text":"Can you confirm if Manipal Sarjapur in Bangalore is in my network?"}'
   ```

3. **Legacy Search Endpoints** (still available):
   ```bash
   # City search
   curl -X POST "http://localhost:8000/search-by-city?city=Bengaluru&limit=3"
   
   # Hospital search
   curl -X POST "http://localhost:8000/search-hospitals?query=Manipal&city=Bengaluru"
   ```

## Files Explained

### `main.py` - Backend Server
- FastAPI application with CORS enabled
- Hospital database management
- Search endpoints
- CSV upload handler
- Startup event to load data

### `static/index.html` - Frontend UI
- Responsive design with gradient background
- Microphone recording button
- Audio capture using Web Audio API
- Response display area
- Animated UI elements

### `requirements.txt` - Dependencies
```
fastapi==0.104.1         # Web framework
uvicorn==0.24.0          # ASGI server
pandas==2.1.3            # Data processing
numpy==1.26.2            # Numerical computing
requests==2.31.0         # HTTP client
python-dotenv==1.0.0     # Environment variables
faiss-cpu==1.7.4         # Vector search (future)
scikit-learn==1.3.2      # ML utilities (future)
```

## Features Implemented

### Part 1 (Compulsory) ✅
- ✅ Simple web interface with microphone button
- ✅ FastAPI backend with hospital CSV data loading (2179 hospitals)
- ✅ Efficient in-memory search without sending entire CSV to AI
- ✅ Successfully handles test query #1: "Tell me 3 hospitals around Bangalore"
- ✅ Successfully handles test query #2: "Can you confirm if Manipal Sarjapur in Bangalore is in my network?"

### Part 2 ✅
- ✅ Introduction: Bot says "Hello, I am Loop AI. I can help you find hospitals in our network."
- ✅ Multi-turn conversation support via session_id
- ✅ Entity extraction (city, hospital name) from natural language queries
- ✅ Clarifying questions (implicit through fallback responses)

### Part 3 ✅
- ✅ Out-of-scope detection: Non-hospital queries trigger "I'm sorry, I can't help with that. I am forwarding this to a human agent."
- ⚠️ Twilio integration (optional): Not implemented in this demo

## Known Limitations

1. **No Voice-to-Voice API Integration**: Text-based `/converse` endpoint only (STT/TTS not integrated)
2. **Simple Regex-based NLP**: Uses regex patterns for entity extraction instead of LLM/NER
3. **Basic Semantic Matching**: Keyword search on hospital names (no vector/RAG search yet)
4. **CSV-only Storage**: No persistent database backend
5. **No Twilio Integration**: Part 3 optional feature not implemented

## Author

Hemant Godve  
IIT Bombay - CSE  

## License

MIT License - See LICENSE file

## Acknowledgments

- Loop Health for the internship assignment
- Hospital data from GIPSA network
- FastAPI documentation and community

---

**Last Updated**: November 19, 2025  
**Status**: Part 1 - Complete ✓
