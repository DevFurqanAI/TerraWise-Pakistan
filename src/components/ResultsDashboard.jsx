import React from "react";

export default function ResultsDashboard({ results, isLoading, error }) {
  if (isLoading) {
    return (
      <div className="text-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-700 mx-auto mb-4" />
        <p className="text-emerald-800 font-semibold">Contacting TerraWise Backend Engine...</p>
        <p className="text-xs text-slate-500 mt-1">Fetching Sentinel Satellite & Weather Telemetry</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-center text-rose-700 text-sm">
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
          Draw a polygon on the map, then click <b>Analyze Farm</b>.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Indicator Matrix Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Vegetation Health (NDVI)</span>
          <p className="text-base font-extrabold text-slate-800 mt-0.5">{results.ndvi_status}</p>
        </div>
        <div className="bg-amber-50 p-3 rounded-lg border border-amber-200">
          <span className="text-xs text-amber-800 font-bold uppercase tracking-wider">Moisture Condition (NDMI)</span>
          <p className="text-base font-bold text-amber-700 mt-0.5">{results.ndmi_status}</p>
        </div>
        <div className="bg-rose-50 p-3 rounded-lg border border-rose-200">
          <span className="text-xs text-rose-800 font-bold uppercase tracking-wider">Thermal Heat Risk</span>
          <p className="text-base font-bold text-rose-700 mt-0.5">{results.temperature_c}°C ({results.heat_risk})</p>
        </div>
        <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
          <span className="text-xs text-emerald-800 font-bold uppercase tracking-wider">Analysis Confidence</span>
          <p className="text-base font-bold text-emerald-700 mt-0.5">{results.analysis_confidence}</p>
        </div>
      </div>

      {/* AI Explanation Box */}
      <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <span>🤖</span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">AI Field Interpretation</h3>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">{results.ai_explanation}</p>
      </div>

      {/* Recommended Action Steps */}
      <div className="bg-emerald-50/70 border border-emerald-200 p-4 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <span>💡</span>
          <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-900">Actionable Insights</h3>
        </div>
        <ul className="text-sm text-emerald-950 list-disc list-inside space-y-1.5">
          {results.recommendations?.map((rec, index) => (
            <li key={index}>{rec}</li>
          ))}
        </ul>
      </div>

      <p className="text-[11px] text-slate-400 italic text-center">
        * TerraWise decision support is based on satellite imagery & telemetry[cite: 1]. It does not replace physical soil testing[cite: 1].
      </p>
    </div>
  );
}