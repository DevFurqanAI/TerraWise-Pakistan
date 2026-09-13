from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.models import FarmAnalyzeRequest, FarmAnalyzeResponse
from app.services import process_farm_analysis

app = FastAPI(
    title="TerraWise Pakistan Backend API",
    description="Full Production-Ready Backend Server with Live Weather, Copernicus, and AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "TerraWise Pakistan Complete API is active!"}

@app.post("/api/v1/analyze", response_model=FarmAnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_farm(payload: FarmAnalyzeRequest):
    try:
        data = process_farm_analysis(
            lat=payload.latitude,
            lng=payload.longitude,
            lang=payload.language
        )
        return data
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Analysis execution failed: {str(e)}"}
        )
