"use client"

import { useState } from "react"
import { Toggle } from "@/components/ui/toggle"
import { BadgeStatus } from "@/components/ui/badge-status"

type NavItem = {
  id: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { id: "integraciones", label: "Integraciones" },
  { id: "generacion", label: "Generación de historias" },
]

const NAV_LABEL: Record<string, string> = Object.fromEntries(NAV_ITEMS.map((n) => [n.id, n.label]))

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
}

function IntegrationCard({ children, title, subtitle, badge, icon }: IntegrationCardProps) {
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
          Guardar
        </button>
      </div>
      <div style={{ padding: "0 18px" }}>
        {children}
      </div>
    </div>
  )
}

const GENERATION_RULES = [
  { label: "Máx. historias por requerimiento", description: "Limita el número de historias generadas por análisis", key: "max-stories" },
  { label: "Criterios de aceptación en Gherkin", description: "Usar formato Given/When/Then", key: "gherkin", default: true },
  { label: "Estimar story points", description: "Calcular puntos de historia automáticamente", key: "story-points", default: true },
  { label: "Vincular archivos afectados", description: "Adjuntar lista de archivos del análisis de impacto", key: "link-files", default: true },
  { label: "Asignación automática", description: "Asignar al desarrollador más activo en los archivos", key: "auto-assign", default: false },
]

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("integraciones")

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
            textTransform: "capitalize",
          }}>
            {NAV_LABEL[activeSection]}
          </h1>
        </div>

        {activeSection === "integraciones" && (
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 12px 0", fontFamily: "var(--font-display)" }}>
              Integraciones
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {/* Jira Cloud */}
                <IntegrationCard
                  icon="JI"
                  title="Jira Cloud"
                  subtitle="Crea issues directamente en tu proyecto de Jira"
                  badge={<BadgeStatus tone="ok" label="Activo" />}
                >
                  <FieldRow label="URL del workspace" defaultValue="https://acme.atlassian.net" />
                  <FieldRow label="Proyecto (clave)" defaultValue="PLAT" placeholder="PLAT" />
                  <FieldRow label="Tipo de issue" defaultValue="Story" />
                  <FieldRow label="Etiquetas por defecto" defaultValue="bridgeai,auto-generated" />
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 0",
                  }}>
                    <div>
                      <div style={{ fontSize: "13px", color: "var(--fg)", fontWeight: 500 }}>Crear como draft</div>
                      <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                        Las historias se crean en estado borrador para revisión previa
                      </div>
                    </div>
                    <Toggle checked={true} onChange={() => {}} />
                  </div>
                </IntegrationCard>

                {/* Azure DevOps */}
                <IntegrationCard
                  icon="AZ"
                  title="Azure DevOps"
                  subtitle="Integración con Azure Boards"
                  badge={<BadgeStatus tone="warn" label="Token expira en 5d" />}
                >
                  <FieldRow label="Organización URL" defaultValue="https://dev.azure.com/acme" />
                  <FieldRow label="Proyecto" defaultValue="Platform" />
                  <FieldRow label="Area Path" defaultValue="Platform\\Backend" />
                  <FieldRow label="Iteration Path" defaultValue="Platform\\Sprint 12" />
                </IntegrationCard>
            </div>
          </div>
        )}

        {activeSection === "generacion" && (
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: 600, color: "var(--fg)", margin: "0 0 12px 0", fontFamily: "var(--font-display)" }}>
              Reglas de generación
            </h2>
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "0 18px",
              boxShadow: "var(--shadow-sm)",
            }}>
              {GENERATION_RULES.map((rule) =>
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

      </div>
    </div>
  )
}
