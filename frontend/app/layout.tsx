import type { Metadata, Viewport } from "next"
import "./globals.css"
import { Auth0Provider } from "@auth0/nextjs-auth0/client"
import { LanguageProvider } from "@/lib/i18n"
import { ThemeProvider } from "@/lib/theme/ThemeContext"
import { Auth0TokenSync } from "@/components/features/Auth0TokenSync"
import { AppShell } from "@/components/features/AppShell"

export const metadata: Metadata = {
  title: "BridgeAI",
  description: "Requirement to ticket automation",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
}

// Runs synchronously before first paint — prevents flash of light theme on reload.
// Must be a native <script> tag (not next/script) to guarantee blocking execution.
const themeScript = `(function(){try{var t=localStorage.getItem('bridgeai-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <Auth0Provider>
      <html lang="es" suppressHydrationWarning>
        <head>
          {/* eslint-disable-next-line @next/next/no-sync-scripts */}
          <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        </head>
        <body>
          <ThemeProvider>
            <LanguageProvider>
              <Auth0TokenSync />
              <AppShell>{children}</AppShell>
            </LanguageProvider>
          </ThemeProvider>
        </body>
      </html>
    </Auth0Provider>
  )
}
