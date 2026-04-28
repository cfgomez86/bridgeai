"use client"

import { useState } from "react"
import { Sun, Moon } from "lucide-react"
import { useLanguage } from "@/lib/i18n"
import type { Locale } from "@/lib/i18n"
import { useTheme } from "@/lib/theme/ThemeContext"
import type { Theme } from "@/lib/theme/ThemeContext"

const THEME_ICONS: Record<Theme, React.ReactNode> = {
  light: <Sun size={20} />,
  dark:  <Moon size={20} />,
}

const LOCALE_META: Record<Locale, { flag: string; name: string }> = {
  es: { flag: "🇪🇸", name: "Español" },
  en: { flag: "🇬🇧", name: "English" },
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
