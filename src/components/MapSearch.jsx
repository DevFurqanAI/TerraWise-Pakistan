import React, { useState } from "react";

export default function MapSearch({ onSearch, isLoading }) {
  const [query, setQuery] = useState("");

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSearch} className="bg-white p-3 rounded-xl shadow-sm border border-slate-200 flex gap-2">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search location (e.g., Sahiwal, Multan, Khanpur, Lahore)..."
        className="flex-grow border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-600 text-sm"
      />
      <button
        type="submit"
        disabled={isLoading}
        className="bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-400 text-white px-5 py-2 rounded-lg font-medium text-sm transition whitespace-nowrap"
      >
        Search Map
      </button>
    </form>
  );
}