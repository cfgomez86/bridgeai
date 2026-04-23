import type { Metadata } from "next"
import "./globals.css"
import { UserProvider } from "@auth0/nextjs-auth0/client"
import { LanguageProvider } from "@/lib/i18n"
import { ThemeProvider } from "@/lib/theme/ThemeContext"
import { Auth0TokenSync } from "@/components/features/Auth0TokenSync"
import { AppShell } from "@/components/features/AppShell"

export const metadata: Metadata = {
  title: "BridgeAI",
  description: "Requirement to ticket automation",
}

const themeScript = `(function(){try{var t=localStorage.getItem('bridgeai-theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}}catch(e){}})();`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <UserProvider>
      {/* suppressHydrationWarning: server renders without .dark; blocking script may add it before hydration */}
      <html lang="es" suppressHydrationWarning>
        <head>
          {/* Blocking script — runs before CSS paint to avoid flash of light theme */}
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
    </UserProvider>
  )
}
