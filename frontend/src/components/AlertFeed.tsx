'use client';

import { useEffect, useState } from 'react';
import type { OsintAlert } from '@/types';

const TYPE_LABELS: Record<string, string> = {
    traffic: '교통', sns: 'SNS', weather: '기상', event: '이벤트',
};

interface Props {
    alerts: OsintAlert[];
    loading: boolean;
}

export function AlertFeed({ alerts, loading }: Props) {
    return (
        <div className="alert-feed">
            <div className="sidebar-label" style={{ padding: '4px 0', flexShrink: 0 }}>
                OSINT 실시간 경보 ({alerts.length})
            </div>
            {loading ? (
                <div style={{ textAlign: 'center', padding: '12px', color: 'var(--text-muted)' }}>
                    <span className="spinner" />
                </div>
            ) : alerts.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: 8 }}>특이 사항 없음</div>
            ) : (
                alerts.map(alert => (
                    <AlertItem key={alert.id} alert={alert} />
                ))
            )}
        </div>
    );
}

function AlertItem({ alert }: { alert: OsintAlert }) {
    return (
        <div className={`alert-item ${alert.severity}`}>
            <div className="alert-top">
                <span className={`alert-type-badge ${alert.type}`}>
                    {TYPE_LABELS[alert.type] || alert.type}
                </span>
                <span className="alert-time">{alert.minutes_ago}분 전</span>
            </div>
            <div className="alert-msg">{alert.message}</div>
        </div>
    );
}
