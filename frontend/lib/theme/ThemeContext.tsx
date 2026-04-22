"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

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

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("light")

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
    if (saved === "light" || saved === "dark") {
      apply(saved)
      setThemeState(saved)
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
      const initial: Theme = prefersDark ? "dark" : "light"
      apply(initial)
      setThemeState(initial)
    }
  }, [])

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
