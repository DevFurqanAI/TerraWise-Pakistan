import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import services  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}

    def json(self):
        return self._json_data


def _owm_entry(local_dt, temp, humidity, rain_3h=None):
    entry = {
        "dt": int(local_dt.timestamp()),
        "main": {"temp": temp, "humidity": humidity},
    }
    if rain_3h is not None:
        entry["rain"] = {"3h": rain_3h}
    return entry


def _owm_payload(tz_offset_seconds, entries):
    return {
        "cod": "200",
        "list": entries,
        "city": {"timezone": tz_offset_seconds},
    }


def test_open_meteo_success_returns_primary_without_fallback():
    ok_response = FakeResponse(
        status_code=200,
        json_data={
            "daily": {
                "temperature_2m_max": [30.0],
                "relative_humidity_2m_mean": [55],
                "precipitation_sum": [1.2],
            }
        },
    )
    with patch("app.services.requests.get", return_value=ok_response) as mock_get:
        result = services.get_weather_data(30.0, 70.0)

    assert result["weather_available"] is True
    assert result["temperature_c"] == 30.0
    assert result["humidity_percent"] == 55
    assert result["recent_rainfall_mm"] == 1.2
    mock_get.assert_called_once()  # only Open-Meteo, no fallback attempted


def test_open_meteo_failure_then_openwatermap_success():
    tz_offset = 5 * 3600
    now_local = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
    today_local = now_local.replace(hour=6, minute=0, second=0, microsecond=0)

    entries = [
        _owm_entry(today_local, temp=28.0, humidity=40, rain_3h=0.5),
        _owm_entry(today_local + timedelta(hours=3), temp=33.0, humidity=50, rain_3h=1.5),
        _owm_entry(today_local - timedelta(days=1), temp=99.0, humidity=99),  # different local day, must be excluded
    ]
    owm_response = FakeResponse(status_code=200, json_data=_owm_payload(tz_offset, entries))
    open_meteo_failure = FakeResponse(status_code=503, json_data={})

    def fake_get(url, *args, **kwargs):
        if "open-meteo.com" in url:
            return open_meteo_failure
        return owm_response

    with patch("app.services.settings.OPENWEATHER_API_KEY", "fake-key"), \
         patch("app.services.requests.get", side_effect=fake_get), \
         patch("app.services.time.sleep"):
        result = services.get_weather_data(30.0, 70.0)

    assert result["weather_available"] is True
    assert result["temperature_c"] == 33.0
    assert result["humidity_percent"] == 45  # average of 40 and 50
    assert result["recent_rainfall_mm"] == 2.0  # 0.5 + 1.5, excluding the other-day entry


def test_open_meteo_failure_then_openweathermap_failure():
    open_meteo_failure = FakeResponse(status_code=503, json_data={})
    owm_failure = FakeResponse(status_code=401, json_data={"message": "Invalid API key"})

    def fake_get(url, *args, **kwargs):
        if "open-meteo.com" in url:
            return open_meteo_failure
        return owm_failure

    with patch("app.services.settings.OPENWEATHER_API_KEY", "fake-key"), \
         patch("app.services.requests.get", side_effect=fake_get), \
         patch("app.services.time.sleep"):
        result = services.get_weather_data(30.0, 70.0)

    assert result["weather_available"] is False
    assert result.get("weather_message")


def test_openweathermap_no_fallback_configured_returns_primary_failure():
    open_meteo_failure = FakeResponse(status_code=503, json_data={})

    with patch("app.services.settings.OPENWEATHER_API_KEY", ""), \
         patch("app.services.requests.get", return_value=open_meteo_failure) as mock_get, \
         patch("app.services.time.sleep"):
        result = services.get_weather_data(30.0, 70.0)

    assert result["weather_available"] is False
    # Only Open-Meteo's retries should have been attempted, never OpenWeatherMap.
    for call in mock_get.call_args_list:
        assert "openweathermap.org" not in call.args[0]


def test_openweathermap_response_with_no_rain_field_treats_missing_as_zero():
    tz_offset = 0
    now_local = datetime.now(timezone.utc)
    today_local = now_local.replace(hour=9, minute=0, second=0, microsecond=0)

    entries = [_owm_entry(today_local, temp=25.0, humidity=60)]  # no rain key at all
    payload = _owm_payload(tz_offset, entries)

    with patch("app.services.requests.get", return_value=FakeResponse(status_code=200, json_data=payload)):
        result = services._fetch_openweathermap_fallback(30.0, 70.0)

    assert result["weather_available"] is True
    assert result["recent_rainfall_mm"] == 0.0
    assert result["temperature_c"] == 25.0
    assert result["humidity_percent"] == 60


def test_openweathermap_response_with_multiple_3hour_rain_values_sums_them():
    tz_offset = 0
    now_local = datetime.now(timezone.utc)
    today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = [
        _owm_entry(today_local + timedelta(hours=3), temp=20.0, humidity=70, rain_3h=1.0),
        _owm_entry(today_local + timedelta(hours=6), temp=22.0, humidity=75, rain_3h=2.5),
        _owm_entry(today_local + timedelta(hours=9), temp=24.0, humidity=80, rain_3h=0.25),
    ]
    payload = _owm_payload(tz_offset, entries)

    with patch("app.services.requests.get", return_value=FakeResponse(status_code=200, json_data=payload)):
        result = services._fetch_openweathermap_fallback(30.0, 70.0)

    assert result["weather_available"] is True
    assert result["recent_rainfall_mm"] == 3.8  # 1.0 + 2.5 + 0.25 = 3.75, rounded to 1 decimal
    assert result["temperature_c"] == 24.0
    assert result["humidity_percent"] == 75  # round(average(70, 75, 80)) == round(75.0)


def test_openweathermap_no_usable_entries_for_local_date_is_unavailable():
    tz_offset = 0
    now_local = datetime.now(timezone.utc)
    # All entries fall on a different local calendar day than "today".
    other_day = now_local + timedelta(days=2)
    entries = [_owm_entry(other_day, temp=20.0, humidity=50, rain_3h=0.0)]
    payload = _owm_payload(tz_offset, entries)

    with patch("app.services.requests.get", return_value=FakeResponse(status_code=200, json_data=payload)):
        result = services._fetch_openweathermap_fallback(30.0, 70.0)

    assert result["weather_available"] is False
    assert result.get("weather_message")
