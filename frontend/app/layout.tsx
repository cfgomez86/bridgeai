import type { Metadata } from "next"
import "./globals.css"
import { ClerkProvider } from "@clerk/nextjs"
import { Sidebar } from "@/components/features/Sidebar"
import { Topbar } from "@/components/features/Topbar"
import { LanguageProvider } from "@/lib/i18n"
import { ThemeProvider } from "@/lib/theme/ThemeContext"
import { ClerkTokenSync } from "@/components/features/ClerkTokenSync"

export const metadata: Metadata = {
  title: "BridgeAI",
  description: "Requirement to ticket automation",
}

const themeScript = `(function(){try{var t=localStorage.getItem('bridgeai-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      {/* suppressHydrationWarning: server renders without .dark; blocking script may add it before hydration */}
      <html lang="es" suppressHydrationWarning>
        <head>
          {/* Blocking script — runs before CSS paint to avoid flash of light theme */}
          <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        </head>
        <body>
          <ThemeProvider>
            <LanguageProvider>
              <ClerkTokenSync />
              <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh" }}>
                <Sidebar />
                <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
                  <Topbar />
                  <main style={{ flex: 1, background: "var(--bg)" }}>{children}</main>
                </div>
              </div>
            </LanguageProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
