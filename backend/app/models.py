from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FarmAnalyzeRequest(BaseModel):
    latitude: float = Field(..., description="Center Latitude")
    longitude: float = Field(..., description="Center Longitude")
    acres: Optional[float] = Field(default=0.0, description="Plot size in acres")
    polygon_geojson: Optional[Dict[str, Any]] = Field(default=None)
    language: Optional[str] = Field(default="ur", description="Language: 'en' or 'ur'")

class FarmAnalyzeResponse(BaseModel):
    ndvi: float
    ndvi_status: str
    ndmi: float
    ndmi_status: str
    temperature_c: float
    humidity_percent: int
    recent_rainfall_mm: float
    heat_risk: str
    possible_water_stress: bool
    analysis_confidence: str
    satellite_observation_date: str
    cloud_cover_percent: int
    ai_explanation: str
    recommendations: List[str]
