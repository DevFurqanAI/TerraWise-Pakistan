import React from "react";

export default function StatsCard({ selectedField, onAnalyze, isLoading }) {
  if (!selectedField) return null;

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 flex justify-between items-center">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">
            Selected Farm Area
          </span>
          <p className="text-xl font-extrabold text-emerald-800">
            {selectedField.acres} acres
          </p>
        </div>
        <div className="border-l pl-4 border-slate-200">
          <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">
            Analysis Confidence
          </span>
          <p className="text-sm font-bold text-emerald-600">
            {selectedField.confidence}
          </p>
        </div>
      </div>

      <button
        onClick={onAnalyze}
        disabled={isLoading}
        className="bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-400 text-white px-6 py-3 rounded-lg font-bold shadow transition flex items-center gap-2"
      >
        ⚡ Analyze Farm
      </button>
    </div>
  );
}