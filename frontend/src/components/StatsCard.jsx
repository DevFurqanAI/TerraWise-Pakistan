import React from "react";

export default function StatsCard({ selectedField, onAnalyze, isLoading }) {
  if (!selectedField) return null;

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm flex flex-wrap gap-4 justify-between items-center">
      <div>
        <span className="text-xs text-slate-500 uppercase font-semibold tracking-wider">
          Selected Area
        </span>
        <p className="text-2xl font-extrabold text-emerald-800 leading-tight">
          {selectedField.acres} <span className="text-base font-semibold text-slate-500">acres</span>
        </p>
      </div>

      <button
        onClick={onAnalyze}
        disabled={isLoading}
        className="bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-400 text-white px-6 py-3 rounded-lg font-bold shadow transition flex items-center gap-2"
      >
        ⚡ Analyze Area
      </button>
    </div>
  );
}
