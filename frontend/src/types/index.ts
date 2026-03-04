// Shared TypeScript types for 분당 골든패스

export type StatusColor = 'green' | 'amber' | 'red';

export interface Hospital {
    id: string;
    name: string;
    name_short: string;
    lat: number;
    lng: number;
    address: string;
    phone: string;
    specialties: string[];
    total_beds: number;
    equipment: string[];
    level: string;
    available_beds: number;
    occupancy_pct: number;
    status_index: number;
    status: StatusColor;
    trend: 'improving' | 'worsening' | 'stable';
    available_specialties: string[];
    offline_specialties: string[];
    last_updated: string;
}

export interface OsintAlert {
    id: string;
    type: 'traffic' | 'sns' | 'weather' | 'event';
    severity: 'high' | 'medium' | 'low';
    message: string;
    timestamp: string;
    minutes_ago: number;
}

export interface HospitalsResponse {
    hospitals: Hospital[];
    system_narrative: string;
    total_hospitals: number;
}

export interface AlertsResponse {
    alerts: OsintAlert[];
    total: number;
}

export interface RecommendRequest {
    ktas: number;
    specialty: string;
    location_lat?: number;
    location_lng?: number;
}

export interface RecommendResult {
    id: string;
    name: string;
    name_short: string;
    status_index: number;
    status: StatusColor;
    available_beds: number;
    eta_minutes: number;
    distance_km: number;
    has_required_specialty: boolean;
    available_specialties: string[];
    score: number;
    recommendation_note: string;
    is_top_pick?: boolean;
}

export interface RecommendResponse {
    ktas: number;
    specialty: string;
    recommendations: RecommendResult[];
    advisory: string;
}
