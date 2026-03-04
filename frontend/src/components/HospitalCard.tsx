'use client';

import type { Hospital } from '@/types';

interface Props {
    hospital: Hospital;
    specialtyLabels: Record<string, string>;
}

const TREND_ICON: Record<string, string> = {
    improving: '↑',
    worsening: '↓',
    stable: '→',
};

export function HospitalCard({ hospital: h, specialtyLabels }: Props) {
    return (
        <div className={`hospital-card ${h.status}`}>
            <div className="card-header">
                <div>
                    <div className="card-name">{h.name_short}</div>
                    <div className="card-level">{h.level}</div>
                </div>
                <div className={`status-badge ${h.status}`}>
                    <span>
                        {h.status === 'green' ? '●' : h.status === 'amber' ? '●' : '●'}
                    </span>
                    {h.status === 'green' ? '수용가능' : h.status === 'amber' ? '주의' : '포화'}
                </div>
            </div>

            <div className="card-metrics">
                <div className="metric">
                    <span className="metric-label">수용지수</span>
                    <span className="metric-value accent">{h.status_index}%</span>
                </div>
                <div className="metric">
                    <span className="metric-label">가용병상</span>
                    <span className="metric-value">{h.available_beds}<span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>/{h.total_beds}</span></span>
                </div>
            </div>

            <div className="si-bar-wrap">
                <div
                    className={`si-bar-fill ${h.status}`}
                    style={{ width: `${h.status_index}%` }}
                />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    점유율 {h.occupancy_pct}%
                </div>
                <div style={{ fontSize: 10, color: h.trend === 'improving' ? 'var(--status-green)' : h.trend === 'worsening' ? 'var(--status-red)' : 'var(--text-muted)' }}>
                    <span className="trend-icon">{TREND_ICON[h.trend]}</span> {h.trend === 'improving' ? '개선 중' : h.trend === 'worsening' ? '악화 중' : '안정'}
                </div>
            </div>

            <div className="card-specialties">
                {h.available_specialties.map(s => (
                    <span key={s} className="spec-tag available">{specialtyLabels[s] || s}</span>
                ))}
                {h.offline_specialties.map(s => (
                    <span key={s} className="spec-tag offline">{specialtyLabels[s] || s}</span>
                ))}
            </div>
        </div>
    );
}
