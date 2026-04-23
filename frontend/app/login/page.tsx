const STEPS = [
  { n: "01", title: "Entiende", desc: "La IA extrae intención, complejidad y términos clave de tu requisito." },
  { n: "02", title: "Impacta", desc: "Cruza tu codebase para identificar archivos y módulos afectados." },
  { n: "03", title: "Genera", desc: "Produce la historia de usuario con criterios, tareas y story points." },
  { n: "04", title: "Entrega", desc: "Crea el ticket en Jira o Azure DevOps con un solo clic." },
]

export default function LoginPage() {

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      fontFamily: "var(--font-sans)",
    }}>

      {/* ── Left: identity panel — same surface as sidebar ── */}
      <div style={{
        background: "var(--surface-2)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "48px",
        minHeight: "100vh",
      }}>

        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{
            width: "28px", height: "28px", borderRadius: "7px",
            background: "linear-gradient(135deg, var(--accent) 0%, oklch(0.62 0.18 300) 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "white", fontSize: "13px", fontWeight: 700,
            fontFamily: "var(--font-display)",
          }}>B</div>
          <span style={{
            fontSize: "14px", fontWeight: 600, color: "var(--fg)",
            fontFamily: "var(--font-display)", letterSpacing: "-0.01em",
          }}>BridgeAI</span>
        </div>

        {/* Hero text */}
        <div>
          <p style={{
            color: "var(--muted-2)", fontSize: "11px", fontWeight: 600,
            letterSpacing: "0.10em", textTransform: "uppercase", marginBottom: "16px",
          }}>
            Plataforma de automatización
          </p>
          <h1 style={{
            color: "var(--fg)", fontSize: "clamp(26px, 3vw, 38px)", fontWeight: 700,
            fontFamily: "var(--font-display)", lineHeight: 1.15,
            letterSpacing: "-0.03em", margin: "0 0 32px",
          }}>
            De requisitos<br />a tickets,<br />con IA.
          </h1>

          {/* Steps */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {STEPS.map(({ n, title, desc }) => (
              <div key={n} style={{ display: "flex", gap: "14px", alignItems: "flex-start" }}>
                <span style={{
                  color: "var(--accent)", fontSize: "10px", fontWeight: 600,
                  fontFamily: "var(--font-mono)", lineHeight: "20px", flexShrink: 0,
                }}>{n}</span>
                <div>
                  <div style={{
                    color: "var(--fg-2)", fontSize: "13px", fontWeight: 600, lineHeight: 1.3,
                  }}>
                    {title}
                  </div>
                  <div style={{
                    color: "var(--muted)", fontSize: "12px", lineHeight: 1.5, marginTop: "2px",
                  }}>
                    {desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p style={{ color: "var(--muted-2)", fontSize: "11px" }}>
          © {new Date().getFullYear()} BridgeAI
        </p>
      </div>

      {/* ── Right: sign-in panel ── */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px",
        background: "var(--bg)",
      }}>

        <div style={{ width: "100%", maxWidth: "320px" }}>
          <h2 style={{
            fontSize: "20px", fontWeight: 700, color: "var(--fg)",
            fontFamily: "var(--font-display)", letterSpacing: "-0.02em",
            margin: "0 0 6px",
          }}>
            Bienvenido
          </h2>
          <p style={{ fontSize: "13px", color: "var(--muted)", margin: "0 0 28px" }}>
            Inicia sesión para acceder a tu workspace
          </p>

          <a
            href="/api/auth/login"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "100%",
              padding: "10px 20px",
              borderRadius: "var(--radius)",
              background: "var(--accent)",
              color: "var(--accent-fg)",
              fontWeight: 600,
              fontSize: "14px",
              textDecoration: "none",
              fontFamily: "var(--font-display)",
              letterSpacing: "-0.01em",
            }}
          >
            Ingresar
          </a>
        </div>

      </div>
    </div>
  )
}
