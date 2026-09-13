from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List


class FarmAnalyzeRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Center Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Center Longitude")
    acres: Optional[float] = Field(default=0.0, ge=0, description="Plot size in acres")
    polygon_geojson: Optional[Dict[str, Any]] = Field(default=None)
    language: Optional[str] = Field(default="ur", description="Language: 'en' or 'ur'")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        v = (v or "ur").strip().lower()
        if v not in ("en", "ur"):
            raise ValueError("language must be 'en' or 'ur'")
        return v

    @model_validator(mode="after")
    def validate_polygon(self):
        if self.polygon_geojson is None:
            return self

        geo = self.polygon_geojson
        if not isinstance(geo, dict):
            raise ValueError("polygon_geojson must be a GeoJSON object")

        # Accept either a bare Polygon geometry or a Feature wrapping one.
        geometry = geo
        if geo.get("type") == "Feature":
            geometry = geo.get("geometry")
            if not isinstance(geometry, dict):
                raise ValueError("polygon_geojson Feature is missing a geometry")

        if geometry.get("type") != "Polygon":
            raise ValueError("polygon_geojson geometry must be of type 'Polygon'")

        coordinates = geometry.get("coordinates")
        if not coordinates or not isinstance(coordinates, list) or len(coordinates) == 0:
            raise ValueError("polygon_geojson is missing coordinates")

        exterior_ring = coordinates[0]
        if not isinstance(exterior_ring, list) or len(exterior_ring) < 4:
            raise ValueError("polygon exterior ring must contain at least 4 positions")

        for point in exterior_ring:
            if not isinstance(point, list) or len(point) < 2:
                raise ValueError("polygon coordinates must be [lng, lat] pairs")

        if exterior_ring[0] != exterior_ring[-1]:
            raise ValueError("polygon exterior ring must be closed (first and last point equal)")

        return self


class FarmAnalyzeResponse(BaseModel):
    ndvi: Optional[float] = None
    ndvi_status: Optional[str] = None

    ndmi: Optional[float] = None
    ndmi_status: Optional[str] = None

    temperature_c: Optional[float] = None
    humidity_percent: Optional[int] = None
    recent_rainfall_mm: Optional[float] = None

    heat_risk: Optional[str] = None
    rainfall_status: Optional[str] = None
    possible_water_stress: Optional[bool] = None

    analysis_confidence: str

    satellite_available: bool
    satellite_observation_date: Optional[str] = None
    cloud_cover_percent: Optional[float] = None
    satellite_message: Optional[str] = None

    weather_available: bool
    weather_message: Optional[str] = None

    ai_explanation: str
    recommendations: List[str]
