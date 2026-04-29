"use client"

import React, { useState } from "react"
import { Sun, Moon } from "lucide-react"
import { useLanguage } from "@/lib/i18n"
import type { Locale } from "@/lib/i18n"
import { useTheme } from "@/lib/theme/ThemeContext"
import type { Theme } from "@/lib/theme/ThemeContext"

const THEME_ICONS: Record<Theme, React.ReactNode> = {
  light: <Sun size={20} />,
  dark:  <Moon size={20} />,
}

const FLAG_STYLE: React.CSSProperties = { width: 28, height: 20, borderRadius: 2, display: "block" }

const SpainFlag = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 2" style={FLAG_STYLE}>
    <rect width="3" height="2" fill="#AA151B"/>
    <rect y="0.5" width="3" height="1" fill="#F1BF00"/>
  </svg>
)

const UKFlag = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30" style={FLAG_STYLE}>
    <rect width="60" height="30" fill="#012169"/>
    <line x1="0" y1="0" x2="60" y2="30" stroke="white" strokeWidth="6"/>
    <line x1="60" y1="0" x2="0" y2="30" stroke="white" strokeWidth="6"/>
    <polygon points="0,0 0,2 29,15 30,12" fill="#C8102E"/>
    <polygon points="60,30 60,28 31,15 30,18" fill="#C8102E"/>
    <polygon points="60,0 58,0 30,12 32,15" fill="#C8102E"/>
    <polygon points="0,30 2,30 30,18 28,15" fill="#C8102E"/>
    <rect x="24" y="0" width="12" height="30" fill="white"/>
    <rect x="0" y="12" width="60" height="6" fill="white"/>
    <rect x="26" y="0" width="8" height="30" fill="#C8102E"/>
    <rect x="0" y="13" width="60" height="4" fill="#C8102E"/>
  </svg>
)

const CatalanFlag = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 60" style={FLAG_STYLE}>
    <rect width="90" height="60" fill="#FCDD09"/>
    <rect y="6.667" width="90" height="6.667" fill="#DA121A"/>
    <rect y="20" width="90" height="6.667" fill="#DA121A"/>
    <rect y="33.333" width="90" height="6.667" fill="#DA121A"/>
    <rect y="46.667" width="90" height="6.667" fill="#DA121A"/>
  </svg>
)

const LOCALE_META: Record<Locale, { flag: React.ReactNode; name: string }> = {
  es: { flag: <SpainFlag />, name: "Español" },
  en: { flag: <UKFlag />, name: "English" },
  ca: { flag: <CatalanFlag />, name: "Català" },
}

function ThemeSection() {
  const { theme, setTheme } = useTheme()
  const { t } = useLanguage()
  const s = t.settings.theme

  return (
    <div>
      <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 6px 0", fontFamily: "var(--font-display)" }}>
        {s.title}
      </h2>
      <p style={{ fontSize: "13px", color: "var(--muted)", margin: "0 0 18px 0" }}>
        {s.description}
      </p>
      <div style={{ display: "flex", gap: "12px" }}>
        {(Object.keys(THEME_ICONS) as Theme[]).map((th) => {
          const isActive = theme === th
          return (
            <button
              key={th}
              onClick={() => setTheme(th)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "12px 20px",
                borderRadius: "var(--radius-lg)",
                border: isActive ? "2px solid var(--accent)" : "2px solid var(--border)",
                background: isActive ? "var(--accent-soft)" : "var(--surface)",
                color: isActive ? "var(--accent-strong)" : "var(--fg)",
                cursor: "pointer",
                fontSize: "13.5px",
                fontWeight: isActive ? 600 : 400,
                transition: "border-color 0.15s, background 0.15s",
                boxShadow: isActive ? "0 0 0 3px var(--accent-soft)" : "none",
              }}
            >
              {THEME_ICONS[th]}
              <span>{s.options[th]}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function LanguageSection() {
  const { locale, setLocale, t } = useLanguage()
  const s = t.settings.language

  return (
    <div>
      <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 6px 0", fontFamily: "var(--font-display)" }}>
        {s.title}
      </h2>
      <p style={{ fontSize: "13px", color: "var(--muted)", margin: "0 0 18px 0" }}>
        {s.description}
      </p>
      <div style={{ display: "flex", gap: "12px" }}>
        {(Object.keys(LOCALE_META) as Locale[]).map((loc) => {
          const { flag, name } = LOCALE_META[loc]
          const isActive = locale === loc
          return (
            <button
              key={loc}
              onClick={() => setLocale(loc)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "12px 20px",
                borderRadius: "var(--radius-lg)",
                border: isActive ? "2px solid var(--accent)" : "2px solid var(--border)",
                background: isActive ? "var(--accent-soft)" : "var(--surface)",
                color: isActive ? "var(--accent-strong)" : "var(--fg)",
                cursor: "pointer",
                fontSize: "13.5px",
                fontWeight: isActive ? 600 : 400,
                transition: "border-color 0.15s, background 0.15s",
                boxShadow: isActive ? "0 0 0 3px var(--accent-soft)" : "none",
              }}
            >
              <span style={{ fontSize: "22px", lineHeight: 1 }}>{flag}</span>
              <span>{name}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const { t } = useLanguage()
  const s = t.settings
  const [activeSection, setActiveSection] = useState("idioma")

  const NAV_ITEMS = [
    { id: "idioma", label: s.sections.language },
    { id: "apariencia", label: s.sections.theme },
  ]

  return (
    <div className="grid-connections-layout">
      {/* Left nav — hidden on mobile */}
      <nav className="desktop-side-nav" style={{
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        padding: "16px 8px",
        position: "sticky",
        top: "48px",
        height: "calc(100vh - 48px)",
        overflow: "auto",
      }}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === activeSection
          return (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "6px 10px",
                borderRadius: "5px",
                border: "none",
                background: isActive ? "var(--accent-soft)" : "transparent",
                color: isActive ? "var(--accent-strong)" : "var(--fg-2)",
                fontSize: "13px",
                fontWeight: isActive ? 500 : 400,
                cursor: "pointer",
                marginBottom: "1px",
              }}
            >
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* Content column */}
      <div>
        {/* Mobile tabs — shown only on mobile */}
        <div className="mobile-nav-tabs">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={item.id === activeSection ? "tab-active" : undefined}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Main content */}
        <div className="page-content" style={{ maxWidth: "760px", display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Section title */}
        <div>
          <h1 style={{
            fontSize: "20px",
            fontWeight: 700,
            fontFamily: "var(--font-display)",
            color: "var(--fg)",
            margin: 0,
            letterSpacing: "-0.01em",
          }}>
            {NAV_ITEMS.find((n) => n.id === activeSection)?.label}
          </h1>
        </div>

        {activeSection === "idioma" && <LanguageSection />}
        {activeSection === "apariencia" && <ThemeSection />}
        </div>
      </div>
    </div>
  )
}
