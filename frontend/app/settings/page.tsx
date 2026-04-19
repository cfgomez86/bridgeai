"use client"

import { useState } from "react"
import { Sun, Moon } from "lucide-react"
import { Toggle } from "@/components/ui/toggle"
import { BadgeStatus } from "@/components/ui/badge-status"
import { useLanguage } from "@/lib/i18n"
import type { Locale } from "@/lib/i18n"
import { useTheme } from "@/lib/theme/ThemeContext"
import type { Theme } from "@/lib/theme/ThemeContext"

interface FieldRowProps {
  label: string
  defaultValue: string
  type?: string
  placeholder?: string
}

function FieldRow({ label, defaultValue, type = "text", placeholder }: FieldRowProps) {
  const [value, setValue] = useState(defaultValue)
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "12px", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <label style={{ width: "160px", fontSize: "12.5px", color: "var(--fg-2)", flexShrink: 0 }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        style={{
          flex: 1,
          padding: "5px 10px",
          borderRadius: "var(--radius)",
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--fg)",
          fontSize: "13px",
          outline: "none",
        }}
      />
    </div>
  )
}

interface ToggleRowProps {
  label: string
  description?: string
  defaultChecked: boolean
}

function ToggleRow({ label, description, defaultChecked }: ToggleRowProps) {
  const [checked, setChecked] = useState(defaultChecked)
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "10px 0",
      borderBottom: "1px solid var(--border)",
      gap: "12px",
    }}>
      <div>
        <div style={{ fontSize: "13px", color: "var(--fg)", fontWeight: 500 }}>{label}</div>
        {description && (
          <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>{description}</div>
        )}
      </div>
      <Toggle checked={checked} onChange={setChecked} />
    </div>
  )
}

interface IntegrationCardProps {
  children: React.ReactNode
  title: string
  subtitle?: string
  badge?: React.ReactNode
  icon: string
  saveLabel: string
}

function IntegrationCard({ children, title, subtitle, badge, icon, saveLabel }: IntegrationCardProps) {
  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      overflow: "hidden",
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{
        padding: "14px 18px",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}>
        <div style={{
          width: "36px",
          height: "36px",
          borderRadius: "8px",
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "11px",
          fontWeight: 700,
          color: "var(--fg-2)",
          fontFamily: "var(--font-mono)",
          flexShrink: 0,
        }}>{icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, fontFamily: "var(--font-display)", color: "var(--fg)" }}>
              {title}
            </span>
            {badge}
          </div>
          {subtitle && <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>{subtitle}</div>}
        </div>
        <button style={{
          padding: "5px 12px",
          borderRadius: "var(--radius)",
          border: "none",
          background: "var(--accent)",
          color: "var(--accent-fg)",
          fontSize: "12.5px",
          fontWeight: 500,
          cursor: "pointer",
        }}>
          {saveLabel}
        </button>
      </div>
      <div style={{ padding: "0 18px" }}>
        {children}
      </div>
    </div>
  )
}

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
  const [activeSection, setActiveSection] = useState("integraciones")

  const NAV_ITEMS = [
    { id: "integraciones", label: s.sections.integrations },
    { id: "generacion", label: s.sections.generation },
    { id: "idioma", label: s.sections.language },
    { id: "apariencia", label: s.sections.theme },
  ]

  const generationRules: { key: string; label: string; description: string; default?: boolean }[] = [
    { key: "max-stories", ...s.generation.rules.max_stories },
    { key: "gherkin", ...s.generation.rules.gherkin, default: true },
    { key: "story-points", ...s.generation.rules.story_points, default: true },
    { key: "link-files", ...s.generation.rules.link_files, default: true },
    { key: "auto-assign", ...s.generation.rules.auto_assign, default: false },
  ]

  return (
    <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", minHeight: "calc(100vh - 48px)" }}>
      {/* Left nav */}
      <nav style={{
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

      {/* Main content */}
      <div style={{ padding: "28px 32px", maxWidth: "760px", display: "flex", flexDirection: "column", gap: "24px" }}>
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

        {activeSection === "integraciones" && (
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 12px 0", fontFamily: "var(--font-display)" }}>
              {s.integrations.title}
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <IntegrationCard
                icon="JI"
                title="Jira Cloud"
                subtitle={s.integrations.jira.subtitle}
                badge={<BadgeStatus tone="ok" label={s.integrations.badge_active} />}
                saveLabel={s.integrations.save}
              >
                <FieldRow label={s.integrations.jira.workspace_url} defaultValue="https://acme.atlassian.net" />
                <FieldRow label={s.integrations.jira.project_key} defaultValue="PLAT" placeholder="PLAT" />
                <FieldRow label={s.integrations.jira.issue_type} defaultValue="Story" />
                <FieldRow label={s.integrations.jira.default_labels} defaultValue="bridgeai,auto-generated" />
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 0",
                }}>
                  <div>
                    <div style={{ fontSize: "13px", color: "var(--fg)", fontWeight: 500 }}>
                      {s.integrations.jira.draft_label}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                      {s.integrations.jira.draft_desc}
                    </div>
                  </div>
                  <Toggle checked={true} onChange={() => {}} />
                </div>
              </IntegrationCard>

              <IntegrationCard
                icon="AZ"
                title="Azure DevOps"
                subtitle={s.integrations.azure.subtitle}
                badge={<BadgeStatus tone="warn" label={s.integrations.badge_token_expiry} />}
                saveLabel={s.integrations.save}
              >
                <FieldRow label={s.integrations.azure.org_url} defaultValue="https://dev.azure.com/acme" />
                <FieldRow label={s.integrations.azure.project} defaultValue="Platform" />
                <FieldRow label={s.integrations.azure.area_path} defaultValue="Platform\\Backend" />
                <FieldRow label={s.integrations.azure.iteration_path} defaultValue="Platform\\Sprint 12" />
              </IntegrationCard>
            </div>
          </div>
        )}

        {activeSection === "generacion" && (
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 12px 0", fontFamily: "var(--font-display)" }}>
              {s.generation.title}
            </h2>
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "0 18px",
              boxShadow: "var(--shadow-sm)",
            }}>
              {generationRules.map((rule) =>
                rule.key === "max-stories" ? (
                  <div key={rule.key} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "13px", color: "var(--fg)", fontWeight: 500 }}>{rule.label}</div>
                      <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>{rule.description}</div>
                    </div>
                    <input
                      type="number"
                      defaultValue={3}
                      min={1}
                      max={10}
                      style={{
                        width: "60px",
                        padding: "5px 8px",
                        borderRadius: "var(--radius)",
                        border: "1px solid var(--border)",
                        background: "var(--surface)",
                        color: "var(--fg)",
                        fontSize: "13px",
                        outline: "none",
                        textAlign: "center",
                        fontFamily: "var(--font-mono)",
                      }}
                    />
                  </div>
                ) : (
                  <ToggleRow
                    key={rule.key}
                    label={rule.label}
                    description={rule.description}
                    defaultChecked={rule.default ?? false}
                  />
                )
              )}
            </div>
          </div>
        )}

        {activeSection === "idioma" && <LanguageSection />}
        {activeSection === "apariencia" && <ThemeSection />}
      </div>
    </div>
  )
}
