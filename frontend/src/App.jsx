import React, { useState } from "react";
import Header from "./components/Header";
import MapSearch from "./components/MapSearch";
import MapContainer from "./components/MapContainer";
import StatsCard from "./components/StatsCard";
import ResultsDashboard from "./components/ResultsDashboard";
import { geocodeLocation, analyzeFieldPayload } from "./services/api";

export default function App() {
  const [language, setLanguage] = useState("en");
  const [mapCenter, setMapCenter] = useState({ lat: 30.1575, lng: 71.5249 });
  const [selectedField, setSelectedField] = useState(null);
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (query) => {
    setIsLoading(true);
    setError(null);
    try {
      const coords = await geocodeLocation(query);
      setMapCenter(coords);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePolygonSelect = (fieldData) => {
    setSelectedField(fieldData);
    setResults(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedField) return;

    setIsLoading(true);
    setError(null);

    // Payload sent directly to FastAPI backend
    const payload = {
      latitude: selectedField.center.lat,
      longitude: selectedField.center.lng,
      acres: selectedField.acres,
      polygon_geojson: selectedField.polygonGeoJSON,
      language: language,
    };

    try {
      const backendResponse = await analyzeFieldPayload(payload);
      setResults(backendResponse);
    } catch (err) {
      setError(err.message || "Failed to retrieve results from FastAPI backend.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-slate-100 text-slate-800 min-h-screen flex flex-col font-sans">
      <Header language={language} setLanguage={setLanguage} />

      <main className="max-w-7xl mx-auto w-full p-4 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-grow">
        {/* Left Column: Map Controls */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <MapSearch onSearch={handleSearch} isLoading={isLoading} />
          <MapContainer mapCenter={mapCenter} onPolygonSelect={handlePolygonSelect} />
          <StatsCard selectedField={selectedField} onAnalyze={handleAnalyze} isLoading={isLoading} />
        </div>

        {/* Right Column: Analysis Results */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col gap-5">
          <div className="flex justify-between items-center border-b pb-3">
            <h2 className="text-lg font-bold text-slate-800">Farm Analysis Results</h2>
          </div>
          <ResultsDashboard results={results} isLoading={isLoading} error={error} />
        </div>
      </main>

      <footer className="bg-slate-200 text-center py-3 text-xs text-slate-600 border-t border-slate-300">
        TerraWise Platform V1 &copy; 2026 | Powered by FastAPI, Open-Meteo & Groq AI
      </footer>
    </div>
  );
}