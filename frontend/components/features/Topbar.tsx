"use client"

import { usePathname } from "next/navigation"

const ROUTE_LABELS: Record<string, string> = {
  "": "Inicio",
  "workflow": "Workflow",
  "indexing": "Indexado",
  "connections": "Conexiones",
  "settings": "Ajustes",
}

function SearchIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.5 10.5l3 3" />
    </svg>
  )
}

export function Topbar() {
  const pathname = usePathname()
  const segments = pathname.split("/").filter(Boolean)

  const crumbs: { label: string; href: string }[] = [{ label: "BridgeAI", href: "/" }]
  let cumulative = ""
  for (const seg of segments) {
    cumulative += "/" + seg
    crumbs.push({ label: ROUTE_LABELS[seg] ?? seg, href: cumulative })
  }

  return (
    <header style={{
      height: "48px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 20px",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      backdropFilter: "blur(8px)",
      position: "sticky",
      top: 0,
      zIndex: 20,
      flexShrink: 0,
    }}>
      {/* Breadcrumbs */}
      <nav style={{ display: "flex", alignItems: "center", gap: "4px" }}>
        {crumbs.map((crumb, i) => (
          <span key={crumb.href} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {i > 0 && (
              <span style={{ color: "var(--muted-2)", fontSize: "13px" }}>/</span>
            )}
            <span style={{
              fontSize: "13px",
              color: i === crumbs.length - 1 ? "var(--fg)" : "var(--muted)",
              fontWeight: i === crumbs.length - 1 ? 500 : 400,
            }}>
              {crumb.label}
            </span>
          </span>
        ))}
      </nav>

      {/* Search kbar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        minWidth: "220px",
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: "6px",
        padding: "4px 8px",
        cursor: "pointer",
      }}>
        <span style={{ color: "var(--muted)", flexShrink: 0 }}><SearchIcon /></span>
        <span style={{ fontSize: "12.5px", color: "var(--muted)", flex: 1 }}>
          Buscar requerimientos, archivos…
        </span>
        <kbd style={{
          fontSize: "10.5px",
          color: "var(--muted-2)",
          background: "var(--surface-3)",
          border: "1px solid var(--border)",
          borderRadius: "3px",
          padding: "1px 5px",
          fontFamily: "var(--font-mono)",
        }}>⌘K</kbd>
      </div>
    </header>
  )
}
