import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '분당 골든패스 | 응급의료 자원 최적화 플랫폼',
  description: 'OSINT 기반 분당 권역 응급의료 자원 실시간 모니터링 및 최적 이송지 추천 시스템',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
