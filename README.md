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

## Testing

### Manual Testing Steps

1. **Start Backend**:
   ```bash
   python main.py
   ```

2. **Upload CSV Data**:
   ```bash
   curl -X POST -F "file=@hospitals.csv" http://localhost:8000/upload-csv
   ```

3. **Test Search Endpoints**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
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

## Known Limitations (Part 1)

1. **No Voice API Integration**: Mock responses only
2. **Simple String Matching**: Basic keyword search (not semantic)
3. **No Multi-turn Context**: Single query only
4. **No Error Detection**: Limited validation
5. **CSV Only**: No database backend

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
