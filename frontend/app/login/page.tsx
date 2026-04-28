import { GitHubLogo, GitLabLogo, AzureLogo, BitbucketLogo, JiraLogo } from "@/components/features/connections/PlatformLogos"

// Login page — public, no Auth0Provider in tree, no useLanguage().
// Strings are hardcoded in Spanish as per design spec.

const PIPELINE_STEPS = [
  { n: "01", title: "Entiende",  out: '"Migrar auth a OAuth2"',       active: false },
  { n: "02", title: "Impacta",   out: "12 archivos · backend & frontend", active: true },
  { n: "03", title: "Genera",    out: "1 historia + 6 subtareas",      active: false },
  { n: "04", title: "Entrega",   out: "-> AUTH-1204 (Jira)",           active: false },
]

export default function LoginPage() {
  return (
    <div className="login-page-grid" style={{ fontFamily: "var(--font-sans)" }}>
      {/* Left column — decorative, hidden on mobile */}
      <div className="login-left-col" style={{
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        padding: "64px 56px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        position: "relative",
        overflow: "hidden",
        minHeight: "100vh",
      }}>
        {/* Blob */}
        <div style={{
          position: "absolute",
          top: "-100px",
          right: "-100px",
          width: "360px",
          height: "360px",
          borderRadius: "50%",
          background: "radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "9px", position: "relative", zIndex: 1 }}>
          <div style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "var(--accent-soft)", display: "grid", placeItems: "center",
            color: "var(--accent-strong)", flexShrink: 0,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 6L3 12l6 6" /><path d="M15 6l6 6-6 6" /><path d="M14 5l-4 14" />
            </svg>
          </div>
          <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "14px", color: "var(--fg)", letterSpacing: "-0.01em" }}>BridgeAI</span>
        </div>

        {/* Hero */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
            <div style={{ width: "18px", height: "1px", background: "var(--accent)", flexShrink: 0 }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" as const, color: "var(--muted)" }}>
              Plataforma para equipos de ingeniería
            </span>
          </div>

          <h1 style={{
            fontFamily: "var(--font-display)", fontSize: "44px", fontWeight: 600,
            lineHeight: 1.05, letterSpacing: "-0.03em", margin: "0 0 16px", color: "var(--fg)",
          }}>
            De requisitos<br />a tickets,{" "}
            <em style={{
              fontStyle: "normal",
              background: "linear-gradient(135deg, var(--accent), var(--accent-grad-2))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}>
              con IA<br />que entiende tu código.
            </em>
          </h1>

          <p style={{ fontSize: "15px", color: "var(--fg-2)", margin: "0 0 28px", maxWidth: "460px", lineHeight: 1.55 }}>
            BridgeAI lee tu repo, entiende qué pides, calcula impacto real en archivos y crea historias listas para Jira o Azure DevOps en menos de un minuto.
          </p>

          {/* Pipeline card */}
          <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
              <span style={{
                width: "6px", height: "6px", borderRadius: "50%",
                background: "var(--ok-fg)", display: "inline-block",
                animation: "pdot 2s infinite",
              }} />
              <style>{`@keyframes pdot { 0%,100% { opacity:1 } 50% { opacity:.35 } }`}</style>
              <span style={{ fontFamily: "var(--font-display)", fontSize: "13px", fontWeight: 600, color: "var(--fg)" }}>Pipeline en vivo</span>
              <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: "10.5px", color: "var(--muted)" }}>— ejemplo —</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px" }}>
              {PIPELINE_STEPS.map(({ n, title, out, active }) => (
                <div key={n} style={{
                  background: active ? "var(--accent-soft)" : "var(--surface)",
                  border: active ? "1px solid var(--accent)" : "1px solid var(--border)",
                  borderRadius: "8px", padding: "10px 10px 9px",
                }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", fontWeight: 600, color: "var(--accent)" }}>{n}</div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "12.5px", fontWeight: 600, marginTop: "2px", color: "var(--fg)" }}>{title}</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: active ? "var(--accent-strong)" : "var(--muted)", marginTop: "4px", lineHeight: 1.3 }}>{out}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ position: "relative", zIndex: 1 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--muted-2)" }}>© 2026 BridgeAI</span>
        </div>
      </div>

      {/* Right column */}
      <div className="login-right-col" style={{
        background: "var(--surface-2)", padding: "64px 56px",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        minHeight: "100vh",
      }}>
        <div style={{ width: "100%", maxWidth: "380px" }}>
          {/* Mobile brand — shown only when left column is hidden */}
          <div className="login-mobile-brand">
            <div style={{
              width: "30px", height: "30px", borderRadius: "8px",
              background: "var(--accent-soft)", display: "grid", placeItems: "center",
              color: "var(--accent-strong)", flexShrink: 0,
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 6L3 12l6 6" /><path d="M15 6l6 6-6 6" /><path d="M14 5l-4 14" />
              </svg>
            </div>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "16px", color: "var(--fg)", letterSpacing: "-0.01em" }}>BridgeAI</span>
          </div>

          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "28px", fontWeight: 600, letterSpacing: "-0.02em", margin: "0 0 6px", color: "var(--fg)" }}>
            Bienvenido
          </h2>
          <p style={{ fontSize: "14px", color: "var(--fg-2)", margin: "0 0 24px" }}>
            Inicia sesión para acceder a tu workspace.
          </p>

          <a href="/api/auth/login" style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
            width: "100%", height: "44px", borderRadius: "var(--radius)",
            background: "var(--accent)", color: "var(--accent-fg)",
            fontWeight: 600, fontSize: "14px", fontFamily: "var(--font-display)",
            textDecoration: "none", letterSpacing: "-0.01em",
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
              <path d="M9 12l2 2 4-4" /><circle cx="12" cy="12" r="9" />
            </svg>
            Continuar con Auth0
          </a>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", margin: "18px 0", color: "var(--muted-2)" }}>
            <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "10.5px", textTransform: "uppercase" as const, letterSpacing: "0.18em", whiteSpace: "nowrap" as const }}>
              Inicio de sesión seguro
            </span>
            <div style={{ flex: 1, height: "1px", background: "var(--border)" }} />
          </div>

          <div className="grid-2col" style={{ gap: "10px" }}>
            {/* Conecta tu repo */}
            <div style={{ padding: "12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              <div style={{ display: "flex", gap: "4px", marginBottom: "8px" }}>
                {[
                  { el: <GitHubLogo size={15} />, accent: true },
                  { el: <GitLabLogo size={15} />, accent: false },
                  { el: <AzureLogo size={15} />, accent: false },
                  { el: <BitbucketLogo size={15} />, accent: false },
                ].map(({ el, accent }, i) => (
                  <div key={i} style={{
                    width: "26px", height: "26px", borderRadius: "6px",
                    background: accent ? "var(--accent-soft)" : "var(--surface-2)",
                    border: accent ? "none" : "1px solid var(--border)",
                    display: "grid", placeItems: "center",
                    color: accent ? "var(--accent-strong)" : "var(--fg-2)",
                  }}>{el}</div>
                ))}
              </div>
              <b style={{ display: "block", fontFamily: "var(--font-display)", fontSize: "12.5px", fontWeight: 600, color: "var(--fg)" }}>Conecta tu repo</b>
              <span style={{ fontSize: "10.5px", color: "var(--muted)" }}>OAuth o PAT · 4 plataformas</span>
            </div>

            {/* Tickets en un clic */}
            <div style={{ padding: "12px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", marginBottom: "8px", height: "26px" }}>
                <div style={{ padding: "4px 8px", background: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--fg-2)", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "9.5px", fontWeight: 600, letterSpacing: "0.04em" }}>REQ</div>
                <span style={{ color: "var(--muted-2)", fontSize: "11px" }}>→</span>
                <div style={{ width: "26px", height: "26px", borderRadius: "6px", background: "var(--surface-2)", border: "1px solid var(--border)", display: "grid", placeItems: "center" }}><JiraLogo size={15} /></div>
                <div style={{ width: "26px", height: "26px", borderRadius: "6px", background: "var(--surface-2)", border: "1px solid var(--border)", display: "grid", placeItems: "center" }}><AzureLogo size={15} /></div>
              </div>
              <b style={{ display: "block", fontFamily: "var(--font-display)", fontSize: "12.5px", fontWeight: 600, color: "var(--fg)" }}>Tickets en un clic</b>
              <span style={{ fontSize: "10.5px", color: "var(--muted)" }}>Jira &amp; Azure DevOps</span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "24px", padding: "10px 12px", background: "var(--surface-3)", border: "1px solid var(--border)", borderRadius: "var(--radius)", fontSize: "11.5px", color: "var(--muted)" }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" style={{ flexShrink: 0, color: "var(--muted)" }} aria-hidden="true">
              <path d="M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.623C17.176 19.29 21 14.59 21 9a12.02 12.02 0 00-.382-3.016z" />
            </svg>
            Tu código nunca abandona los repos que tú autorices.
          </div>
        </div>
      </div>
    </div>
  )
}
