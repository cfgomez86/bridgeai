"use client"

import React, { createContext, useContext, useState } from "react"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Theme = "light" | "dark"

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)
const STORAGE_KEY = "bridgeai-theme"

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

// Read initial theme from the DOM class set by the blocking <script> in layout.tsx.
// This avoids a "light → dark" flash on hydration because the DOM already has the
// correct class before React mounts.
function getInitialTheme(): Theme {
  if (typeof document === "undefined") return "light"
  return document.documentElement.classList.contains("dark") ? "dark" : "light"
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  function apply(t: Theme) {
    document.documentElement.classList.toggle("dark", t === "dark")
  }

  function setTheme(t: Theme) {
    setThemeState(t)
    apply(t)
    localStorage.setItem(STORAGE_KEY, t)
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}
