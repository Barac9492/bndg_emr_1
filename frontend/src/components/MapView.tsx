'use client';

import { useEffect, useRef } from 'react';
import type { Hospital } from '@/types';

interface Props {
  hospitals: Hospital[];
}

const STATUS_COLORS: Record<string, string> = {
  green: '#00e676',
  amber: '#ffb347',
  red: '#ff4757',
};

export function MapView({ hospitals }: Props) {
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Leaflet must be imported client-side only
    let L: any;
    async function init() {
      if (mapRef.current) return; // already initialised
      L = await import('leaflet');
      // @ts-expect-error — leaflet CSS has no type declarations, import is safe at runtime
      await import('leaflet/dist/leaflet.css');

      if (!containerRef.current) return;

      // Guard: Leaflet sets _leaflet_id on the container after L.map().
      // React Strict Mode / HMR can call the effect twice before cleanup runs,
      // so we check and bail out if the container was already initialized.
      const container = containerRef.current as any;
      if (container._leaflet_id) return;

      const map = L.map(containerRef.current, {
        center: [37.3700, 127.1150],
        zoom: 13,
        zoomControl: true,
        attributionControl: false,
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap © CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = { map, L };
    }
    init();

    return () => {
      if (mapRef.current) {
        mapRef.current.map.remove();
        mapRef.current = null;
      }
      // Also clear the Leaflet ID from the container so re-mount works cleanly
      if (containerRef.current) {
        delete (containerRef.current as any)._leaflet_id;
      }
    };
  }, []);

  // Update markers whenever hospitals data changes
  useEffect(() => {
    if (!mapRef.current || !hospitals.length) return;
    const { map, L } = mapRef.current;

    // Remove old markers
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    hospitals.forEach(h => {
      const color = STATUS_COLORS[h.status];
      const iconHtml = `
        <div style="
          width:40px;height:40px;border-radius:50%;
          background:${color}22;border:2.5px solid ${color};
          display:flex;align-items:center;justify-content:center;
          font-size:18px;cursor:pointer;
          box-shadow:0 0 12px ${color}66;
          transition:transform 0.2s;
        ">🏥</div>`;

      const icon = L.divIcon({ html: iconHtml, iconSize: [40, 40], className: '' });

      const marker = L.marker([h.lat, h.lng], { icon })
        .addTo(map)
        .bindPopup(`
          <div style="
            background:#0d1526;color:#e8f0fe;border:1px solid rgba(0,212,255,0.3);
            border-radius:10px;padding:12px;min-width:220px;font-family:Inter,sans-serif;
          ">
            <div style="font-weight:800;font-size:14px;margin-bottom:6px;">${h.name}</div>
            <div style="font-size:12px;color:#8ba3c7;margin-bottom:8px;">${h.level}</div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
              <span style="font-size:12px;color:#8ba3c7;">수용지수</span>
              <span style="font-weight:700;color:${color};">${h.status_index}%</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
              <span style="font-size:12px;color:#8ba3c7;">가용 병상</span>
              <span style="font-weight:700;">${h.available_beds} / ${h.total_beds}</span>
            </div>
            <div style="
              height:4px;background:rgba(255,255,255,0.08);border-radius:4px;overflow:hidden;
            ">
              <div style="
                height:100%;width:${h.status_index}%;background:${color};border-radius:4px;
              "></div>
            </div>
            <div style="margin-top:8px;font-size:11px;color:#8ba3c7;">${h.phone}</div>
          </div>
        `, {
          maxWidth: 260,
          className: 'golden-pass-popup',
        });

      markersRef.current.push(marker);
    });
  }, [hospitals]);

  return (
    <>
      <style>{`
        .leaflet-popup-content-wrapper {
          background: transparent !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .leaflet-popup-content {
          margin: 0 !important;
        }
        .leaflet-popup-tip-container { display: none; }
        .leaflet-control-zoom a {
          background: #0d1526 !important;
          color: #e8f0fe !important;
          border-color: rgba(59,130,246,0.3) !important;
        }
        .leaflet-control-zoom a:hover {
          background: #162035 !important;
        }
      `}</style>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </>
  );
}
