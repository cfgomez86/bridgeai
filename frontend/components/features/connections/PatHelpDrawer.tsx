"use client"

import { useState, useEffect } from "react"
import { X } from "lucide-react"
import { useLanguage } from "@/lib/i18n"

interface PatHelpDrawerProps {
  platform: string | null
  onClose: () => void
}

type Scope = { name: string; desc_es: string; desc_en: string }
type Step  = { es: string; en: string }

interface PlatformHelp {
  label: string
  tokenExample: string
  scopes: Scope[]
  steps: Step[]
  note_es?: string
  note_en?: string
}

const PLATFORMS: string[] = ["github", "gitlab", "azure_devops", "azure_boards", "bitbucket", "jira"]

const HELP: Record<string, PlatformHelp> = {
  github: {
    label: "GitHub",
    tokenExample: "ghp_xxxx  o  github_pat_xxxx",
    scopes: [
      {
        name: "repo",
        desc_es: "Acceso completo a repositorios públicos y privados",
        desc_en: "Full access to public and private repositories",
      },
      {
        name: "read:user",
        desc_es: "Leer información básica del perfil",
        desc_en: "Read basic profile information",
      },
    ],
    note_es: "Para GitHub Enterprise Server, introduce también la URL de tu instancia (ej. https://github.miempresa.com) al conectar. El token se genera de la misma forma en tu instancia propia.",
    note_en: "For GitHub Enterprise Server, also enter your instance URL (e.g. https://github.mycompany.com) when connecting. The token is generated the same way on your own instance.",
    steps: [
      { es: "Inicia sesión en github.com (o tu instancia Enterprise).", en: "Sign in to github.com (or your Enterprise instance)." },
      {
        es: "Haz clic en tu avatar (arriba a la derecha) → Settings.",
        en: "Click your avatar (top-right) → Settings.",
      },
      {
        es: 'Baja hasta "Developer settings" en el menú lateral y haz clic.',
        en: 'Scroll down to "Developer settings" in the sidebar and click it.',
      },
      {
        es: "Selecciona Personal access tokens → Tokens (classic).",
        en: "Select Personal access tokens → Tokens (classic).",
      },
      {
        es: 'Haz clic en "Generate new token" → "Generate new token (classic)".',
        en: 'Click "Generate new token" → "Generate new token (classic)".',
      },
      {
        es: 'Dale un nombre (ej. "BridgeAI") y elige la expiración.',
        en: 'Give it a name (e.g. "BridgeAI") and choose the expiration.',
      },
      {
        es: "Activa los scopes: repo ✓ y read:user ✓.",
        en: "Enable scopes: repo ✓ and read:user ✓.",
      },
      {
        es: 'Haz clic en "Generate token" y copia el valor generado.',
        en: 'Click "Generate token" and copy the generated value.',
      },
    ],
  },
  gitlab: {
    label: "GitLab",
    tokenExample: "glpat-xxxxxxxxxxxxxxxxxxxx",
    scopes: [
      {
        name: "read_api",
        desc_es: "Acceso de lectura a la API (lista repositorios, ramas, etc.)",
        desc_en: "Read access to the API (list repos, branches, etc.)",
      },
      {
        name: "read_repository",
        desc_es: "Leer contenido de repositorios",
        desc_en: "Read repository contents",
      },
      {
        name: "read_user",
        desc_es: "Leer información del perfil de usuario",
        desc_en: "Read user profile information",
      },
    ],
    steps: [
      { es: "Inicia sesión en gitlab.com (o tu instancia propia).", en: "Sign in to gitlab.com (or your self-hosted instance)." },
      {
        es: "Haz clic en tu avatar (arriba a la derecha) → Edit profile.",
        en: "Click your avatar (top-right) → Edit profile.",
      },
      {
        es: 'En el menú lateral selecciona "Access tokens".',
        en: 'In the sidebar select "Access tokens".',
      },
      {
        es: 'Haz clic en "Add new token".',
        en: 'Click "Add new token".',
      },
      {
        es: 'Escribe un nombre (ej. "BridgeAI") y elige una fecha de expiración.',
        en: 'Enter a name (e.g. "BridgeAI") and choose an expiry date.',
      },
      {
        es: "Activa los scopes: read_api ✓, read_repository ✓, read_user ✓.",
        en: "Enable scopes: read_api ✓, read_repository ✓, read_user ✓.",
      },
      {
        es: 'Haz clic en "Create personal access token" y copia el valor.',
        en: 'Click "Create personal access token" and copy the value.',
      },
    ],
    note_es: "Para GitLab auto-hospedado, introduce también la URL base de tu instancia (ej. https://gitlab.miempresa.com) al conectar.",
    note_en: "For self-hosted GitLab, also enter your instance base URL (e.g. https://gitlab.mycompany.com) when connecting.",
  },
  azure_devops: {
    label: "Azure Repos",
    tokenExample: "token de texto largo sin prefijo especial",
    scopes: [
      {
        name: "Code › Read",
        desc_es: "Leer repositorios de Azure Repos",
        desc_en: "Read Azure Repos repositories",
      },
      {
        name: "User Profile › Read",
        desc_es: "Leer el perfil del usuario",
        desc_en: "Read the user profile",
      },
    ],
    steps: [
      {
        es: "Ve a dev.azure.com e inicia sesión con tu cuenta de Microsoft.",
        en: "Go to dev.azure.com and sign in with your Microsoft account.",
      },
      {
        es: "Selecciona tu organización.",
        en: "Select your organization.",
      },
      {
        es: "Haz clic en tu avatar (arriba a la derecha) → Personal access tokens.",
        en: "Click your avatar (top-right) → Personal access tokens.",
      },
      {
        es: 'Haz clic en "New Token".',
        en: 'Click "New Token".',
      },
      {
        es: 'Dale un nombre (ej. "BridgeAI"), elige la organización y la expiración.',
        en: 'Give it a name (e.g. "BridgeAI"), choose the organization and expiration.',
      },
      {
        es: 'En "Scopes" selecciona "Custom defined".',
        en: 'Under "Scopes" choose "Custom defined".',
      },
      {
        es: "Activa: Code → Read ✓ y User Profile → Read ✓.",
        en: "Enable: Code → Read ✓ and User Profile → Read ✓.",
      },
      {
        es: 'Haz clic en "Create" y copia el token generado.',
        en: 'Click "Create" and copy the generated token.',
      },
    ],
    note_es: "La URL de tu organización tiene el formato: https://dev.azure.com/nombre-de-tu-org",
    note_en: "Your organization URL follows this format: https://dev.azure.com/your-org-name",
  },
  azure_boards: {
    label: "Azure Boards",
    tokenExample: "token de texto largo sin prefijo especial",
    scopes: [
      {
        name: "Work Items › Read",
        desc_es: "Leer tableros, sprints, issues y epics",
        desc_en: "Read boards, sprints, issues and epics",
      },
      {
        name: "Work Items › Write",
        desc_es: "Crear y actualizar work items",
        desc_en: "Create and update work items",
      },
      {
        name: "Project and Team › Read",
        desc_es: "Leer proyectos y equipos de la organización",
        desc_en: "Read projects and teams in the organization",
      },
    ],
    steps: [
      {
        es: "Ve a dev.azure.com e inicia sesión con tu cuenta de Microsoft.",
        en: "Go to dev.azure.com and sign in with your Microsoft account.",
      },
      { es: "Selecciona tu organización.", en: "Select your organization." },
      {
        es: "Haz clic en tu avatar (arriba a la derecha) → Personal access tokens.",
        en: "Click your avatar (top-right) → Personal access tokens.",
      },
      { es: 'Haz clic en "New Token".', en: 'Click "New Token".' },
      {
        es: 'Dale un nombre (ej. "BridgeAI Boards"), elige la organización y la expiración.',
        en: 'Give it a name (e.g. "BridgeAI Boards"), choose the organization and expiration.',
      },
      {
        es: 'En "Scopes" selecciona "Custom defined".',
        en: 'Under "Scopes" choose "Custom defined".',
      },
      {
        es: "Activa: Work Items → Read ✓, Work Items → Write ✓ y Project and Team → Read ✓.",
        en: "Enable: Work Items → Read ✓, Work Items → Write ✓ and Project and Team → Read ✓.",
      },
      {
        es: 'Haz clic en "Create" y copia el token generado.',
        en: 'Click "Create" and copy the generated token.',
      },
    ],
    note_es: "Si ya conectaste Azure Repos, puedes usar la misma conexión para Boards — no necesitas crear un token nuevo. Un token con los scopes de Boards también funciona para Repos y viceversa si incluyes ambos.",
    note_en: "If you already connected Azure Repos, you can reuse that connection for Boards — no new token needed. A token with Boards scopes also works for Repos if you include both scope groups.",
  },
  bitbucket: {
    label: "Bitbucket",
    tokenExample: "ATCTT3xFfGN... o ATBBxxxx...",
    scopes: [
      {
        name: "Repositories › Read",
        desc_es: "Listar y leer repositorios del workspace",
        desc_en: "List and read workspace repositories",
      },
      {
        name: "Account › Read",
        desc_es: "Leer información de la cuenta",
        desc_en: "Read account information",
      },
    ],
    steps: [
      {
        es: "Inicia sesión en bitbucket.org.",
        en: "Sign in to bitbucket.org.",
      },
      {
        es: "Haz clic en el icono de tu workspace (menú lateral izquierdo) → Settings.",
        en: "Click your workspace icon (left sidebar) → Settings.",
      },
      {
        es: 'En el menú lateral, bajo "Security", selecciona "Access tokens".',
        en: 'In the sidebar, under "Security", select "Access tokens".',
      },
      {
        es: 'Haz clic en "Create access token".',
        en: 'Click "Create access token".',
      },
      {
        es: 'Dale un nombre (ej. "BridgeAI").',
        en: 'Give it a name (e.g. "BridgeAI").',
      },
      {
        es: "Activa los permisos: Repositories → Read ✓ y Account → Read ✓.",
        en: "Enable permissions: Repositories → Read ✓ and Account → Read ✓.",
      },
      {
        es: 'Haz clic en "Create" y copia el token generado.',
        en: 'Click "Create" and copy the generated token.',
      },
    ],
    note_es: "Para Bitbucket Cloud usa HTTP Access Tokens del workspace (no App Passwords). Para Bitbucket Data Center, introduce la URL de tu instancia (ej. https://bitbucket.miempresa.com) al conectar.",
    note_en: "For Bitbucket Cloud use workspace HTTP Access Tokens (not App Passwords). For Bitbucket Data Center, enter your instance URL (e.g. https://bitbucket.mycompany.com) when connecting.",
  },
  jira: {
    label: "Jira",
    tokenExample: "ATATT3xFfGN0aBcDeFgHiJkLmNoPqRsTuVwXyZ...",
    scopes: [
      {
        name: "read:jira-work",
        desc_es: "Leer proyectos, issues, tableros y sprints",
        desc_en: "Read projects, issues, boards and sprints",
      },
      {
        name: "read:jira-user",
        desc_es: "Leer información del perfil de usuario",
        desc_en: "Read user profile information",
      },
      {
        name: "offline_access",
        desc_es: "Mantener la sesión activa sin re-autenticar",
        desc_en: "Keep the session active without re-authenticating",
      },
    ],
    steps: [
      {
        es: "Inicia sesión en tu cuenta de Atlassian en id.atlassian.com.",
        en: "Sign in to your Atlassian account at id.atlassian.com.",
      },
      {
        es: "Haz clic en tu avatar (arriba a la derecha) → Manage account.",
        en: "Click your avatar (top-right) → Manage account.",
      },
      {
        es: 'Selecciona la pestaña "Security" en el menú superior.',
        en: 'Select the "Security" tab in the top menu.',
      },
      {
        es: 'En la sección "API tokens", haz clic en "Create and manage API tokens".',
        en: 'Under "API tokens", click "Create and manage API tokens".',
      },
      {
        es: 'Haz clic en "Create API token".',
        en: 'Click "Create API token".',
      },
      {
        es: 'Dale un nombre descriptivo (ej. "BridgeAI") y haz clic en "Create".',
        en: 'Give it a descriptive name (e.g. "BridgeAI") and click "Create".',
      },
      {
        es: "Copia el token generado — solo se muestra una vez.",
        en: "Copy the generated token — it is only shown once.",
      },
    ],
    note_es: "El token de API se usa junto con tu email de Atlassian. Introduce el token en el campo Token y tu email en el campo Email al conectar. La URL del sitio tiene el formato https://mi-org.atlassian.net",
    note_en: "The API token is used together with your Atlassian email. Enter the token in the Token field and your email in the Email field when connecting. The site URL follows the format https://my-org.atlassian.net",
  },
}

const LABELS_ES = {
  title: "Cómo generar tu token",
  scopes_title: "Permisos necesarios",
  steps_title: "Pasos para generarlo",
  token_example: "Formato del token:",
  note_title: "Nota",
  connect_btn: "Conectar con este token",
}

const LABELS_EN = {
  title: "How to generate your token",
  scopes_title: "Required permissions",
  steps_title: "Steps to generate it",
  token_example: "Token format:",
  note_title: "Note",
  connect_btn: "Connect with this token",
}

export function PatHelpDrawer({ platform, onClose }: PatHelpDrawerProps) {
  const { locale } = useLanguage()
  const L = locale === "en" ? LABELS_EN : LABELS_ES

  const isOpen = platform !== null
  const [active, setActive] = useState(platform ?? PLATFORMS[0])

  useEffect(() => {
    if (platform) setActive(platform)
  }, [platform])

  const help = HELP[active] ?? null

  if (!isOpen) return null

  const note = help ? (locale === "en" ? help.note_en : help.note_es) : undefined

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 40,
          background: "rgba(0,0,0,0.35)",
        }}
      />

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 50,
          width: "100%",
          maxWidth: "480px",
          background: "var(--surface)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "-8px 0 40px rgba(0,0,0,0.18)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 18px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          <h2 style={{
            fontSize: "14px",
            fontWeight: 600,
            color: "var(--fg)",
            margin: 0,
            fontFamily: "var(--font-display)",
          }}>
            {L.title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: "28px", height: "28px", borderRadius: "var(--radius)",
              border: "none", background: "transparent", color: "var(--muted)",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Platform tabs */}
        <div style={{
          display: "flex",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
          overflowX: "auto",
        }}>
          {PLATFORMS.map((p) => {
            const isActive = p === active
            return (
              <button
                key={p}
                type="button"
                onClick={() => setActive(p)}
                style={{
                  padding: "9px 14px",
                  border: "none",
                  borderBottom: isActive ? "2px solid var(--accent)" : "2px solid transparent",
                  background: "transparent",
                  color: isActive ? "var(--accent-strong)" : "var(--fg-2)",
                  fontSize: "12.5px",
                  fontWeight: isActive ? 600 : 400,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                }}
              >
                {HELP[p]?.label ?? p}
              </button>
            )
          })}
        </div>

        {/* Content */}
        {help && (
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "20px 20px 28px",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
          }}>
            {/* Token format */}
            <div style={{
              padding: "10px 14px",
              borderRadius: "var(--radius)",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              fontSize: "12.5px",
              color: "var(--fg-2)",
            }}>
              <span style={{ fontWeight: 500 }}>{L.token_example} </span>
              <code style={{ fontFamily: "var(--font-mono)", color: "var(--fg)" }}>{help.tokenExample}</code>
            </div>

            {/* Scopes */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <h3 style={{
                fontSize: "11.5px",
                fontWeight: 600,
                color: "var(--fg-2)",
                margin: 0,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}>
                {L.scopes_title}
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {help.scopes.map((scope) => (
                  <div
                    key={scope.name}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "10px",
                      padding: "8px 12px",
                      borderRadius: "var(--radius)",
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <code style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11.5px",
                      fontWeight: 600,
                      color: "var(--accent-strong)",
                      background: "var(--accent-soft)",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}>
                      {scope.name}
                    </code>
                    <span style={{ fontSize: "12px", color: "var(--fg-2)", lineHeight: 1.5 }}>
                      {locale === "en" ? scope.desc_en : scope.desc_es}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Steps */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <h3 style={{
                fontSize: "11.5px",
                fontWeight: 600,
                color: "var(--fg-2)",
                margin: 0,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}>
                {L.steps_title}
              </h3>
              <ol style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "8px" }}>
                {help.steps.map((step, idx) => (
                  <li
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "10px",
                    }}
                  >
                    <span style={{
                      flexShrink: 0,
                      width: "22px",
                      height: "22px",
                      borderRadius: "50%",
                      background: "var(--accent-soft)",
                      color: "var(--accent-strong)",
                      fontSize: "11px",
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginTop: "1px",
                    }}>
                      {idx + 1}
                    </span>
                    <span style={{ fontSize: "13px", color: "var(--fg)", lineHeight: 1.55 }}>
                      {locale === "en" ? step.en : step.es}
                    </span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Note */}
            {note && (
              <div style={{
                padding: "10px 14px",
                borderRadius: "var(--radius)",
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                fontSize: "12px",
                color: "var(--fg-2)",
                lineHeight: 1.5,
              }}>
                <span style={{ fontWeight: 600 }}>{L.note_title}: </span>
                {note}
              </div>
            )}

          </div>
        )}
      </div>
    </>
  )
}
