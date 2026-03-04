'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState, useCallback } from 'react';
import type { Hospital, OsintAlert, HospitalsResponse, AlertsResponse } from '@/types';
import { HospitalCard } from '@/components/HospitalCard';
import { AlertFeed } from '@/components/AlertFeed';
import { TriageModal } from '@/components/TriageModal';

const MapView = dynamic(() => import('@/components/MapView').then(m => m.MapView), {
  ssr: false,
  loading: () => (
    <div style={{
      width: '100%', height: '100%', display: 'flex', alignItems: 'center',
      justifyContent: 'center', color: 'var(--text-muted)', background: 'var(--bg-base)',
      flexDirection: 'column', gap: 12, fontSize: 14,
    }}>
      <span className="spinner" />
      <span>지도 로딩 중...</span>
    </div>
  ),
});

const SPECIALTY_LABELS: Record<string, string> = {
  trauma: '외상', cardiac: '심장', neuro: '뇌신경',
  pediatric: '소아', obstetrics: '산부인과', internal: '내과',
};

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function HomePage() {
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [alerts, setAlerts] = useState<OsintAlert[]>([]);
  const [narrative, setNarrative] = useState<string>('시스템 초기화 중...');
  const [hosLoading, setHosLoading] = useState(true);
  const [altLoading, setAltLoading] = useState(true);
  const [triadgeOpen, setTriageOpen] = useState(false);
  const [clock, setClock] = useState('');

  // Clock
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  const fetchHospitals = useCallback(async () => {
    try {
      const res = await fetch(`${API}/hospitals`);
      const data: HospitalsResponse = await res.json();
      setHospitals(data.hospitals);
      setNarrative(data.system_narrative);
    } catch {
      setNarrative('⚠️ 백엔드 연결 실패 — 백엔드 서버를 시작하세요');
    } finally {
      setHosLoading(false);
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/alerts`);
      const data: AlertsResponse = await res.json();
      setAlerts(data.alerts);
    } catch {
      // silent
    } finally {
      setAltLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHospitals();
    fetchAlerts();
    const hosInterval = setInterval(fetchHospitals, 30000); // every 30s
    const altInterval = setInterval(fetchAlerts, 15000);    // every 15s
    return () => { clearInterval(hosInterval); clearInterval(altInterval); };
  }, [fetchHospitals, fetchAlerts]);

  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-brand">
          <div>
            <div className="header-logo">🚑 분당 골든패스</div>
            <div className="header-sub">OSINT 기반 응급의료 자원 최적화</div>
          </div>
        </div>
        <div className="header-meta">
          <div className="narrative-bar">{narrative}</div>
          <div className="live-badge">
            <span className="live-dot" />
            LIVE
          </div>
          <div className="clock">{clock}</div>
        </div>
      </header>

      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-section">
          <span className="sidebar-label">병원 현황 ({hospitals.length})</span>
          {hosLoading ? (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>
              <span className="spinner" /> 로딩 중...
            </div>
          ) : hospitals.map(h => (
            <HospitalCard key={h.id} hospital={h} specialtyLabels={SPECIALTY_LABELS} />
          ))}
        </div>

        <AlertFeed alerts={alerts} loading={altLoading} />

        <button className="triage-btn" onClick={() => setTriageOpen(true)}>
          🚑 지능형 이송 추천 실행
        </button>
      </aside>

      {/* ── Map ── */}
      <main className="map-wrapper">
        <MapView hospitals={hospitals} />
      </main>

      {/* ── Triage Modal ── */}
      <TriageModal open={triadgeOpen} onClose={() => setTriageOpen(false)} />
    </div>
  );
}
