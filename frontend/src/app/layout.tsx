
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Governance Engine',
  description: 'Deterministic Architectural Governance — Static analysis for system architecture plans',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Header />

        <main className="container">
          {children}
        </main>

        <footer className="footer">
          <div>
            <span style={{
              fontWeight: 600
            }}>Governance Engine</span>
            <span style={{ margin: '0 0.5rem', color: 'var(--border-highlight)' }}>·</span>
            <span>MVP — 4 Architectural Rules</span>
          </div>
          <div>
            Gemini 3 Pro · BYOK · Deterministic DFR
          </div>
        </footer>
      </body>
    </html>
  )
}
