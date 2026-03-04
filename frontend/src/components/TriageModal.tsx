'use client';

import { useState } from 'react';
import type { RecommendResult, RecommendResponse } from '@/types';

const KTAS_LABELS = ['', '즉시', '응급', '긴급', '준긴급', '비응급'];
const SPECIALTIES = [
    { key: 'general', icon: '🏥', label: '일반' },
    { key: 'trauma', icon: '🩹', label: '외상' },
    { key: 'cardiac', icon: '❤️', label: '심장' },
    { key: 'neuro', icon: '🧠', label: '뇌신경' },
    { key: 'pediatric', icon: '👶', label: '소아' },
    { key: 'obstetrics', icon: '🤱', label: '산부인과' },
];

interface Props {
    open: boolean;
    onClose: () => void;
}

export function TriageModal({ open, onClose }: Props) {
    const [ktas, setKtas] = useState<number>(0);
    const [specialty, setSpecialty] = useState<string>('general');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<RecommendResponse | null>(null);

    if (!open) return null;

    async function handleRecommend() {
        if (!ktas) return;
        setLoading(true);
        setResult(null);
        try {
            const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
            const res = await fetch(`${API}/recommend`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ktas, specialty }),
            });
            const data: RecommendResponse = await res.json();
            setResult(data);
        } catch {
            // backend not reachable
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
            <div className="modal-box">
                <div className="modal-header">
                    <span className="modal-title">🚑 지능형 이송 추천</span>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    {/* KTAS */}
                    <div className="form-group">
                        <label className="form-label">KTAS 응급도 (1=최위급)</label>
                        <div className="ktas-grid">
                            {[1, 2, 3, 4, 5].map(k => (
                                <button
                                    key={k}
                                    className={`ktas-btn ${ktas === k ? 'active' : ''}`}
                                    data-ktas={k}
                                    onClick={() => setKtas(k)}
                                >
                                    <div>{k}</div>
                                    <div className="ktas-sub">{KTAS_LABELS[k]}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Specialty */}
                    <div className="form-group">
                        <label className="form-label">질환 분류</label>
                        <div className="spec-grid">
                            {SPECIALTIES.map(s => (
                                <button
                                    key={s.key}
                                    className={`spec-btn ${specialty === s.key ? 'active' : ''}`}
                                    onClick={() => setSpecialty(s.key)}
                                >
                                    <span>{s.icon}</span>
                                    <span>{s.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        className="recommend-btn"
                        onClick={handleRecommend}
                        disabled={!ktas || loading}
                    >
                        {loading ? <><span className="spinner" /> 분석 중...</> : '최적 이송지 추천 →'}
                    </button>

                    {/* Results */}
                    {result && (
                        <div className="results-section">
                            <div className="advisory-box">{result.advisory}</div>
                            <div className="rec-list">
                                {result.recommendations.map(rec => (
                                    <RecCard key={rec.id} rec={rec} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function RecCard({ rec }: { rec: RecommendResult }) {
    return (
        <div className={`rec-item ${rec.is_top_pick ? 'top-pick' : ''}`}>
            {rec.is_top_pick && <span className="top-pick-label">추천</span>}
            <div className="rec-header">
                <div className="rec-name">{rec.name}</div>
                <div className={`rec-si ${rec.status}`}>{rec.status_index}%</div>
            </div>
            <div className="rec-meta">
                <div className="rec-meta-item">⏱ {rec.eta_minutes}분</div>
                <div className="rec-meta-item">📍 {rec.distance_km}km</div>
                <div className="rec-meta-item">🛏 여유 {rec.available_beds}병상</div>
                {!rec.has_required_specialty && (
                    <div className="rec-meta-item" style={{ color: 'var(--status-red)' }}>⚠️ 전문의 부재</div>
                )}
            </div>
            <div className="rec-note">{rec.recommendation_note}</div>
        </div>
    );
}
