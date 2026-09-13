import React from "react";

const CHIP_TONES = {
  green: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-rose-100 text-rose-800",
  blue: "bg-sky-100 text-sky-800",
  gray: "bg-slate-200 text-slate-600",
};

function StatusChip({ label, tone = "gray" }) {
  if (!label) return null;
  return (
    <span
      className={`inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${CHIP_TONES[tone]}`}
    >
      {label}
    </span>
  );
}

function SectionLabel({ children }) {
  return (
    <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">{children}</h3>
  );
}

function MetricCard({ label, value, chip, tone }) {
  return (
    <div className="bg-slate-50 p-3 rounded-lg flex flex-col gap-1.5">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <p className="text-lg font-extrabold text-slate-800 leading-none">{value}</p>
      {chip && <StatusChip label={chip} tone={tone} />}
    </div>
  );
}

const ndviTone = (status) =>
  ({ VERY_LOW: "red", LOW: "amber", MODERATE: "amber", GOOD: "green", VERY_GOOD: "green" }[status] || "gray");

const ndmiTone = (status) =>
  ({ VERY_LOW: "red", LOW: "amber", MODERATE: "blue", GOOD: "green" }[status] || "gray");

const heatTone = (risk) => ({ LOW: "green", MODERATE: "amber", HIGH: "red" }[risk] || "gray");

const confidenceTone = (level) => ({ HIGH: "green", MEDIUM: "amber", LOW: "red" }[level] || "gray");

export default function ResultsDashboard({ results, isLoading, error }) {
  if (isLoading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-700 mx-auto mb-4" />
        <p className="text-emerald-800 font-semibold">Contacting TerraWise Backend Engine...</p>
        <p className="text-xs text-slate-500 mt-1">Fetching satellite and weather data</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 p-4 rounded-xl text-center text-rose-700 text-sm">
        <p className="font-bold">Analysis Request Failed</p>
        <p className="mt-1 text-xs">{error}</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="text-center py-16 text-slate-400">
        <p className="text-5xl mb-3">🛰️</p>
        <p className="text-sm font-medium text-slate-600">Select an agricultural field boundary</p>
        <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
          Draw a polygon on the map, then click <b>Analyze Area</b>.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {!results.satellite_available && (
        <div className="bg-slate-100 text-slate-600 text-xs p-3 rounded-lg">
          <span className="font-bold text-slate-700 block mb-0.5">Satellite data unavailable</span>
          Satellite analysis could not be completed for this request.
        </div>
      )}

      {!results.weather_available && (
        <div className="bg-slate-100 text-slate-600 text-xs p-3 rounded-lg">
          <span className="font-bold text-slate-700">Weather data unavailable.</span>{" "}
          {results.weather_message || "Live weather data could not be retrieved for this location."}
        </div>
      )}

      {/* A. Satellite Insights */}
      <section>
        <SectionLabel>Satellite Insights</SectionLabel>
        <div className="grid grid-cols-2 gap-2.5">
          <MetricCard
            label="Vegetation Activity (NDVI)"
            value={results.ndvi != null ? results.ndvi.toFixed(3) : "Unavailable"}
            chip={results.ndvi_status}
            tone={ndviTone(results.ndvi_status)}
          />
          <MetricCard
            label="Moisture (NDMI)"
            value={results.ndmi != null ? results.ndmi.toFixed(3) : "Unavailable"}
            chip={results.ndmi != null ? results.ndmi_status : "N/A"}
            tone={ndmiTone(results.ndmi_status)}
          />
        </div>
        {results.satellite_available && (
          <p className="text-[11px] text-slate-400 mt-2">
            Sentinel-2 • Observed {results.satellite_observation_date || "N/A"}
            {results.cloud_cover_percent != null && ` • Cloud cover ${results.cloud_cover_percent}%`}
          </p>
        )}
      </section>

      {/* B. Weather Conditions */}
      <section>
        <SectionLabel>Weather Conditions</SectionLabel>
        <div className="grid grid-cols-3 gap-2.5">
          <MetricCard
            label="Temperature"
            value={results.temperature_c != null ? `${results.temperature_c}°C` : "N/A"}
            chip={results.heat_risk}
            tone={heatTone(results.heat_risk)}
          />
          <MetricCard
            label="Humidity"
            value={results.humidity_percent != null ? `${results.humidity_percent}%` : "N/A"}
          />
          <MetricCard
            label="Recent Rainfall"
            value={results.recent_rainfall_mm != null ? `${results.recent_rainfall_mm} mm` : "N/A"}
            chip={results.rainfall_status}
            tone="blue"
          />
        </div>
        {results.weather_available && (
          <p className="text-[11px] text-slate-400 mt-2">Open-Meteo • Latest available data</p>
        )}
      </section>

      {/* C. Analysis Summary */}
      <section className="flex flex-col gap-2.5">
        <SectionLabel>Analysis Summary</SectionLabel>

        {results.possible_water_stress != null && (
          <div
            className={`text-xs p-3 rounded-lg ${
              results.possible_water_stress ? "bg-amber-50 text-amber-800" : "bg-slate-50 text-slate-600"
            }`}
          >
            {results.possible_water_stress
              ? "Current indicators suggest possible moisture stress. Consider verifying soil moisture in the field."
              : "No strong moisture-stress signal is detected from the current indicators."}
          </div>
        )}

        <div className="bg-slate-50 p-3 rounded-lg flex items-center justify-between gap-3">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block">
              Analysis Confidence
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Based on satellite availability, observation quality, and data completeness.
            </p>
          </div>
          <StatusChip label={results.analysis_confidence} tone={confidenceTone(results.analysis_confidence)} />
        </div>
      </section>

      {/* D. AI Interpretation */}
      <section className="bg-slate-50 p-4 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <span>🤖</span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">AI Interpretation</h3>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">{results.ai_explanation}</p>
      </section>

      {/* E. Recommended Next Steps */}
      <section className="bg-emerald-50/70 p-4 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <span>💡</span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900">Recommended Next Steps</h3>
        </div>
        <ul className="text-sm text-emerald-950 list-disc list-inside space-y-2">
          {results.recommendations?.map((rec, index) => (
            <li key={index}>{rec}</li>
          ))}
        </ul>
      </section>

      <p className="text-xs text-slate-400 text-center">
        TerraWise provides decision-support insights from satellite and weather data. It does not replace physical
        field inspection or soil testing.
      </p>
    </div>
  );
}
