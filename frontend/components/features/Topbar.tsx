"use client"

import { usePathname } from "next/navigation"
import { useLanguage } from "@/lib/i18n"
import { useUser } from "@auth0/nextjs-auth0/client"

export function Topbar() {
  const pathname = usePathname()
  const { t } = useLanguage()
  const { user } = useUser()

  const segments = pathname.split("/").filter(Boolean)

  const ROUTE_LABELS: Record<string, string> = {
    workflow: t.nav.workflow,
    indexing: t.nav.indexing,
    connections: t.nav.connections,
    settings: t.nav.settings,
  }

  const crumbs: { label: string; href: string }[] = [{ label: "BridgeAI", href: "/" }]
  let cumulative = ""
  for (const seg of segments) {
    cumulative += "/" + seg
    const label = ROUTE_LABELS[seg]
    if (label) crumbs.push({ label, href: cumulative })
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

      {/* User menu */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {user && (
          <span style={{ fontSize: "13px", color: "var(--muted)" }}>
            {user.email}
          </span>
        )}
        <a
          href="/api/auth/logout"
          style={{
            fontSize: "13px",
            color: "var(--muted)",
            textDecoration: "none",
            padding: "4px 10px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          Salir
        </a>
      </div>
    </header>
  )
}
