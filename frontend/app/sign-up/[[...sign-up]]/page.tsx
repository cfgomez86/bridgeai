import { SignUp } from "@clerk/nextjs"

export default function SignUpPage() {
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
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "36px", height: "36px",
            borderRadius: "10px",
            background: "rgba(255,255,255,0.18)",
            border: "1px solid rgba(255,255,255,0.28)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: 700,
          }}>B</div>
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.01em" }}>BridgeAI</span>
        </div>

        <div>
          <h1 style={{
            fontSize: "38px",
            fontWeight: 700,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
            margin: "0 0 16px 0",
          }}>
            Empieza gratis<br />hoy mismo
          </h1>
          <p style={{
            fontSize: "15px",
            opacity: 0.82,
            lineHeight: 1.6,
            margin: 0,
            maxWidth: "340px",
          }}>
            Crea tu cuenta y conecta tu repositorio en minutos. Sin tarjeta de crédito.
          </p>
        </div>

        <div style={{
          padding: "20px 24px",
          borderRadius: "12px",
          background: "rgba(255,255,255,0.12)",
          border: "1px solid rgba(255,255,255,0.2)",
          maxWidth: "360px",
        }}>
          <p style={{ fontSize: "13.5px", opacity: 0.9, lineHeight: 1.6, margin: 0, fontStyle: "italic" }}>
            &ldquo;BridgeAI redujo a la mitad el tiempo que pasábamos convirtiendo requisitos en tickets de Jira.&rdquo;
          </p>
          <p style={{ fontSize: "12px", opacity: 0.7, margin: "10px 0 0 0" }}>
            — Equipo de producto
          </p>
        </div>
      </div>

      {/* Form panel */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 40px",
        gap: "24px",
      }}>
        <div style={{ textAlign: "center" }}>
          <h2 style={{
            fontSize: "22px",
            fontWeight: 700,
            color: "var(--fg)",
            margin: "0 0 6px 0",
            letterSpacing: "-0.01em",
          }}>
            Crea tu cuenta
          </h2>
          <p style={{ fontSize: "13.5px", color: "var(--muted)", margin: 0 }}>
            Únete a BridgeAI y automatiza tu flujo
          </p>
        </div>

        <SignUp
          fallbackRedirectUrl="/select-org"
          appearance={{
            variables: {
              colorPrimary: "#6C5CE7",
              borderRadius: "6px",
              fontFamily: "Inter, system-ui, sans-serif",
            },
          }}
        />
      </div>
    </div>
  )
}
