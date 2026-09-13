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
    <form onSubmit={handleSearch} className="flex gap-2" aria-label="Search for a location on the map">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search a location, e.g. Sahiwal, Multan, Khanpur, Lahore"
        aria-label="Location search"
        className="flex-grow bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600"
      />
      <button
        type="submit"
        disabled={isLoading}
        className="bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-400 text-white px-5 py-2.5 rounded-lg font-medium text-sm shadow-sm transition whitespace-nowrap"
      >
        Search
      </button>
    </form>
  );
}