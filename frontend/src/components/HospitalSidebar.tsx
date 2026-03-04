'use client';

import { HospitalCard } from './HospitalCard';
import type { Hospital } from '@/types';

interface SidebarProps {
    hospitals: Hospital[];
    loading: boolean;
    onTriageOpen: () => void;
}

export function HospitalSidebar({ hospitals, loading, onTriageOpen }: SidebarProps) {
    const SPECIALTY_LABELS: Record<string, string> = {
        trauma: '외상', cardiac: '심장', neuro: '뇌신경',
        pediatric: '소아', obstetrics: '산부인과', internal: '내과',
    };

    return (
        <>
            <div className="sidebar-section">
                <span className="sidebar-label">병원 현황 ({hospitals.length})</span>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>
                        <span className="spinner" /> 로딩 중...
                    </div>
                ) : (
                    hospitals.map(h => (
                        <HospitalCard key={h.id} hospital={h} specialtyLabels={SPECIALTY_LABELS} />
                    ))
                )}
            </div>
        </>
    );
}
