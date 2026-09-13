import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests
from groq import Groq

from app.config import settings

logger = logging.getLogger("terrawise.services")

groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

COPERNICUS_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
COPERNICUS_STATS_URL = "https://sh.dataspace.copernicus.eu/api/v1/statistics"

# ---------------------------------------------------------------------------
# V1 heuristic thresholds.
#
# These are general-purpose, crop-agnostic heuristics used only to bucket raw
# NDVI/NDMI/weather values into human-readable bands for the dashboard and the
# AI explanation. They are NOT universal agronomic diagnostic thresholds -
# actual thresholds vary heavily by crop type, growth stage, season and soil.
# Treat all outputs as decision-support signals, not lab-grade diagnostics.
# ---------------------------------------------------------------------------
NDVI_THRESHOLDS = [
    (0.20, "VERY_LOW"),
    (0.35, "LOW"),
    (0.50, "MODERATE"),
    (0.65, "GOOD"),
]
NDVI_MAX_LABEL = "VERY_GOOD"

NDMI_THRESHOLDS = [
    (0.05, "VERY_LOW"),
    (0.15, "LOW"),
    (0.30, "MODERATE"),
]
NDMI_MAX_LABEL = "GOOD"

HEAT_THRESHOLDS = [
    (30.0, "LOW"),
    (38.0, "MODERATE"),
]
HEAT_MAX_LABEL = "HIGH"

RAINFALL_THRESHOLDS = [
    (2.0, "LOW"),
    (10.0, "MODERATE"),
]
RAINFALL_MAX_LABEL = "HIGH"


def _bucket(value: float, thresholds, max_label: str) -> str:
    for limit, label in thresholds:
        if value < limit:
            return label
    return max_label


def classify_ndvi(ndvi: float) -> str:
    return _bucket(ndvi, NDVI_THRESHOLDS, NDVI_MAX_LABEL)


def classify_ndmi(ndmi: float) -> str:
    return _bucket(ndmi, NDMI_THRESHOLDS, NDMI_MAX_LABEL)


def classify_heat(temp_c: float) -> str:
    return _bucket(temp_c, HEAT_THRESHOLDS, HEAT_MAX_LABEL)


def classify_rainfall(rainfall_mm: float) -> str:
    return _bucket(rainfall_mm, RAINFALL_THRESHOLDS, RAINFALL_MAX_LABEL)


def _extract_polygon_geometry(polygon_geojson: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not polygon_geojson:
        return None
    if polygon_geojson.get("type") == "Feature":
        return polygon_geojson.get("geometry")
    return polygon_geojson


def _fallback_bbox_polygon(lat: float, lng: float, delta: float = 0.001) -> Dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng - delta, lat - delta],
            [lng + delta, lat - delta],
            [lng + delta, lat + delta],
            [lng - delta, lat + delta],
            [lng - delta, lat - delta],
        ]],
    }


def get_copernicus_token() -> Optional[str]:
    if not settings.COPERNICUS_CLIENT_ID or not settings.COPERNICUS_CLIENT_SECRET:
        return None
    try:
        data = {
            "client_id": settings.COPERNICUS_CLIENT_ID,
            "client_secret": settings.COPERNICUS_CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        res = requests.post(COPERNICUS_TOKEN_URL, data=data, timeout=8)
        if res.status_code == 200:
            return res.json().get("access_token")
    except requests.RequestException:
        pass
    return None


NDVI_NDMI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "B11", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "ndmi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}

function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 1e-6);
  let ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11 + 1e-6);
  // SCL cloud/shadow classes: 3 cloud shadow, 8/9 cloud medium/high prob, 10 thin cirrus
  let cloudy = [3, 8, 9, 10].includes(sample.SCL) ? 0 : 1;
  let valid = sample.dataMask * cloudy;
  return {
    ndvi: [ndvi],
    ndmi: [ndmi],
    dataMask: [valid]
  };
}
"""


def fetch_sentinel2_indices(polygon_geometry: Dict[str, Any], token: str) -> Dict[str, Any]:
    """
    Query the Copernicus Data Space Sentinel Hub Statistical API for polygon-level
    NDVI/NDMI statistics, avoiding a full raster download.

    Returns a dict with satellite_available + (on success) ndvi, ndmi,
    satellite_observation_date, cloud_cover_percent.
    """
    now = datetime.now(timezone.utc)
    time_from = (now - timedelta(days=45)).strftime("%Y-%m-%dT00:00:00Z")
    time_to = now.strftime("%Y-%m-%dT23:59:59Z")

    request_body = {
        "input": {
            "bounds": {
                "geometry": polygon_geometry,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {"from": time_from, "to": time_to},
                    "maxCloudCoverage": 80,
                },
            }],
        },
        "aggregation": {
            "timeRange": {"from": time_from, "to": time_to},
            "aggregationInterval": {"of": "P1D"},
            "evalscript": NDVI_NDMI_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
    }

    try:
        res = requests.post(
            COPERNICUS_STATS_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=request_body,
            timeout=25,
        )
    except requests.RequestException as exc:
        return {"satellite_available": False, "satellite_message": f"Satellite service request failed: {exc}"}

    if res.status_code != 200:
        return {
            "satellite_available": False,
            "satellite_message": f"Satellite service returned HTTP {res.status_code}.",
        }

    try:
        payload = res.json()
        intervals = payload.get("data", [])
    except (ValueError, KeyError):
        return {"satellite_available": False, "satellite_message": "Satellite service returned an unreadable response."}

    best_candidate = None
    for entry in intervals:
        outputs = entry.get("outputs", {})
        ndvi_stats = outputs.get("ndvi", {}).get("bands", {}).get("B0", {}).get("stats")
        ndmi_stats = outputs.get("ndmi", {}).get("bands", {}).get("B0", {}).get("stats")
        if not ndvi_stats:
            continue

        sample_count = ndvi_stats.get("sampleCount", 0)
        nodata_count = ndvi_stats.get("noDataCount", 0)
        valid_count = sample_count - nodata_count
        if sample_count <= 0 or valid_count <= 0:
            continue

        valid_fraction = valid_count / sample_count
        if valid_fraction < 0.15:
            continue  # too cloud-contaminated to be useful

        observation_date = entry.get("interval", {}).get("from", "")[:10]
        candidate = {
            "date": observation_date,
            "ndvi": ndvi_stats.get("mean"),
            "ndmi": (ndmi_stats or {}).get("mean"),
            "valid_fraction": valid_fraction,
            "cloud_cover_percent": round((1 - valid_fraction) * 100, 1),
        }

        # Prefer the most recent date with a usable observation.
        if best_candidate is None or candidate["date"] > best_candidate["date"]:
            best_candidate = candidate

    if best_candidate is None or best_candidate["ndvi"] is None:
        return {
            "satellite_available": False,
            "satellite_message": "No cloud-free Sentinel-2 observation was found for this area in the last 45 days.",
        }

    return {
        "satellite_available": True,
        "ndvi": round(float(best_candidate["ndvi"]), 3),
        "ndmi": round(float(best_candidate["ndmi"]), 3) if best_candidate["ndmi"] is not None else None,
        "satellite_observation_date": best_candidate["date"],
        "cloud_cover_percent": best_candidate["cloud_cover_percent"],
    }


def get_satellite_data(polygon_geojson: Optional[Dict[str, Any]], lat: float, lng: float) -> Dict[str, Any]:
    token = get_copernicus_token()
    if not token:
        return {
            "satellite_available": False,
            "satellite_message": "Satellite data unavailable: Copernicus credentials are not configured.",
        }

    geometry = _extract_polygon_geometry(polygon_geojson) or _fallback_bbox_polygon(lat, lng)
    return fetch_sentinel2_indices(geometry, token)


WEATHER_MAX_ATTEMPTS = 3  # 1 initial attempt + 2 retries
WEATHER_BACKOFF_SECONDS = [1, 2]  # wait before retry 1, then before retry 2


def _is_retryable_weather_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code < 600


def _fetch_open_meteo(lat: float, lng: float) -> Dict[str, Any]:
    """Primary weather provider. Daily max temperature, mean humidity, and total
    precipitation for the selected coordinates, with short retry-on-429/5xx handling."""
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lng}&"
        f"daily=temperature_2m_max,precipitation_sum,relative_humidity_2m_mean&"
        f"timezone=auto&forecast_days=1&past_days=1"
    )

    res = None
    for attempt in range(WEATHER_MAX_ATTEMPTS):
        try:
            res = requests.get(weather_url, timeout=6)
        except requests.RequestException as exc:
            logger.warning("Open-Meteo request failed: %s", exc)
            return {"weather_available": False, "weather_message": f"Weather service request failed: {exc}"}

        if res.status_code == 200 or not _is_retryable_weather_status(res.status_code):
            break

        is_last_attempt = attempt == WEATHER_MAX_ATTEMPTS - 1
        logger.warning(
            "Open-Meteo returned HTTP %d (attempt %d/%d)%s",
            res.status_code,
            attempt + 1,
            WEATHER_MAX_ATTEMPTS,
            "" if is_last_attempt else ", retrying",
        )
        if is_last_attempt:
            break

        wait_seconds = WEATHER_BACKOFF_SECONDS[attempt]
        retry_after = res.headers.get("Retry-After")
        if retry_after:
            try:
                wait_seconds = max(wait_seconds, float(retry_after))
            except ValueError:
                pass
        time.sleep(wait_seconds)

    if res.status_code != 200:
        return {"weather_available": False, "weather_message": f"Weather service returned HTTP {res.status_code}."}

    try:
        daily = res.json().get("daily", {})
        temps = daily.get("temperature_2m_max", [])
        hums = daily.get("relative_humidity_2m_mean", [])
        rains = daily.get("precipitation_sum", [])

        if not temps or temps[-1] is None:
            return {"weather_available": False, "weather_message": "Weather service returned no usable data for this location."}

        return {
            "weather_available": True,
            "temperature_c": float(temps[-1]),
            "humidity_percent": int(hums[-1]) if hums and hums[-1] is not None else None,
            "recent_rainfall_mm": float(rains[-1]) if rains and rains[-1] is not None else None,
        }
    except (ValueError, KeyError, IndexError):
        return {"weather_available": False, "weather_message": "Weather service returned an unreadable response."}


WEATHERAPI_FORECAST_URL = "https://api.weatherapi.com/v1/forecast.json"
WEATHERAPI_TIMEOUT_SECONDS = 6


def _fetch_weatherapi_fallback(lat: float, lng: float) -> Dict[str, Any]:
    """Secondary weather provider, used only when Open-Meteo is unavailable.

    Uses forecast.json with days=1 (not current.json) so temperature/humidity/rainfall
    are daily aggregates (max temperature, average humidity, total precipitation) -
    matching the semantics of Open-Meteo's temperature_2m_max / relative_humidity_2m_mean /
    precipitation_sum, rather than a single instantaneous reading.
    """
    try:
        res = requests.get(
            WEATHERAPI_FORECAST_URL,
            params={
                "key": settings.WEATHERAPI_KEY,
                "q": f"{lat},{lng}",
                "days": 1,
                "aqi": "no",
                "alerts": "no",
            },
            timeout=WEATHERAPI_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning("WeatherAPI fallback request failed: %s", exc)
        return {"weather_available": False, "weather_message": "Weather service request failed."}

    if res.status_code != 200:
        logger.warning("WeatherAPI fallback returned HTTP %d", res.status_code)
        return {"weather_available": False, "weather_message": "Weather service returned no usable data for this location."}

    try:
        forecast_days = res.json().get("forecast", {}).get("forecastday", [])
        if not forecast_days:
            return {"weather_available": False, "weather_message": "Weather service returned no usable data for this location."}

        day = forecast_days[0].get("day", {})
        max_temp = day.get("maxtemp_c")
        avg_humidity = day.get("avghumidity")
        total_precip = day.get("totalprecip_mm")

        if max_temp is None:
            return {"weather_available": False, "weather_message": "Weather service returned no usable data for this location."}

        return {
            "weather_available": True,
            "temperature_c": float(max_temp),
            "humidity_percent": int(avg_humidity) if avg_humidity is not None else None,
            "recent_rainfall_mm": float(total_precip) if total_precip is not None else None,
        }
    except (ValueError, KeyError, IndexError):
        return {"weather_available": False, "weather_message": "Weather service returned an unreadable response."}


def get_weather_data(lat: float, lng: float) -> Dict[str, Any]:
    primary_result = _fetch_open_meteo(lat, lng)
    if primary_result.get("weather_available"):
        logger.info("Weather data obtained from provider=open-meteo")
        return primary_result

    if not settings.WEATHERAPI_KEY:
        return primary_result

    logger.warning("Open-Meteo unavailable, attempting WeatherAPI fallback")
    fallback_result = _fetch_weatherapi_fallback(lat, lng)
    if fallback_result.get("weather_available"):
        logger.info("Weather data obtained from provider=weatherapi")
        return fallback_result

    logger.warning("WeatherAPI fallback also unavailable")
    return primary_result


def compute_confidence(satellite_available: bool, weather_available: bool, cloud_cover_percent: Optional[float]) -> str:
    if not satellite_available or not weather_available:
        return "LOW"
    if cloud_cover_percent is not None and cloud_cover_percent > 40:
        return "MEDIUM"
    return "HIGH"


# ---------------------------------------------------------------------------
# ASCII-safe text sanitization for AI-generated text only.
#
# Groq output can include "smart" Unicode punctuation (en/em dashes, curly
# quotes, non-breaking or narrow no-break spaces, ellipsis characters). These
# render fine in UTF-8-aware terminals but show up as mojibake (e.g. "38.4â¯Â°C")
# in some Windows consoles / codepages. We normalize them to plain ASCII
# equivalents. This does not touch any numeric/satellite/weather/rule values,
# only the free-text ai_explanation/recommendations strings.
# ---------------------------------------------------------------------------
_UNICODE_PUNCTUATION_MAP = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-",
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "…": "...",
    " ": " ", " ": " ", " ": " ", " ": " ", "⁠": "", "﻿": "",
    "•": "-", "·": "-",
}

PLAIN_TEXT_INSTRUCTION = (
    "Formatting rule: use only plain ASCII punctuation - a regular hyphen (-), regular spaces, "
    "straight quotes, and the degree symbol only if directly followed by C with a plain space "
    "(e.g. \"38.4 C\"). Do not use en dashes, em dashes, curly/smart quotes, ellipsis characters, "
    "non-breaking spaces, or narrow no-break spaces."
)


def sanitize_ai_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    for bad_char, replacement in _UNICODE_PUNCTUATION_MAP.items():
        text = text.replace(bad_char, replacement)
    return text


def sanitize_ai_result(ai_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ai_explanation": sanitize_ai_text(ai_result.get("ai_explanation", "")),
        "recommendations": [sanitize_ai_text(rec) for rec in ai_result.get("recommendations", [])],
    }


def build_ai_prompt(lang: str, facts: Dict[str, Any]) -> str:
    facts_json = json.dumps(facts, ensure_ascii=False, indent=2)

    if lang == "en":
        return f"""You explain remote-sensing and weather indicators for a selected agricultural area. You are an
explanation layer only - you interpret the structured facts below, you do not diagnose or measure anything yourself.

You must ONLY use the structured facts provided below. Never invent or estimate NDVI, NDMI, rainfall, soil
moisture, crop type, disease, pests, soil NPK values, fertilizer dosage, irrigation quantities, or yield beyond
what is given.

Strict guardrails - do not do any of the following:
- Do not identify or guess a specific crop type.
- Do not diagnose a disease or pest.
- Do not state exact soil moisture, NPK, or fertilizer amounts.
- Do not prescribe exact irrigation quantities or a fertilizer dosage.
- Do not guarantee a yield outcome or make a definitive crop-health verdict.

Wording guidance - prefer neutral, cautious phrasing:
- Say "relatively strong vegetation activity" or "higher vegetation activity" instead of "healthy vegetation".
- Say "conditions may indicate increasing moisture stress" instead of "the crops may be approaching water stress".
- Use terms like "vegetation activity", "moisture condition", "possible moisture stress", "conditions may indicate...",
  "consider checking...", "verify...", "inspect..." rather than "healthy crop", "unhealthy crop", "your crop is
  stressed", "the field needs irrigation", or "you should irrigate now".
- The dashboard already shows the exact numbers - interpret them, don't just restate every value.

Data availability: check the "satellite_available" and "weather_available" fields in the structured facts before
writing anything. If a source is unavailable (false), its fields will be null - never describe or imply a value
for it. If only weather is available, say so and explain that vegetation/moisture indicators cannot be assessed
until satellite data is available. If only satellite is available, say so and explain that current weather
conditions cannot be assessed until weather data is available. If neither is available, clearly state that a full
analysis could not be completed. Recommendations must never refer to an unavailable measurement as if it were known.

{PLAIN_TEXT_INSTRUCTION}

Structured facts:
{facts_json}

Return STRICTLY valid JSON with this shape:
{{
  "ai_explanation": "2-4 concise sentences interpreting the most important signals (vegetation activity, moisture, heat/rainfall context, and whether a moisture-stress signal is present) in plain, non-technical language.",
  "recommendations": ["2-3 cautious, actionable recommendations - no exact quantities, dosages, or diagnoses"]
}}"""

    return f"""آپ منتخب زرعی رقبے کے سیٹلائٹ اور موسمی اشاریوں کی وضاحت کرتے ہیں۔ آپ صرف ایک وضاحتی تہہ ہیں - آپ نیچے
دیے گئے ساختہ حقائق کی تشریح کرتے ہیں، خود کوئی پیمائش یا تشخیص نہیں کرتے۔

آپ کو صرف نیچے دیے گئے ساختہ حقائق استعمال کرنے ہیں۔ NDVI، NDMI، بارش، مٹی کی نمی، فصل کی قسم، بیماری، کیڑے،
مٹی کے NPK اعداد، کھاد کی مقدار، آبپاشی کی مقدار، یا پیداوار ہرگز خود سے نہ بنائیں۔

سخت حدود:
- کسی مخصوص فصل کی قسم کی شناخت یا اندازہ نہ لگائیں۔
- کسی بیماری یا کیڑے کی تشخیص نہ کریں۔
- مٹی کی نمی، NPK، یا کھاد کی صحیح مقدار نہ بتائیں۔
- آبپاشی کی صحیح مقدار یا کھاد کی خوراک تجویز نہ کریں۔
- پیداوار کی ضمانت یا فصل کی صحت کا حتمی فیصلہ نہ دیں۔

الفاظ کا انتخاب - محتاط اور غیر جانبدار زبان استعمال کریں:
"نباتاتی سرگرمی زیادہ ہے" جیسے الفاظ استعمال کریں، "فصل صحت مند ہے" کہنے کے بجائے۔ "حالات نمی کے دباؤ کی طرف اشارہ کر
سکتے ہیں" کہیں، "فصل پانی کی کمی کا شکار ہو رہی ہے" کہنے کے بجائے۔ "ظاہر کر سکتا ہے"، "معائنہ کرنے پر غور کریں"،
"چیک کریں"، "تصدیق کریں" جیسے الفاظ استعمال کریں۔ ڈیش بورڈ پر تمام اعداد پہلے سے موجود ہیں - انہیں دہرانے کے بجائے
ان کی مختصر تشریح کریں۔

ڈیٹا کی دستیابی: لکھنے سے پہلے ساختہ حقائق میں "satellite_available" اور "weather_available" کی قدریں چیک کریں۔
اگر کوئی ذریعہ دستیاب نہیں (false) تو اس کی قدریں null ہوں گی - ایسی صورت میں اس کے بارے میں کوئی قدر بیان یا فرض نہ
کریں۔ اگر صرف موسمی ڈیٹا دستیاب ہے تو یہ واضح کریں اور بتائیں کہ نباتاتی و نمی کے اشاریوں کا اندازہ سیٹلائٹ ڈیٹا کے
بغیر نہیں لگایا جا سکتا۔ اگر صرف سیٹلائٹ ڈیٹا دستیاب ہے تو یہ واضح کریں اور بتائیں کہ موجودہ موسمی حالات کا اندازہ
موسمی ڈیٹا کے بغیر نہیں لگایا جا سکتا۔ اگر دونوں دستیاب نہیں تو واضح طور پر کہیں کہ مکمل تجزیہ ممکن نہیں۔ تجاویز میں
کبھی بھی کسی غیر دستیاب پیمائش کا یوں ذکر نہ کریں جیسے وہ معلوم ہو۔

فارمیٹنگ اصول: صرف سادہ ASCII اعداد اور عام ہائیفن (-) استعمال کریں جہاں انگریزی نمبر یا یونٹ لکھیں
(مثلا "38.4 C")۔ خاص یونیکوڈ ڈیش، خمدار حوالہ جاتی علامات، یا نان بریکنگ اسپیس استعمال نہ کریں۔

ساختہ حقائق:
{facts_json}

صرف اور صرف درست JSON فارمیٹ میں جواب دیں:
{{
  "ai_explanation": "نباتاتی سرگرمی، نمی، موسمی حالات، اور ممکنہ نمی کے دباؤ کے بارے میں 2-4 مختصر اور سادہ جملے۔",
  "recommendations": ["2-3 محتاط اور عملی تجاویز - بغیر صحیح مقدار، خوراک، یا تشخیص کے"]
}}"""


def default_ai_response(lang: str, satellite_available: bool, weather_available: bool) -> Dict[str, Any]:
    """
    Static fallback text used when Groq is unavailable or its response could not be parsed.
    Wording must always match what data actually came back - never imply a measurement
    is known when its source (satellite or weather) was unavailable for this request.
    """
    if lang == "en":
        if satellite_available and weather_available:
            return {
                "ai_explanation": "Structured vegetation and weather indicators were calculated for this area, but "
                                   "an AI-generated interpretation is not available right now. The measurements "
                                   "above reflect the current satellite and weather data for the selected area.",
                "recommendations": [
                    "Inspect the selected area for visible signs of moisture stress.",
                    "Consider checking field moisture and irrigation coverage if low rainfall continues.",
                    "Continue monitoring vegetation and weather conditions over the coming days.",
                ],
            }
        if weather_available and not satellite_available:
            return {
                "ai_explanation": "Weather indicators were retrieved successfully for the selected area, but "
                                   "satellite indicators are currently unavailable. The available weather data "
                                   "shows the current environmental conditions, while vegetation and "
                                   "satellite-derived moisture conditions cannot be assessed until satellite data "
                                   "becomes available.",
                "recommendations": [
                    "Review the available weather conditions shown above.",
                    "Check back later for satellite-based vegetation and moisture indicators.",
                    "Consider a field visit to assess vegetation and moisture conditions directly in the meantime.",
                ],
            }
        if satellite_available and not weather_available:
            return {
                "ai_explanation": "Satellite indicators were retrieved successfully for the selected area, but "
                                   "weather indicators are currently unavailable. The available satellite data "
                                   "shows vegetation and moisture conditions, while current temperature, humidity, "
                                   "and rainfall cannot be assessed until weather data becomes available.",
                "recommendations": [
                    "Review the available vegetation and moisture indicators shown above.",
                    "Check back later for current weather conditions for this area.",
                    "Consider a field visit to verify current temperature and moisture conditions in the meantime.",
                ],
            }
        return {
            "ai_explanation": "Neither satellite nor weather data could be retrieved for the selected area, so a "
                               "full analysis is not currently available.",
            "recommendations": [
                "Try the analysis again later once satellite and weather data sources are reachable.",
                "Consider verifying the selected location or trying a nearby area.",
                "In the meantime, consider a field visit to assess current conditions directly.",
            ],
        }

    if satellite_available and weather_available:
        return {
            "ai_explanation": "اس رقبے کے لیے نباتاتی اور موسمی اشاریے حاصل کر لیے گئے ہیں، لیکن اس وقت AI کی تفصیلی "
                               "تشریح دستیاب نہیں۔ اوپر دی گئی اقدار موجودہ سیٹلائٹ اور موسمی ڈیٹا کی عکاسی کرتی ہیں۔",
            "recommendations": [
                "منتخب رقبے میں نمی کے دباؤ کی ظاہری علامات کے لیے معائنہ کریں۔",
                "اگر بارش کم ہو رہی ہے تو زمین کی نمی اور آبپاشی کی صورتحال چیک کرنے پر غور کریں۔",
                "اگلے چند دنوں تک نباتات اور موسمی حالات کی نگرانی جاری رکھیں۔",
            ],
        }
    if weather_available and not satellite_available:
        return {
            "ai_explanation": "اس رقبے کے لیے موسمی اشاریے کامیابی سے حاصل کر لیے گئے ہیں، لیکن سیٹلائٹ اشاریے اس "
                               "وقت دستیاب نہیں۔ موجودہ موسمی ڈیٹا ماحولیاتی حالات ظاہر کرتا ہے، جبکہ نباتاتی سرگرمی "
                               "اور سیٹلائٹ سے حاصل ہونے والی نمی کی صورتحال کا اندازہ سیٹلائٹ ڈیٹا دستیاب ہونے تک "
                               "نہیں لگایا جا سکتا۔",
            "recommendations": [
                "اوپر دی گئی موسمی صورتحال کا جائزہ لیں۔",
                "سیٹلائٹ پر مبنی نباتاتی اور نمی کے اشاریوں کے لیے بعد میں دوبارہ چیک کریں۔",
                "اس دوران نباتات اور نمی کی صورتحال جانچنے کے لیے کھیت کا معائنہ کرنے پر غور کریں۔",
            ],
        }
    if satellite_available and not weather_available:
        return {
            "ai_explanation": "اس رقبے کے لیے سیٹلائٹ اشاریے کامیابی سے حاصل کر لیے گئے ہیں، لیکن موسمی اشاریے اس "
                               "وقت دستیاب نہیں۔ موجودہ سیٹلائٹ ڈیٹا نباتاتی سرگرمی اور نمی کی صورتحال ظاہر کرتا ہے، "
                               "جبکہ موجودہ درجہ حرارت، نمی اور بارش کا اندازہ موسمی ڈیٹا دستیاب ہونے تک نہیں لگایا "
                               "جا سکتا۔",
            "recommendations": [
                "اوپر دی گئی نباتاتی اور نمی کی صورتحال کا جائزہ لیں۔",
                "اس رقبے کے موجودہ موسمی حالات کے لیے بعد میں دوبارہ چیک کریں۔",
                "اس دوران موجودہ درجہ حرارت اور نمی کی تصدیق کے لیے کھیت کا معائنہ کرنے پر غور کریں۔",
            ],
        }
    return {
        "ai_explanation": "اس منتخب رقبے کے لیے نہ سیٹلائٹ اور نہ ہی موسمی ڈیٹا حاصل کیا جا سکا، اس لیے مکمل تجزیہ "
                           "اس وقت دستیاب نہیں۔",
        "recommendations": [
            "سیٹلائٹ اور موسمی ڈیٹا دستیاب ہونے کے بعد دوبارہ کوشش کریں۔",
            "منتخب مقام کی تصدیق کریں یا قریبی رقبے کو آزمائیں۔",
            "اس دوران موجودہ حالات جانچنے کے لیے کھیت کا معائنہ کرنے پر غور کریں۔",
        ],
    }


def get_ai_explanation(lang: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    satellite_available = bool(facts.get("satellite_available", False))
    weather_available = bool(facts.get("weather_available", False))
    fallback = sanitize_ai_result(default_ai_response(lang, satellite_available, weather_available))
    if not groq_client:
        return fallback

    prompt = build_ai_prompt(lang, facts)
    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        parsed = json.loads(content.strip())
        if "ai_explanation" in parsed and "recommendations" in parsed:
            return sanitize_ai_result(
                {"ai_explanation": parsed["ai_explanation"], "recommendations": parsed["recommendations"]}
            )
    except Exception:
        pass

    return fallback


def process_farm_analysis(
    lat: float,
    lng: float,
    acres: Optional[float],
    polygon_geojson: Optional[Dict[str, Any]],
    lang: str,
) -> Dict[str, Any]:
    lang = (lang or "ur").strip().lower()

    weather = get_weather_data(lat, lng)
    satellite = get_satellite_data(polygon_geojson, lat, lng)

    ndvi = satellite.get("ndvi")
    ndmi = satellite.get("ndmi")
    ndvi_status = classify_ndvi(ndvi) if ndvi is not None else None
    ndmi_status = classify_ndmi(ndmi) if ndmi is not None else None

    temp_c = weather.get("temperature_c")
    humidity = weather.get("humidity_percent")
    rainfall = weather.get("recent_rainfall_mm")
    heat_risk = classify_heat(temp_c) if temp_c is not None else None
    rainfall_status = classify_rainfall(rainfall) if rainfall is not None else None

    possible_water_stress = None
    if ndmi_status is not None and heat_risk is not None and rainfall_status is not None:
        possible_water_stress = bool(
            ndmi_status in ("VERY_LOW", "LOW") and heat_risk == "HIGH" and rainfall_status == "LOW"
        )

    confidence = compute_confidence(
        satellite.get("satellite_available", False),
        weather.get("weather_available", False),
        satellite.get("cloud_cover_percent"),
    )

    facts = {
        "acres": acres,
        "ndvi": ndvi,
        "ndvi_status": ndvi_status,
        "ndmi": ndmi,
        "ndmi_status": ndmi_status,
        "temperature_c": temp_c,
        "humidity_percent": humidity,
        "recent_rainfall_mm": rainfall,
        "heat_risk": heat_risk,
        "rainfall_status": rainfall_status,
        "possible_water_stress": possible_water_stress,
        "analysis_confidence": confidence,
        "satellite_observation_date": satellite.get("satellite_observation_date"),
        "cloud_cover_percent": satellite.get("cloud_cover_percent"),
        "satellite_available": satellite.get("satellite_available", False),
        "weather_available": weather.get("weather_available", False),
    }

    ai_result = get_ai_explanation(lang, facts)

    return {
        "ndvi": ndvi,
        "ndvi_status": ndvi_status,
        "ndmi": ndmi,
        "ndmi_status": ndmi_status,
        "temperature_c": temp_c,
        "humidity_percent": humidity,
        "recent_rainfall_mm": rainfall,
        "heat_risk": heat_risk,
        "rainfall_status": rainfall_status,
        "possible_water_stress": possible_water_stress,
        "analysis_confidence": confidence,
        "satellite_available": satellite.get("satellite_available", False),
        "satellite_observation_date": satellite.get("satellite_observation_date"),
        "cloud_cover_percent": satellite.get("cloud_cover_percent"),
        "satellite_message": satellite.get("satellite_message"),
        "weather_available": weather.get("weather_available", False),
        "weather_message": weather.get("weather_message"),
        "ai_explanation": ai_result["ai_explanation"],
        "recommendations": ai_result["recommendations"],
    }
