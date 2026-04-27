"use client"

import { useRouter } from "next/navigation"
import { useUser } from "@auth0/nextjs-auth0/client"
import { useLanguage } from "@/lib/i18n"

type EventTone = "ok" | "accent" | "warn" | "neutral"

interface ActivityEvent {
  tone: EventTone
  title: string
  meta: string
  badge?: string
  time: string
}

const ACTIVITY_EVENTS: ActivityEvent[] = [
  { tone: "ok",      title: "REQ-284 -> Ticket AUTH-1204 creado en Jira",  meta: "apps/web/src/auth · 2 historias",                         time: "hace 12m" },
  { tone: "accent",  title: "REQ-283 — Historias generadas",               meta: "Export CSV · 3 historias · 8pt",                          time: "hace 48m" },
  { tone: "warn",    title: "REQ-281 — Análisis bloqueado",                meta: "Multi-tenant en /invoices · requiere indexar",            time: "hace 2h" },
  { tone: "neutral", title: "Conexión a Azure DevOps re-autorizada",       meta: "2 de 4 scopes activos · pendiente", badge: "work_items:write", time: "hace 5h" },
]

function EventIcon({ tone }: { tone: EventTone }) {
  return (
    <div style={{
      width: "28px", height: "28px", borderRadius: "7px", display: "grid", placeItems: "center", flexShrink: 0,
      background: tone === "ok" ? "var(--ok-bg)" : tone === "accent" ? "var(--accent-soft)" : tone === "warn" ? "var(--warn-bg)" : "var(--surface-2)",
      color: tone === "ok" ? "var(--ok-fg)" : tone === "accent" ? "var(--accent-strong)" : tone === "warn" ? "var(--warn-fg)" : "var(--fg-2)",
      border: (tone === "ok" || tone === "accent" || tone === "warn") ? "none" : "1px solid var(--border)",
    }}>
      {tone === "ok" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>}
      {tone === "accent" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 7h6M9 11h6M9 15h4"/></svg>}
      {tone === "warn" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="0.5" fill="currentColor"/></svg>}
      {tone === "neutral" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M21 2H3v16h5l3 3 3-3h7V2z"/></svg>}
    </div>
  )
}

function StepCircle({ done, num }: { done: boolean; num: number }) {
  return (
    <div style={{
      width: "28px", height: "28px", borderRadius: "50%", display: "grid", placeItems: "center",
      flexShrink: 0, background: done ? "var(--ok-fg)" : "var(--accent-soft)",
      color: done ? "#ffffff" : "var(--accent-strong)", border: "none",
      fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 600,
    }}>
      {done
        ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>
        : num
      }
    </div>
  )
}

export function DashboardView() {
  const { t } = useLanguage()
  const d = t.dashboard
  const router = useRouter()
  const { user } = useUser()

  const firstName = user?.name?.split(" ")[0] ?? user?.nickname ?? null

  const howItWorksSteps = [
    { done: true,  num: 1, title: d.howItWorks.step1.title, desc: d.howItWorks.step1.desc },
    { done: true,  num: 2, title: d.howItWorks.step2.title, desc: d.howItWorks.step2.desc },
    { done: false, num: 3, title: d.howItWorks.step3.title, desc: d.howItWorks.step3.desc },
    { done: false, num: 4, title: d.howItWorks.step4.title, desc: d.howItWorks.step4.desc },
  ]

  return (
    <div style={{ padding: "40px 48px", maxWidth: "1080px" }}>
      {/* Greeting */}
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "26px", fontWeight: 600, letterSpacing: "-0.02em", margin: "0 0 4px", color: "var(--fg)" }}>
          {firstName ? `${d.greeting} ${firstName}` : d.greetingNoName}
        </h1>
        <p style={{ margin: 0, fontSize: "14px", color: "var(--fg-2)" }}>
          Tienes{" "}
          <strong style={{ fontWeight: 600, color: "var(--fg)" }}>1 repo activo</strong>
          {" "}y{" "}
          <strong style={{ fontWeight: 600, color: "var(--fg)" }}>3 requerimientos</strong>
          {" "}esperando análisis.
        </p>
      </div>

      {/* Quick-start hero */}
      <div style={{
        background: "linear-gradient(135deg, var(--accent-soft), color-mix(in oklch, var(--accent-soft) 50%, var(--surface-2)))",
        border: "1px solid color-mix(in oklch, var(--accent) 25%, var(--border))",
        borderRadius: "var(--radius-xl)", padding: "28px", position: "relative", overflow: "hidden", marginBottom: "24px",
      }}>
        <div style={{ position: "absolute", top: "-40px", right: "-40px", width: "200px", height: "200px", background: "radial-gradient(circle, color-mix(in oklch, var(--accent) 15%, transparent) 0%, transparent 65%)", pointerEvents: "none" }} />
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: "20px", fontWeight: 600, letterSpacing: "-0.02em", margin: "0 0 8px", color: "var(--fg)", position: "relative" }}>
          {d.quickStartTitle}
        </h3>
        <p style={{ fontSize: "14px", color: "var(--fg-2)", margin: "0 0 20px", maxWidth: "540px", lineHeight: 1.55, position: "relative" }}>
          {d.quickStartLead}
        </p>
        <button
          onClick={() => router.push("/workflow")}
          style={{ display: "inline-flex", alignItems: "center", height: "38px", padding: "0 18px", borderRadius: "var(--radius)", border: "none", background: "var(--accent)", color: "var(--accent-fg)", fontFamily: "var(--font-display)", fontSize: "13.5px", fontWeight: 600, cursor: "pointer", letterSpacing: "-0.01em", position: "relative" }}
        >
          {d.startWorkflow}
        </button>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px", marginBottom: "24px" }}>
        {[
          { label: d.stats.requirements, value: "142", meta: d.stats.last30days },
          { label: d.stats.stories,      value: "318", meta: d.stats.last30days },
          { label: d.stats.tickets,      value: "89",  meta: d.stats.jiraAzure },
        ].map(({ label, value, meta }) => (
          <div key={label} style={{ padding: "18px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 600, color: "var(--muted)", textTransform: "uppercase" as const, letterSpacing: "0.14em", marginBottom: "4px" }}>{label}</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: "32px", fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1, color: "var(--fg)" }}>{value}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>{meta}</div>
          </div>
        ))}
      </div>

      {/* Bottom row */}
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "18px" }}>

        {/* Activity */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <h4 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "13.5px", fontWeight: 600, color: "var(--fg)" }}>{d.activity.title}</h4>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "11.5px", color: "var(--muted)", marginLeft: "auto" }}>{d.activity.meta}</span>
            <button style={{ padding: 0, border: "none", background: "transparent", color: "var(--accent-strong)", fontSize: "12px", fontWeight: 500, cursor: "pointer" }}>{d.activity.viewAll}</button>
          </div>
          <div>
            {ACTIVITY_EVENTS.map((ev, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "28px 1fr auto", gap: "10px", alignItems: "flex-start", padding: "10px 16px", borderTop: i === 0 ? "none" : "1px solid var(--border)" }}>
                <EventIcon tone={ev.tone} />
                <div>
                  <b style={{ fontSize: "13px", fontWeight: 500, display: "block", color: "var(--fg)" }}>{ev.title}</b>
                  <span style={{ fontSize: "11.5px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                    {ev.meta}
                    {ev.badge && (
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", padding: "1px 5px", background: "var(--warn-bg)", color: "var(--warn-fg)", borderRadius: "4px" }}>{ev.badge}</span>
                    )}
                  </span>
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--muted)", whiteSpace: "nowrap" as const, paddingTop: "4px" }}>{ev.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* How it works */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <h4 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "13.5px", fontWeight: 600, color: "var(--fg)" }}>{d.howItWorks.title}</h4>
          </div>
          <div>
            {howItWorksSteps.map((step, i) => (
              <div key={step.num} style={{ display: "grid", gridTemplateColumns: "28px 1fr", gap: "10px", padding: "10px 16px", borderTop: i === 0 ? "none" : "1px solid var(--border)", alignItems: "center" }}>
                <StepCircle done={step.done} num={step.num} />
                <div>
                  <b style={{ fontSize: "13px", fontWeight: 500, display: "block", color: "var(--fg)" }}>{step.title}</b>
                  <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>{step.desc}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
