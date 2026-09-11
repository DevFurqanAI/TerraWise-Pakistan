import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet-draw";
import * as turf from "@turf/turf";

export default function MapContainer({ mapCenter, onPolygonSelect }) {
  const mapRef = useRef(null);
  const leafletInstance = useRef(null);
  const drawnItemsRef = useRef(null);

  useEffect(() => {
    if (!leafletInstance.current) {
      const map = L.map(mapRef.current).setView([mapCenter.lat, mapCenter.lng], 10);

      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS",
      }).addTo(map);

      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);
      drawnItemsRef.current = drawnItems;

      const drawControl = new L.Control.Draw({
        draw: {
          polygon: { allowIntersection: false },
          rectangle: true,
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: { featureGroup: drawnItems, remove: true },
      });
      map.addControl(drawControl);

      map.on(L.Draw.Event.CREATED, (e) => {
        drawnItems.clearLayers();
        const layer = e.layer;
        drawnItems.addLayer(layer);

        const geojson = layer.toGeoJSON();
        const areaSqMeters = turf.area(geojson);
        const acres = parseFloat((areaSqMeters * 0.000247105).toFixed(2));

        const center = turf.centerOfMass(geojson).geometry.coordinates;

        let confidence = "HIGH";
        if (acres < 0.5) confidence = "LOW";
        else if (acres > 500) confidence = "MEDIUM";

        onPolygonSelect({
          polygonGeoJSON: geojson,
          center: { lat: center[1], lng: center[0] },
          acres,
          confidence,
        });
      });

      leafletInstance.current = map;
    }
  }, []);

  useEffect(() => {
    if (leafletInstance.current && mapCenter) {
      leafletInstance.current.setView([mapCenter.lat, mapCenter.lng], 14);
    }
  }, [mapCenter]);

  return (
    <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-200">
      <div ref={mapRef} className="h-[520px] w-full rounded-lg z-10" />
    </div>
  );
}