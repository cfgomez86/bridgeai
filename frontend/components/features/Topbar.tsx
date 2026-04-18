"use client"

import { usePathname } from "next/navigation"

const ROUTE_LABELS: Record<string, string> = {
  "": "Inicio",
  "workflow": "Workflow",
  "indexing": "Indexado",
  "connections": "Conexiones",
  "settings": "Ajustes",
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
    </header>
  )
}
