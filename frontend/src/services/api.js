const BACKEND_BASE_URL = "http://localhost:8000/api/v1"; // Update to your team's FastAPI URL

export async function geocodeLocation(query) {
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`
  );
  if (!response.ok) throw new Error("Location search failed.");
  const data = await response.json();
  if (!data || data.length === 0) throw new Error("Location not found.");
  return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
}

export async function analyzeFieldPayload(payload) {
  const response = await fetch(`${BACKEND_BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to analyze field with backend server.");
  }

  return await response.json();
}