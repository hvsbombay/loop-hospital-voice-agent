"""Loop AI Hospital Network Voice Agent - Part 1
Backend server for voice-based hospital search using FastAPI
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
import json
from typing import List, Dict, Optional
import logging

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
