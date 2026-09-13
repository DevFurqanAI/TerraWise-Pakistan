import React from "react";

export default function Header({ language, setLanguage }) {
  return (
    <header className="bg-emerald-900 text-white">
      <div className="max-w-7xl mx-auto flex flex-wrap gap-3 justify-between items-center px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            🌱 TerraWise
          </h1>
          <span className="text-[10px] text-emerald-300/80 border border-emerald-700 px-1.5 py-0.5 rounded uppercase tracking-wider font-medium">
            V1 Hackathon
          </span>
          <span className="hidden sm:inline text-xs text-emerald-300/70 ml-1">
            Agricultural decision support from satellite &amp; weather data
          </span>
        </div>

        <div
          role="tablist"
          aria-label="AI response language"
          className="flex items-center bg-emerald-950/60 p-1 rounded-lg text-xs shrink-0"
        >
          <button
            type="button"
            role="tab"
            aria-selected={language === "en"}
            onClick={() => setLanguage("en")}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              language === "en"
                ? "bg-white text-emerald-900 shadow-sm"
                : "text-emerald-200 hover:text-white"
            }`}
          >
            English
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={language === "ur"}
            onClick={() => setLanguage("ur")}
            className={`px-3 py-1.5 rounded-md font-semibold transition ${
              language === "ur"
                ? "bg-white text-emerald-900 shadow-sm"
                : "text-emerald-200 hover:text-white"
            }`}
          >
            اردو
          </button>
        </div>
      </div>
    </header>
  );
}
