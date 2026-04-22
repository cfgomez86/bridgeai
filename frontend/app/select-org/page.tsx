"use client"

import { OrganizationList } from "@clerk/nextjs"

export default function SelectOrgPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bg)",
      padding: "48px 24px",
      gap: "32px",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div style={{
          width: "40px", height: "40px",
          borderRadius: "11px",
          background: "linear-gradient(135deg, oklch(0.52 0.18 275) 0%, oklch(0.62 0.18 300) 100%)",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "white", fontSize: "18px", fontWeight: 700,
        }}>B</div>
        <span style={{ fontSize: "20px", fontWeight: 700, color: "var(--fg)", letterSpacing: "-0.01em" }}>
          BridgeAI
        </span>
      </div>

      <div style={{ textAlign: "center" }}>
        <h2 style={{
          fontSize: "22px",
          fontWeight: 700,
          color: "var(--fg)",
          margin: "0 0 8px 0",
          letterSpacing: "-0.01em",
        }}>
          Selecciona tu organización
        </h2>
        <p style={{ fontSize: "13.5px", color: "var(--muted)", margin: 0 }}>
          Elige o crea una organización para continuar
        </p>
      </div>

      <OrganizationList
        afterSelectOrganizationUrl="/"
        afterCreateOrganizationUrl="/"
        appearance={{
          variables: {
            colorPrimary: "#6C5CE7",
            borderRadius: "6px",
            fontFamily: "Inter, system-ui, sans-serif",
          },
        }}
      />
    </div>
  )
}
