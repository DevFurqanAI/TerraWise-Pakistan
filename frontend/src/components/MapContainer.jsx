import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet-draw";
import * as turf from "@turf/turf";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

export default function MapContainer({ mapCenter, onPolygonSelect }) {
  const mapRef = useRef(null);
  const leafletInstance = useRef(null);
  const drawnItemsRef = useRef(null);

  useEffect(() => {
    if (!leafletInstance.current && mapRef.current) {
      const map = L.map(mapRef.current).setView([mapCenter.lat, mapCenter.lng], 14);

      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS",
      }).addTo(map);

      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);
      drawnItemsRef.current = drawnItems;

      // 1. ORIGINAL POLYGON TOOL SETTINGS PRESERVED
      const drawControl = new L.Control.Draw({
        draw: {
          polygon: { allowIntersection: false }, // Exact original setting
          rectangle: {
            shapeOptions: { color: "#3b82f6", weight: 2, fillOpacity: 0.2 },
            metric: true
          },
          polyline: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: { featureGroup: drawnItems, remove: true },
      });
      map.addControl(drawControl);

      const notifyParent = (layer) => {
        const geojson = layer.toGeoJSON();
        const areaSqMeters = turf.area(geojson);
        const acres = parseFloat((areaSqMeters * 0.000247105).toFixed(2));

        const center = turf.centerOfMass(geojson).geometry.coordinates;

        onPolygonSelect({
          polygonGeoJSON: geojson,
          center: { lat: center[1], lng: center[0] },
          acres,
        });
      };

      // 2. RECTANGLE SPECIFIC: CLICK-TO-DROP RESIZABLE BOX
      map.on(L.Draw.Event.DRAWSTART, (e) => {
        if (e.layerType === "rectangle") {
          const handleRectangleClick = (clickEvent) => {
            drawnItems.clearLayers();

            const lat = clickEvent.latlng.lat;
            const lng = clickEvent.latlng.lng;
            const offset = 0.0018; // Default initial box frame

            const bounds = [
              [lat - offset, lng - offset],
              [lat + offset, lng + offset],
            ];

            const rectangle = L.rectangle(bounds, {
              color: "#3b82f6",
              weight: 2,
              fillOpacity: 0.2,
            });

            drawnItems.addLayer(rectangle);

            // Resize/move handles are shown only via the "Edit layers" toolbar control,
            // so the map stays clean once a shape is placed instead of leaving stray
            // vertex handles visible.

            notifyParent(rectangle);
            map.off("click", handleRectangleClick);
          };

          map.once("click", handleRectangleClick);
        }
      });

      // 3. ORIGINAL POLYGON CREATION EVENT PRESERVED
      map.on(L.Draw.Event.CREATED, (e) => {
        if (e.layerType === "polygon") {
          drawnItems.clearLayers();
          const layer = e.layer;
          drawnItems.addLayer(layer);
          notifyParent(layer);
        }
      });

      // Edit event handlers for corner adjustments
      map.on(L.Draw.Event.EDITMOVE, (e) => notifyParent(e.layer));
      map.on(L.Draw.Event.EDITRESIZE, (e) => notifyParent(e.layer));
      map.on(L.Draw.Event.EDITED, (e) => {
        e.layers.eachLayer((layer) => {
          notifyParent(layer);
          if (layer.editing && layer.editing.enabled()) {
            layer.editing.disable();
          }
        });
      });

      map.on(L.Draw.Event.DELETED, () => {
        onPolygonSelect(null);
      });

      leafletInstance.current = map;

      setTimeout(() => map.invalidateSize(), 250);
    }
  }, []);

  useEffect(() => {
    if (leafletInstance.current && mapCenter) {
      leafletInstance.current.setView([mapCenter.lat, mapCenter.lng], 14);
      leafletInstance.current.invalidateSize();
    }
  }, [mapCenter]);

  return (
    <div className="bg-white p-1.5 rounded-xl shadow-md">
      <div ref={mapRef} className="h-[520px] w-full rounded-lg z-10" />
    </div>
  );
}