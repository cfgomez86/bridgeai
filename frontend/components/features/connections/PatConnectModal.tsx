"use client"

import { useState } from "react"
import { X, Loader2, HelpCircle } from "lucide-react"
import { createPatConnection } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface PatConnectModalProps {
  platform: string
  isOpen: boolean
  onClose: () => void
  onConnected: () => void
  onOpenHelp?: () => void
}

export function PatConnectModal({ platform, isOpen, onClose, onConnected, onOpenHelp }: PatConnectModalProps) {
  const [token, setToken] = useState("")
  const [orgUrl, setOrgUrl] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t, locale } = useLanguage()
  const s = t.connections.pat

  if (!isOpen) return null

  const isAzure = platform === "azure_devops"
  const isGitlab = platform === "gitlab"
  const isGithub = platform === "github"
  const isBitbucket = platform === "bitbucket"
  const isDisabled = loading || !token.trim()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token.trim()) return

    setLoading(true)
    setError(null)
    try {
      await createPatConnection(
        platform,
        token.trim(),
        isAzure ? orgUrl.trim() || undefined : undefined,
        (isGitlab || isGithub || isBitbucket) ? baseUrl.trim() || undefined : undefined,
      )
      onConnected()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al conectar.")
    } finally {
      setLoading(false)
    }
  }

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose()
  }

  const labelStyle: React.CSSProperties = {
    fontSize: "12.5px",
    fontWeight: 500,
    color: "var(--fg-2)",
    marginBottom: "4px",
    display: "block",
  }

  const inputStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    padding: "7px 10px",
    borderRadius: "var(--radius)",
    border: "1px solid var(--border)",
    background: "var(--surface-2)",
    color: "var(--fg)",
    fontSize: "13px",
    outline: "none",
    fontFamily: "var(--font-mono)",
  }

  return (
    <div
      onClick={handleBackdropClick}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.45)",
      }}
    >
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        width: "100%",
        maxWidth: "440px",
        margin: "0 16px",
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 18px",
          borderBottom: "1px solid var(--border)",
        }}>
          <h2 style={{
            fontSize: "14px",
            fontWeight: 600,
            color: "var(--fg)",
            margin: 0,
            fontFamily: "var(--font-display)",
          }}>
            {s.modal_title}
          </h2>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            {onOpenHelp && (
              <button
                type="button"
                onClick={onOpenHelp}
                title={locale === "en" ? "How to generate a token" : "Cómo generar el token"}
                style={{
                  display: "flex", alignItems: "center", gap: "4px",
                  padding: "4px 8px", borderRadius: "var(--radius)",
                  border: "none", background: "transparent",
                  color: "var(--muted)", cursor: "pointer",
                  fontSize: "11.5px",
                }}
              >
                <HelpCircle size={13} />
                {locale === "en" ? "Guide" : "Ver guía"}
              </button>
            )}
          <button
            type="button"
            onClick={onClose}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "28px",
              height: "28px",
              borderRadius: "var(--radius)",
              border: "none",
              background: "transparent",
              color: "var(--muted)",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "18px", display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={labelStyle}>{s.token_label}</label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={s.token_placeholder}
              autoFocus
              required
              style={inputStyle}
            />
          </div>

          {isAzure && (
            <div>
              <label style={labelStyle}>{s.org_url_label}</label>
              <input
                type="url"
                value={orgUrl}
                onChange={(e) => setOrgUrl(e.target.value)}
                placeholder={s.org_url_placeholder}
                required
                style={inputStyle}
              />
            </div>
          )}

          {(isGitlab || isGithub || isBitbucket) && (
            <div>
              <label style={labelStyle}>{s.base_url_label}</label>
              <input
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={
                  isGithub ? "https://github.mycompany.com" :
                  isBitbucket ? "https://bitbucket.mycompany.com" :
                  s.base_url_placeholder
                }
                style={inputStyle}
              />
              <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: "4px 0 0" }}>
                {s.base_url_optional}
              </p>
            </div>
          )}

          {error && (
            <div style={{
              padding: "8px 10px",
              borderRadius: "var(--radius)",
              background: "var(--err-bg)",
              color: "var(--err-fg)",
              fontSize: "12.5px",
            }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", paddingTop: "2px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius)",
                border: "1px solid var(--border)",
                background: "var(--surface-2)",
                color: "var(--fg-2)",
                fontSize: "12.5px",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {t.connections.actions.cancel}
            </button>
            <button
              type="submit"
              disabled={isDisabled}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 14px",
                borderRadius: "var(--radius)",
                border: "none",
                background: isDisabled ? "var(--surface-3)" : "var(--accent)",
                color: isDisabled ? "var(--muted)" : "var(--accent-fg)",
                fontSize: "12.5px",
                fontWeight: 500,
                cursor: isDisabled ? "not-allowed" : "pointer",
              }}
            >
              {loading && <Loader2 size={13} className="animate-spin" />}
              {loading ? s.connecting : s.connect_btn}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
