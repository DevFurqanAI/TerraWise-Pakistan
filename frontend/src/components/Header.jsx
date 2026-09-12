import React from "react";

export default function Header({ language, setLanguage }) {
  return (
    <header className="bg-emerald-800 text-white p-4 shadow-md">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            🌱 TerraWise
            <span className="text-xs bg-emerald-600 border border-emerald-400 px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
              V1 Hackathon
            </span>
          </h1>
          <p className="text-xs text-emerald-200 mt-0.5">
            Agricultural Intelligence & Environmental Decision Support
          </p>
        </div>

        <div className="flex items-center gap-2 bg-emerald-900/60 p-1.5 rounded-lg text-xs">
          <span className="text-emerald-200 font-medium">AI Language:</span>
          <button
            onClick={() => setLanguage("en")}
            className={`px-2.5 py-1 rounded font-bold transition ${
              language === "en"
                ? "bg-emerald-500 text-white shadow-sm"
                : "text-emerald-200 hover:text-white"
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage("ur")}
            className={`px-2.5 py-1 rounded font-bold transition ${
              language === "ur"
                ? "bg-emerald-500 text-white shadow-sm"
                : "text-emerald-200 hover:text-white"
            }`}
          >
            اردو (Urdu)
          </button>
        </div>
      </div>
    </header>
  );
}