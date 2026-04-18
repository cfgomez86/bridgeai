import type { Metadata } from "next"
import "./globals.css"
import { Sidebar } from "@/components/features/Sidebar"
import { Topbar } from "@/components/features/Topbar"

export const metadata: Metadata = {
  title: "BridgeAI",
  description: "Requirement to ticket automation",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh" }}>
          <Sidebar />
          <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
            <Topbar />
            <main style={{ flex: 1, background: "var(--bg)" }}>{children}</main>
          </div>
        </div>
      </body>
    </html>
  )
}
