# TerraWise V1

An agricultural land intelligence and decision-support web application that turns satellite and weather data for a user-selected area into a plain-language summary.

---

## 1. Project Overview

TerraWise is a web application that lets a user pick a piece of agricultural land on a map and receive a structured, easy-to-read summary of that land's current vegetation and weather conditions.

The user does not need any technical or scientific background. They can:

- Search for a location.
- Draw the boundary of a field (as a polygon or a rectangle) directly on a satellite map.
- See the selected area calculated automatically, in acres.
- Request an analysis of that specific area.
- View the results as a simple dashboard, in English or Urdu.

TerraWise is built around one core principle, applied in this exact order for every request:

**Real Data → Deterministic Processing → Structured Conditions → AI Explanation**

In practice this means:

1. The backend retrieves real satellite data (Sentinel-2) and real weather data (Open-Meteo) for the selected area.
2. The backend performs fixed, rule-based calculations on that data (for example, turning a raw vegetation index into a category like "GOOD" or "LOW").
3. Only after these structured, calculated results exist does an AI model (Groq) step in.
4. The AI's only job is to explain the already-calculated results in plain language and suggest cautious next steps. It never generates the underlying numbers itself.

This separation matters: the scientific measurements always come from real data and fixed rules, never from the AI's imagination.

---

## 2. Problem Statement

Satellite imagery and weather data exist and are technically accessible, but they are not easy for an ordinary person to use directly:

- Raw satellite imagery requires specialized software and expertise to interpret.
- Vegetation and moisture indices (explained in Section 9) are meaningful to remote-sensing specialists but not self-explanatory to most people.
- Weather data on its own does not say anything about how a specific plot of land is doing.

TerraWise's purpose is to close this gap: it fetches this technical data for a specific, user-selected area and converts it into structured, understandable indicators and a short plain-language explanation.

---

## 3. Proposed Solution

TerraWise implements the following user flow, end to end:

```
Search for a location
    → Select or draw a land boundary on the map
    → The selected area is calculated automatically (in acres)
    → The user clicks "Analyze Area"
    → The backend retrieves weather data and satellite data for that area
    → The backend calculates vegetation and moisture indices (NDVI / NDMI)
    → The backend classifies these values and the weather values into categories
    → The backend applies a small set of combined rules (for example, possible moisture stress)
    → An AI model explains the structured results in plain language
    → The frontend displays everything on a results dashboard
```

---

## 4. Target Users

Based on the current scope of the project, TerraWise V1 is intended for:

- Farmers and landowners who want a simplified, remote view of a field's vegetation and weather conditions.
- Agriculture students and researchers who want to see satellite-derived indicators for a specific area.
- Anyone with a general interest in understanding the environmental condition of a piece of agricultural land.

TerraWise V1 is a decision-support tool, not a certified agronomic instrument. It is not positioned as a replacement for professional agronomic consultation, and it does not currently include the account management, historical tracking, or multi-farm features that a production agronomy platform would typically require.

---

## 5. Core Features

The following features are implemented and verified in the current codebase.

| Feature | Description |
|---|---|
| Location search | Search bar that geocodes a place name (city, town, etc.) using OpenStreetMap's Nominatim service and re-centers the map. |
| Satellite basemap | The map is rendered using Esri World Imagery satellite tiles. |
| Polygon / rectangle land selection | The user can draw an irregular polygon or a rectangle directly on the map to mark a field boundary, using the Leaflet Draw toolbar. |
| Editing and deletion | Drawn shapes can be edited (moved, resized) or deleted using the map's edit toolbar, without leaving stray selection handles on screen. |
| Automatic area calculation | The selected shape's area is calculated in acres, and its center point is calculated, both using Turf.js. |
| Analyze Area | A single action sends the selected area's coordinates, polygon, and acreage to the backend for analysis. |
| Real Sentinel-2 NDVI | Vegetation activity is calculated from actual Sentinel-2 satellite bands for the selected polygon (not a fixed or placeholder number). |
| Real Sentinel-2 NDMI | Vegetation/canopy moisture condition is calculated from actual Sentinel-2 satellite bands for the selected polygon. |
| Satellite observation date | The date of the actual satellite observation used for the analysis is returned and displayed. |
| Cloud cover / data-quality handling | The system estimates how much of the selected area was cloud-free in the satellite observation and factors this into its confidence rating. |
| Open-Meteo weather data | Current-day temperature, humidity, and recent rainfall are retrieved for the selected coordinates. |
| Heat-risk classification | Temperature is classified into LOW / MODERATE / HIGH heat risk. |
| Rainfall classification | Recent rainfall is classified into LOW / MODERATE / HIGH. |
| Possible moisture-stress signal | A combined rule flags a possible moisture-stress condition when moisture, heat, and rainfall indicators align (see Section 10). |
| Analysis confidence | A HIGH / MEDIUM / LOW rating reflecting how complete and reliable the underlying data was. |
| AI explanation | A short, plain-language interpretation of the structured results, generated by Groq. |
| Cautious recommendations | Two to three non-prescriptive suggested next steps (for example, "consider checking..."), generated alongside the explanation. |
| English / Urdu support | The AI explanation and recommendations are returned in either English or Urdu, based on a language selector in the interface. |
| Loading states | The interface shows a loading indicator while a location search or an analysis request is in progress. |
| Error handling | Failed requests (invalid input, unreachable backend, and so on) are shown as a clear error message rather than a silent failure. |
| Unavailable-data handling | If satellite or weather data cannot be retrieved for a request, the interface says so plainly instead of showing fabricated numbers. |
| Responsive layout | The interface is usable on desktop, tablet, and mobile screen widths. |

---

## 6. How TerraWise Works

1. The user opens the application and, optionally, searches for a location to move the map there.
2. The user draws a polygon or rectangle on the map to mark an agricultural area. The frontend immediately calculates the area (in acres) and its center point.
3. The user clicks **Analyze Area**. The frontend sends the selected coordinates, the polygon boundary, the calculated acreage, and the chosen language to the backend.
4. The backend validates the request (see Section 12) and then, independently:
   - Requests current weather data for the location from Open-Meteo.
   - Requests Sentinel-2 satellite statistics for the selected polygon from the Copernicus Data Space Ecosystem.
5. If satellite data is retrieved, the backend calculates NDVI and NDMI for the area (see Section 9) using the actual spectral bands, along with the observation date and an estimated cloud-cover percentage.
6. The backend classifies each raw value (NDVI, NDMI, temperature, rainfall) into a category using fixed, documented thresholds (see Section 10), and applies a small set of combined rules, such as flagging a possible moisture-stress condition.
7. The backend calculates an overall analysis confidence rating based on whether satellite and weather data were both available and how reliable the satellite observation was.
8. The backend sends only these already-calculated, structured facts (never raw imagery or an open-ended question) to the Groq AI model, which returns a short explanation and a small number of cautious recommendations, in the requested language.
9. The backend returns a single structured JSON response containing all of the above.
10. The frontend displays the results in a grouped dashboard: satellite insights, weather conditions, an analysis summary, the AI interpretation, and recommended next steps.

Simplified flow:

```
User
  |
  v
React Frontend (map, drawing tools, dashboard)
  |
  v
Selected Polygon / Coordinates / Acreage
  |
  v
FastAPI Backend (validation)
  |
  v
Open-Meteo (weather)  +  Copernicus Sentinel-2 (satellite)
  |
  v
Deterministic Analysis (NDVI/NDMI classification, heat/rainfall classification, combined rules, confidence)
  |
  v
Groq AI Explanation (plain-language summary and cautious recommendations)
  |
  v
Results Dashboard
```

---

## 7. System Architecture

### Frontend

Built with **React** and **Vite** (the build tool and development server), styled with **Tailwind CSS** (a utility-based styling framework).

| Technology | Role in TerraWise |
|---|---|
| React | Builds the interactive interface (search bar, map, results dashboard) as reusable components. |
| Vite | Runs the local development server and produces the optimized production build. |
| Tailwind CSS | Provides the visual styling (spacing, color, typography) directly in the component code. |
| Leaflet | Renders the interactive satellite map itself. |
| Leaflet Draw | Adds the polygon/rectangle drawing, editing, and deleting tools on top of the Leaflet map. |
| Turf.js | Performs the geographic calculations: the area of the drawn shape (converted to acres) and its center point. |

The frontend is also responsible for calling the OpenStreetMap Nominatim service directly (a free, public geocoding service) to turn a typed place name into map coordinates for the search feature.

### Backend

Built with **Python** and **FastAPI** (a web framework for building APIs), with **Pydantic** used for request and response data validation.

| Responsibility | Where it lives |
|---|---|
| API routing and request handling | `app/main.py` |
| Request/response data validation | `app/models.py` |
| Weather retrieval, satellite retrieval, classification rules, and AI explanation | `app/services.py` |
| Environment configuration (API keys, allowed origins) | `app/config.py` |

The backend is the only part of the system that talks to Open-Meteo, Copernicus/Sentinel Hub, and Groq. The frontend never calls these services directly (with the exception of the OpenStreetMap search noted above), and never sees any API keys.

---

## 8. Data Sources and External Services

### Sentinel-2 / Copernicus Data Space

TerraWise retrieves satellite data using the **Copernicus Data Space Ecosystem's Sentinel Hub Statistical API**. This is a service that returns statistics (such as an average value) calculated over a chosen area, rather than requiring the application to download and process a full satellite image.

How it works in TerraWise:

- The exact polygon the user drew is sent as the area of interest. If no polygon is available, a small area around the selected point is used instead.
- The request looks at Sentinel-2 imagery (Level-2A, meaning it is already atmospherically corrected) from the last 45 days.
- **NDVI** (Normalized Difference Vegetation Index) is calculated from the Red band (B04) and the Near-Infrared band (B08).
- **NDMI** (Normalized Difference Moisture Index) is calculated from the Near-Infrared band (B08) and the Short-Wave Infrared band (B11).
- Cloud and shadow pixels are excluded using Sentinel-2's own Scene Classification Layer before the statistics are calculated.
- The system automatically selects the most recent day, within the last 45 days, that has a sufficiently cloud-free observation over the selected area.
- The actual observation date and an estimated cloud-cover percentage are returned alongside the index values.
- If no usable observation exists (for example, due to persistent cloud cover, or if satellite access is not configured), TerraWise does not invent a value. It marks satellite data as unavailable and communicates this clearly in the interface, without exposing internal technical or configuration details to the user.

### Open-Meteo

TerraWise retrieves weather data from **Open-Meteo**, a free weather data API. Specifically, it retrieves, for the selected coordinates:

- Maximum temperature (in Celsius)
- Average relative humidity (as a percentage)
- Total precipitation (rainfall, in millimeters)

It is important to note that this is forecast/model-based weather data for the general location, similar to a weather app. It is **not** a physical weather sensor installed on the selected field.

If Open-Meteo does not respond successfully (for example, if it returns a "too many requests" or a temporary server error), the backend retries the request a couple of times with a short delay before giving up. If Open-Meteo still cannot be reached after that, and a **WeatherAPI.com** key is configured, TerraWise automatically falls back to WeatherAPI.com as a secondary weather provider, using the same daily maximum temperature, average humidity, and total rainfall fields so the meaning of each value stays consistent regardless of which provider answered. If neither provider can supply usable data, TerraWise marks weather data as unavailable rather than substituting a made-up value.

### Groq

**Groq** is the AI service used to generate the plain-language explanation and recommendations. Its role is intentionally narrow:

- It is only called after all satellite and weather data has been retrieved and classified.
- It receives a structured set of already-calculated facts (index values, categories, weather values, and whether each data source was actually available), not raw imagery or an open-ended question.
- Its output is a short explanation (a few sentences) and two to three cautious next-step suggestions.
- It is explicitly instructed not to invent measurements, and its guardrails are described in full in Section 11.
- If Groq is not configured, is unreachable, or returns something that cannot be parsed as expected, TerraWise falls back to a fixed, pre-written explanation that still accurately reflects which data sources were actually available for that request (see Section 17).

---

## 9. Satellite Indices

### NDVI (Normalized Difference Vegetation Index)

**What it measures:** the relative amount of active, healthy-looking green vegetation in the selected area, based on how strongly the surface reflects visible red light versus near-infrared light. Living, actively photosynthesizing plants reflect near-infrared light much more strongly than red light, which produces a higher NDVI value.

Conceptually:

```
NDVI = (Near-Infrared reflectance - Red reflectance) / (Near-Infrared reflectance + Red reflectance)
```

**What it can tell us:** a relative indication of how much active vegetation cover is present in the area at the time of the satellite observation.

**What it cannot tell us:** NDVI cannot identify the crop type, cannot diagnose disease or pest problems, and does not by itself confirm whether a crop is "healthy" in an agronomic sense. Bare soil, harvested land, fallow land, and newly planted land can all produce a low NDVI value for different reasons.

### NDMI (Normalized Difference Moisture Index)

**What it measures:** a relative indication of moisture content in vegetation and canopy, based on how the surface reflects near-infrared light versus short-wave infrared light.

Conceptually:

```
NDMI = (Near-Infrared reflectance - Short-Wave Infrared reflectance) / (Near-Infrared reflectance + Short-Wave Infrared reflectance)
```

**What it can tell us:** a relative signal that can help indicate whether vegetation in the area appears to be under more or less moisture stress compared to typical conditions.

**What it cannot tell us:** NDMI is not a direct or exact measurement of soil moisture percentage. It reflects conditions in vegetation and canopy as seen from space, not a ground-level soil moisture sensor reading.

---

## 10. Rule-Based Analysis

Before the AI ever sees any data, TerraWise converts every raw measurement into a category using fixed thresholds defined in the backend code. These thresholds are documented in the code as **general-purpose, V1 decision-support heuristics**, not universal, crop-specific agronomic standards. Actual appropriate thresholds vary by crop type, growth stage, season, and soil, which this V1 system does not account for.

**NDVI classification:**

| NDVI value | Category |
|---|---|
| Below 0.20 | VERY_LOW |
| 0.20 to below 0.35 | LOW |
| 0.35 to below 0.50 | MODERATE |
| 0.50 to below 0.65 | GOOD |
| 0.65 and above | VERY_GOOD |

**NDMI classification:**

| NDMI value | Category |
|---|---|
| Below 0.05 | VERY_LOW |
| 0.05 to below 0.15 | LOW |
| 0.15 to below 0.30 | MODERATE |
| 0.30 and above | GOOD |

**Heat risk (based on maximum temperature, °C):**

| Temperature | Category |
|---|---|
| Below 30°C | LOW |
| 30°C to below 38°C | MODERATE |
| 38°C and above | HIGH |

**Rainfall status (based on recent rainfall, mm):**

| Rainfall | Category |
|---|---|
| Below 2 mm | LOW |
| 2 mm to below 10 mm | MODERATE |
| 10 mm and above | HIGH |

**Possible moisture stress:** this combined flag is only calculated when NDMI, heat risk, and rainfall status are all available. It is set to true only when all three of the following are true at once: the NDMI category is VERY_LOW or LOW, the heat risk is HIGH, and the rainfall status is LOW. Otherwise it is false, or left unknown if any of the three inputs is missing.

**Analysis confidence:** this reflects data quality, not a scientific certainty score.

- **LOW** if either satellite data or weather data could not be retrieved at all.
- **MEDIUM** if both were retrieved, but the satellite observation's estimated cloud cover was above 40%.
- **HIGH** if both were retrieved and the satellite observation was reasonably cloud-free.

---

## 11. AI Role and Guardrails

The AI (Groq) is used strictly as an **explanation layer**. It operates on top of the already-calculated, structured results described above and does not perform any measurement or diagnosis itself.

**The AI is allowed to:**

- Summarize the structured indicators in plain language.
- Explain what the combination of results may suggest, cautiously.
- Provide two to three general, non-prescriptive next-step suggestions.

**The AI is explicitly instructed not to:**

- Invent or estimate NDVI, NDMI, rainfall, or any other measurement beyond what was actually calculated.
- Identify or guess a specific crop type.
- Diagnose a disease or pest.
- State exact soil moisture, soil nutrient (NPK), or fertilizer amounts.
- Prescribe exact irrigation quantities or a fertilizer dosage.
- Guarantee a yield outcome or make a definitive, final crop-health verdict.
- Describe a data source as available when it was not (see Section 17).

The system prompt instructs the AI to prefer cautious, neutral phrasing such as "conditions may indicate," "consider checking," "inspect," and "verify," rather than definitive statements like "your crop is stressed" or "you should irrigate now." This wording guidance, and all of the guardrails above, apply equally to the English and Urdu versions of the prompt.

---

## 12. API Contract

### Endpoint

```
POST /api/v1/analyze
Content-Type: application/json
```

A basic health-check endpoint is also available at `GET /`.

### Example Request

```json
{
  "latitude": 30.1575,
  "longitude": 71.5249,
  "acres": 12.5,
  "polygon_geojson": {
    "type": "Feature",
    "properties": {},
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [
          [71.5230, 30.1560],
          [71.5260, 30.1560],
          [71.5260, 30.1590],
          [71.5230, 30.1590],
          [71.5230, 30.1560]
        ]
      ]
    }
  },
  "language": "en"
}
```

Request field notes:

- `latitude` / `longitude`: required, standard geographic coordinates.
- `acres`: optional, defaults to `0`, must not be negative.
- `polygon_geojson`: optional. If provided, it must be a valid GeoJSON `Polygon` (either on its own or wrapped in a `Feature`), with a closed outer ring (the first and last coordinate pairs must match) of at least four points. If omitted, the analysis falls back to a small area around the given coordinates for the satellite lookup.
- `language`: `"en"` for English or `"ur"` for Urdu. Defaults to `"ur"` if omitted. Any other value is rejected.

Requests that fail validation (for example, a malformed or unclosed polygon, or an unsupported language) receive a `422 Unprocessable Entity` response with a plain-text `detail` message, and never a stack trace or internal error detail.

### Example Response (satellite and weather both available)

```json
{
  "ndvi": 0.612,
  "ndvi_status": "GOOD",
  "ndmi": 0.205,
  "ndmi_status": "MODERATE",
  "temperature_c": 34.6,
  "humidity_percent": 42,
  "recent_rainfall_mm": 3.4,
  "heat_risk": "MODERATE",
  "rainfall_status": "MODERATE",
  "possible_water_stress": false,
  "analysis_confidence": "HIGH",
  "satellite_available": true,
  "satellite_observation_date": "2026-09-10",
  "cloud_cover_percent": 8.5,
  "satellite_message": null,
  "weather_available": true,
  "weather_message": null,
  "ai_explanation": "The selected area shows relatively strong vegetation activity based on the current NDVI reading. Moisture conditions are moderate, and while temperatures are elevated, recent rainfall has been moderate. The combined indicators do not currently show a strong moisture-stress signal.",
  "recommendations": [
    "Continue monitoring vegetation and weather conditions over the coming days.",
    "Consider checking field moisture directly if temperatures remain elevated.",
    "Verify conditions on the ground before making any irrigation decisions."
  ]
}
```

### Example Response (satellite unavailable, weather available)

```json
{
  "ndvi": null,
  "ndvi_status": null,
  "ndmi": null,
  "ndmi_status": null,
  "temperature_c": 38.4,
  "humidity_percent": 51,
  "recent_rainfall_mm": 0.0,
  "heat_risk": "HIGH",
  "rainfall_status": "LOW",
  "possible_water_stress": null,
  "analysis_confidence": "LOW",
  "satellite_available": false,
  "satellite_observation_date": null,
  "cloud_cover_percent": null,
  "satellite_message": "No cloud-free Sentinel-2 observation was found for this area in the last 45 days.",
  "weather_available": true,
  "weather_message": null,
  "ai_explanation": "Weather indicators were retrieved successfully for the selected area, but satellite indicators are currently unavailable. The available weather data shows the current environmental conditions, while vegetation and satellite-derived moisture conditions cannot be assessed until satellite data becomes available.",
  "recommendations": [
    "Review the available weather conditions shown above.",
    "Check back later for satellite-based vegetation and moisture indicators.",
    "Consider a field visit to assess vegetation and moisture conditions directly in the meantime."
  ]
}
```

Notes on the response:

- Any value that could not be determined (because its data source was unavailable, or because a dependent calculation could not be made) is returned as `null` rather than a fabricated number.
- `satellite_available` and `weather_available` always indicate whether each external data source was successfully retrieved for this specific request.
- `satellite_message` and `weather_message` carry a short, internal explanation of why a source was unavailable; the current frontend deliberately shows the user a simple, fixed message instead of this internal text, so as not to expose configuration or service-level details.
- The full set of fields returned is defined in `backend/app/models.py` (`FarmAnalyzeResponse`), which is the authoritative source for the response shape.

---

## 13. Project Structure

```
TerraWise/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── MapContainer.jsx
│   │   │   ├── MapSearch.jsx
│   │   │   ├── ResultsDashboard.jsx
│   │   │   └── StatsCard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── .env.example
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── config.py
│   ├── .env.example
│   └── requirements.txt
├── .gitignore
└── README.md
```

(Generated folders such as `node_modules`, `venv`, and build output are omitted here; see Section 16 for where build output is generated.)

---

## 14. Environment Variables

Actual values must never be committed to the repository. Only the variable names are documented here.

### Backend (`backend/.env`)

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Authenticates requests to the Groq AI service for generating explanations. |
| `COPERNICUS_CLIENT_ID` | Client ID used to authenticate with the Copernicus Data Space Ecosystem for satellite data. |
| `COPERNICUS_CLIENT_SECRET` | Client secret used alongside the client ID for Copernicus authentication. |
| `WEATHERAPI_KEY` | Optional. Enables WeatherAPI.com as a secondary/fallback weather provider, used only if Open-Meteo (the primary provider) is unavailable. If left unset, TerraWise simply reports weather as unavailable when Open-Meteo fails, as before. |
| `ALLOWED_ORIGINS` | Comma-separated list of frontend URLs allowed to call this backend (CORS). If left empty, all origins are allowed, which is convenient for local development but should be restricted in a shared or production deployment. |
| `PORT` | Port the backend listens on (defaults to `8000`). |
| `HOST` | Host address the backend binds to (defaults to `0.0.0.0`). |

### Frontend (`frontend/.env`)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | The base URL of the backend API that the frontend should call (for example, `http://localhost:8000`). |

**Never commit real `.env` files or API keys/secrets to GitHub.** Only the `.env.example` files, which contain variable names without real values, should be committed.

---

## 15. Local Setup

### Backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt

# Create a .env file from the template, then fill in real values
cp .env.example .env

uvicorn app.main:app --reload
```

By default this runs the backend at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install

# Create a .env file from the template, then set the backend URL
cp .env.example .env

npm run dev
```

By default this runs the frontend development server at `http://localhost:5173`.

---

## 16. Production Build

**Frontend:** running

```bash
npm run build
```

from the `frontend` directory produces an optimized, static production build in `frontend/dist`. This is the folder that would be deployed to any static web host.

**Backend:** for a production-style run, the backend can be started with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The repository does not define or assume a specific hosting provider. Any environment capable of running a Python/FastAPI application and serving the static frontend build can be used.

---

## 17. Error and Fallback Handling

TerraWise is built to prefer an honest "unavailable" result over a fabricated one. Specifically:

- **Invalid polygon:** if the submitted polygon is not a valid, closed GeoJSON polygon with enough points, the request is rejected with a `422` response and a clear validation message, before any external services are called.
- **Unsupported language:** any `language` value other than `"en"` or `"ur"` is rejected with a `422` response.
- **Missing or unavailable satellite data:** if Copernicus credentials are not configured, the satellite service cannot be reached, or no sufficiently cloud-free Sentinel-2 observation exists for the area in the last 45 days, `satellite_available` is returned as `false`, and NDVI, NDMI, the observation date, and cloud cover are all returned as `null` rather than estimated values.
- **Weather failure:** if Open-Meteo cannot be reached or returns unusable data after its retries, and the optional WeatherAPI.com fallback (if configured) also cannot supply usable data, `weather_available` is returned as `false`, and temperature, humidity, and rainfall are returned as `null`.
- **Missing AI availability:** if the Groq API key is not configured, the service is unreachable, or its response cannot be parsed as expected, TerraWise falls back to a fixed, pre-written explanation and set of recommendations. Importantly, this fallback text is chosen based on which data sources were actually available for that request, so it never claims that satellite or weather data was assessed when it was not.
- **Partial analysis:** satellite and weather data are retrieved independently, so it is entirely possible for one to succeed while the other fails. TerraWise supports this combination cleanly and reflects it accurately in both the structured response and the AI explanation.
- **Unexpected server errors:** any unhandled error during analysis returns a generic `503 Service Unavailable` response with a safe, user-facing message, without exposing internal error details or stack traces.

---

## 18. System Limitations

- An internet connection is required; TerraWise has no offline mode.
- The system depends on external services (Copernicus/Sentinel Hub, Open-Meteo, optionally WeatherAPI.com as a weather fallback, and Groq); if the relevant ones are down, misconfigured, or rate-limited, the corresponding part of the analysis will be marked unavailable.
- Satellite results depend on actual satellite pass timing and cloud cover; a persistently cloudy area may have no usable observation for an extended period.
- NDVI and NDMI are indirect, relative indicators. They do not replace a physical, on-the-ground field inspection.
- NDVI does not prove or measure crop health directly; it reflects vegetation activity as seen from space.
- NDMI is not an exact soil moisture percentage; it reflects vegetation/canopy moisture as seen from space.
- TerraWise does not diagnose crop diseases or pests.
- TerraWise does not report exact soil nutrient (NPK) values.
- TerraWise does not prescribe exact fertilizer quantities.
- TerraWise does not prescribe exact irrigation quantities.
- TerraWise does not predict or guarantee crop yield.
- The current V1 has no user accounts, no database, and no saved-farm functionality; each analysis is a single, self-contained request with nothing stored afterward.

---

## 19. Out of Scope for V1

The following are not implemented in the current version:

- User authentication or accounts
- A database
- Saved farms or multiple stored locations
- Historical satellite or weather monitoring over time
- Automated alerts or notifications
- Disease or pest diagnosis
- Exact soil nutrient (NPK) reporting
- Exact irrigation quantity recommendations
- Fertilizer dosage prescriptions
- Yield prediction
- IoT sensor integration
- A native mobile application
- Offline mode
- Payments or subscriptions

---

## 20. Testing

There is currently no automated test suite (no unit or integration tests) in the repository. Testing during development has been done manually. The following are supported and can be manually verified:

- **Frontend build:** `npm run build` completes successfully and produces a working production build.
- **API request validation:** sending an invalid polygon, an unclosed polygon, or an unsupported language to `POST /api/v1/analyze` correctly returns a `422` response with a descriptive message.
- **English and Urdu responses:** the same request with `"language": "en"` versus `"language": "ur"` returns correctly translated explanation and recommendation text.
- **Polygon handling:** drawing, editing, and deleting a polygon or rectangle on the map correctly updates the calculated area and coordinates sent to the backend.
- **Satellite-unavailable state:** when Copernicus credentials are not configured (or no usable observation exists), the response correctly sets `satellite_available` to `false` with `null` index values, and the interface displays this clearly.
- **Weather availability:** the response correctly reflects whether Open-Meteo data was retrieved.
- **AI fallback:** when the Groq API key is not configured, the interface still receives a complete, sensible response using the fixed fallback text described in Section 17.
- **Responsive interface:** manual checks across desktop, tablet, and mobile widths to confirm the layout does not break.

---

## 21. Suggested Demo Flow

A short sequence suitable for a live demonstration:

1. Open TerraWise.
2. Search for a location (for example, a town or district name).
3. Draw a boundary around an agricultural-looking area on the satellite map.
4. Point out the automatically calculated area, shown in acres.
5. Click **Analyze Area**.
6. Once results load, point out the Sentinel-2-derived NDVI and NDMI values and their categories.
7. Show the weather conditions section (temperature, humidity, recent rainfall).
8. Briefly explain that these values are classified using fixed rules before anything is shown to the user.
9. Show the AI interpretation and the recommended next steps.
10. Toggle the language switch to Urdu and show that the explanation updates accordingly.
11. Close by noting that TerraWise is a decision-support tool: it does not replace a physical field visit or professional agronomic advice.

---

## 22. Future Scope / TerraWise V2

The following are potential directions for a future version. **None of these are implemented in V1**; they are listed here only as possible next steps.

- User accounts and authentication
- Saved farms and support for multiple stored locations per user
- Historical satellite and weather trends over time for a saved area
- Scheduled, recurring monitoring of a saved area
- Automated anomaly detection (for example, a sudden drop in vegetation activity)
- Alerts and notifications
- Richer, crop-specific context and thresholds
- Exportable reports
- Expanded multilingual support beyond English and Urdu
- Voice-based accessibility features

---

## 23. Key Takeaway

TerraWise makes satellite and weather data for a specific piece of land easier to understand, by combining real external data with fixed, transparent rules and a cautious AI-generated explanation. It is designed as a decision-support aid, not a replacement for agronomists, laboratory soil testing, or physical field inspection. Any observation it produces should be treated as one input among several when making real agricultural decisions.
