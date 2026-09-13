# TerraWise Pakistan Backend API

FastAPI backend service for land analysis, Open-Meteo weather integration, Copernicus satellite data processing, and Groq LLM AI recommendations.

## Setup Instructions

1. Navigate to the backend directory:
   cd backend

2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate

3. Install requirements:
   pip install -r requirements.txt

4. Configure Environment Variables:
   Copy `.env.example` to `.env` and fill in API keys.

5. Run FastAPI server:
   uvicorn app.main:app --reload --port 8000

## API Endpoints

- **GET** `/` - Health Check Status.
- **POST** `/api/v1/analyze` - Main analysis endpoint accepting latitude, longitude, acres, polygon_geojson, and language.
