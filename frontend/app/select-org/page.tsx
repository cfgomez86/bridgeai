"use client"

import { OrganizationList } from "@clerk/nextjs"
import { BrandHeader } from "@/components/features/BrandHeader"

export default function SelectOrgPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bg)",
      gap: "24px",
      padding: "24px",
    }}>
      <BrandHeader />
      <p style={{ fontSize: "14px", color: "var(--muted)", margin: 0, textAlign: "center" }}>
        Selecciona o crea tu organización para continuar
      </p>
      <OrganizationList
        afterSelectOrganizationUrl="/"
        afterCreateOrganizationUrl="/"
      />
    </div>
  )
}
