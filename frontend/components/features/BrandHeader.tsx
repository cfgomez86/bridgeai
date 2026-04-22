export function BrandHeader() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <div style={{
        width: "32px",
        height: "32px",
        borderRadius: "8px",
        background: "linear-gradient(135deg, var(--accent) 0%, oklch(0.62 0.18 300) 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "white",
        fontSize: "15px",
        fontWeight: 700,
      }}>B</div>
      <span style={{ fontSize: "18px", fontWeight: 700, color: "var(--fg)" }}>BridgeAI</span>
    </div>
  )
}
