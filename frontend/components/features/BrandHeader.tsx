export function BrandHeader() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <div style={{
        width: "34px", height: "34px", borderRadius: "9px",
        background: "linear-gradient(135deg, var(--accent) 0%, oklch(0.62 0.18 300) 100%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
        boxShadow: "0 2px 8px oklch(0.55 0.22 260 / 0.35)",
      }}>
        <svg width="22" height="20" viewBox="0 0 32 28" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Arch fill */}
          <path d="M3 22 Q16 2 29 22 Z" fill="white" fillOpacity="0.15" />
          {/* Main arch */}
          <path d="M3 22 Q16 2 29 22" stroke="white" strokeWidth="2.4" strokeLinecap="round" />
          {/* Left pillar */}
          <line x1="3" y1="22" x2="3" y2="27" stroke="white" strokeWidth="2.4" strokeLinecap="round" />
          {/* Right pillar */}
          <line x1="29" y1="22" x2="29" y2="27" stroke="white" strokeWidth="2.4" strokeLinecap="round" />
          {/* Road deck */}
          <line x1="1" y1="22" x2="31" y2="22" stroke="white" strokeWidth="2" strokeLinecap="round" />
          {/* Center vertical cable */}
          <line x1="16" y1="6" x2="16" y2="22" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeOpacity="0.6" />
        </svg>
      </div>
      <span style={{
        fontSize: "17px", fontWeight: 700, color: "var(--fg)",
        letterSpacing: "-0.02em", fontFamily: "var(--font-display)",
      }}>
        BridgeAI
      </span>
    </div>
  )
}
