from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import FarmAnalyzeRequest, FarmAnalyzeResponse
from app.services import process_farm_analysis

app = FastAPI(
    title="TerraWise Pakistan Backend API",
    description="Backend API providing satellite (Sentinel-2), weather, and AI-assisted field analysis.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Invalid request payload.")
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": message})


@app.get("/")
def read_root():
    return {"status": "online", "message": "TerraWise Pakistan API is active."}


@app.post("/api/v1/analyze", response_model=FarmAnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_farm(payload: FarmAnalyzeRequest):
    try:
        return process_farm_analysis(
            lat=payload.latitude,
            lng=payload.longitude,
            acres=payload.acres,
            polygon_geojson=payload.polygon_geojson,
            lang=payload.language,
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Analysis could not be completed. Please try again shortly."},
        )
