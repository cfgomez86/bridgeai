const FEATURES = [
  "Análisis de impacto automático en tu codebase",
  "Historias de usuario con criterios Gherkin",
  "Integración directa con Jira y Azure DevOps",
  "Soporte para GitHub, GitLab, Azure y Bitbucket",
]

export default function SignInPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      background: "var(--bg)",
    }}>
      {/* Brand panel */}
      <div style={{
        background: "oklch(0.17 0.013 260)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "48px",
        color: "white",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "36px", height: "36px",
            borderRadius: "10px",
            background: "oklch(0.28 0.016 260)",
            border: "1px solid oklch(0.35 0.018 260)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: 700,
            color: "oklch(0.88 0.008 260)",
          }}>B</div>
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.01em", color: "oklch(0.92 0.005 260)" }}>
            BridgeAI
          </span>
        </div>

        <div>
          <h1 style={{
            fontSize: "36px",
            fontWeight: 700,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            margin: "0 0 16px 0",
            color: "oklch(0.96 0.004 260)",
          }}>
            De requisito<br />a ticket<br />en segundos
          </h1>
          <p style={{
            fontSize: "14px",
            color: "oklch(0.62 0.010 260)",
            lineHeight: 1.65,
            margin: 0,
            maxWidth: "340px",
          }}>
            Conecta tu repositorio, describe el requisito y BridgeAI genera
            historias listas para tu herramienta de gestión.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {FEATURES.map((f) => (
            <div key={f} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div style={{
                width: "16px", height: "16px", flexShrink: 0,
                borderRadius: "50%",
                background: "oklch(0.26 0.016 260)",
                border: "1px solid oklch(0.36 0.018 260)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "9px",
                color: "oklch(0.68 0.012 260)",
              }}>✓</div>
              <span style={{ fontSize: "13px", color: "oklch(0.60 0.010 260)", lineHeight: 1.4 }}>{f}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Login panel */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 40px",
        gap: "24px",
        background: "var(--bg)",
      }}>
        <div style={{ textAlign: "center" }}>
          <h2 style={{
            fontSize: "22px",
            fontWeight: 700,
            color: "var(--fg)",
            margin: "0 0 6px 0",
            letterSpacing: "-0.01em",
          }}>
            Bienvenido de vuelta
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--muted)", margin: 0 }}>
            Inicia sesión para continuar en BridgeAI
          </p>
        </div>

        <a
          href="/api/auth/login"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            maxWidth: "360px",
            padding: "12px 24px",
            borderRadius: "8px",
            background: "#6C5CE7",
            color: "white",
            fontWeight: 600,
            fontSize: "15px",
            textDecoration: "none",
            cursor: "pointer",
          }}
        >
          Ingresar
        </a>
      </div>
    </div>
  )
}
