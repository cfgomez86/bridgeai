"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Locale = "es" | "en"

interface Translations {
  nav: {
    home: string
    workflow: string
    indexing: string
    connections: string
    settings: string
  }
  connections: {
    title: string
    description: string
    connected_accounts: string
    coming_soon: string
    status: {
      connected: string
      configured: string
      disconnected: string
    }
    actions: {
      connect: string
      connecting: string
      disconnect: string
      disconnecting: string
      configure: string
      edit: string
      save: string
      saving: string
      cancel: string
      delete: string
      connect_first: string
    }
    oauth: {
      bridge_title: string
      bridge_desc: string
      active_tag: string
      fallback_tag: string
      own_app_title: string
      not_configured: string
    }
    errors: {
      oauth: string
      save: string
      delete: string
      disconnect: string
    }
    card: {
      active_badge: string
      select_repo: string
      disconnect_title: string
    }
    repo_selector: {
      title: string
      filter_placeholder: string
      loading: string
      not_found: string
      error_load: string
      error_activate: string
      close: string
    }
    platform_desc: {
      github: string
      gitlab: string
      azure_devops: string
      bitbucket: string
    }
    default_platform_desc: string
    toast_connected: string
    toast_error: string
  }
  workflow: {
    step_prefix: string
    step_of: string
    new_requirement: string
    subtitle: string
    stepper: {
      current: string
      steps: {
        requirement: { label: string; hint: string }
        impact: { label: string; hint: string }
        story: { label: string; hint: string }
        ticket: { label: string; hint: string }
      }
    }
    step1: {
      title: string
      description: string
      requirement_label: string
      placeholder: string
      min_chars: string
      story_language: string
      analyzing: string
      analyze_btn: string
    }
    step2: {
      title: string
      description: string
      files: string
      risk: string
      affected_modules: string
      complexity: string
      step1_summary: string
      analyzing: string
      analyze_btn: string
      re_analyze: string
    }
    step3: {
      title: string
      description: string
      step1_summary: string
      step2_summary: string
      files: string
      complexity: string
      description_label: string
      acceptance_criteria: string
      subtasks_frontend: string
      subtasks_backend: string
      subtasks_configuration: string
      definition_of_done: string
      risk_notes: string
      point: string
      points: string
      generating: string
      generate_btn: string
      regenerating: string
      regenerate_btn: string
    }
    step4: {
      title: string
      description: string
      step1_summary: string
      step2_summary: string
      step3_summary: string
      files: string
      complexity: string
      description_label: string
      acceptance_criteria: string
      subtasks_frontend: string
      subtasks_backend: string
      subtasks_configuration: string
      definition_of_done: string
      risk_notes: string
      point: string
      points: string
      loading_story: string
      ticket_title: string
      ticket_description: string
      ticket_success: string
      open_in: string
      provider_label: string
      provider_select: string
      project_key_label: string
      issue_type_label: string
      create_subtasks_label: string
      creating: string
      create_btn: string
      new_story: string
      integration_status: string
      subtasks_created: string
      subtasks_failed: string
    }
  }
  indexing: {
    title: string
    description: string
    active_repo: string
    loading: string
    no_repo: string
    change_repo: string
    indexing_progress: string
    index_btn: string
    force_reindex: string
    error_unexpected: string
    completed_in: string
    source: string
    no_repo_title: string
    no_repo_desc_pre: string
    no_repo_desc_post: string
    no_data_title: string
    no_data_desc: string
  }
  settings: {
    sections: {
      integrations: string
      generation: string
      language: string
      theme: string
    }
    integrations: {
      title: string
      save: string
      badge_active: string
      badge_token_expiry: string
      jira: {
        subtitle: string
        workspace_url: string
        project_key: string
        issue_type: string
        default_labels: string
        draft_label: string
        draft_desc: string
      }
      azure: {
        subtitle: string
        org_url: string
        project: string
        area_path: string
        iteration_path: string
      }
    }
    generation: {
      title: string
      rules: {
        max_stories: { label: string; description: string }
        gherkin: { label: string; description: string }
        story_points: { label: string; description: string }
        link_files: { label: string; description: string }
        auto_assign: { label: string; description: string }
      }
    }
    language: {
      title: string
      description: string
    }
    theme: {
      title: string
      description: string
      options: {
        light: string
        dark: string
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Spanish translations
// ---------------------------------------------------------------------------

const es: Translations = {
  nav: {
    home: "Inicio",
    workflow: "Workflow",
    indexing: "Indexacion",
    connections: "Conexiones",
    settings: "Ajustes",
  },
  connections: {
    title: "Conexiones",
    description: "Conecta tus plataformas de codigo fuente para analizar impacto y generar historias.",
    connected_accounts: "Cuentas conectadas",
    coming_soon: "Proximamente",
    status: {
      connected: "Conectado",
      configured: "Configurado",
      disconnected: "Sin configurar",
    },
    actions: {
      connect: "Conectar",
      connecting: "Conectando...",
      disconnect: "Desconectar",
      disconnecting: "Desconectando...",
      configure: "Configurar",
      edit: "Editar",
      save: "Guardar",
      saving: "Guardando...",
      cancel: "Cancelar",
      delete: "Eliminar configuracion",
      connect_first: "Configura primero",
    },
    oauth: {
      bridge_title: "OAuth de BridgeAI",
      bridge_desc: "Usa la app OAuth gestionada por BridgeAI.",
      active_tag: "activo",
      fallback_tag: "secundario",
      own_app_title: "Tu propia app OAuth",
      not_configured: "No configurado — introduce Client ID y Secret.",
    },
    errors: {
      oauth: "Error al iniciar el flujo OAuth.",
      save: "Error al guardar la configuracion.",
      delete: "Error al eliminar la configuracion.",
      disconnect: "Error al desconectar la cuenta.",
    },
    card: {
      active_badge: "activo",
      select_repo: "Seleccionar repo",
      disconnect_title: "Desconectar cuenta",
    },
    repo_selector: {
      title: "Seleccionar repositorio",
      filter_placeholder: "Buscar repositorio...",
      loading: "Cargando repositorios...",
      not_found: "No se encontraron repositorios.",
      error_load: "Error al cargar repositorios.",
      error_activate: "Error al activar el repositorio.",
      close: "Cancelar",
    },
    platform_desc: {
      github: "Conecta repositorios de GitHub para analizar codigo y estimar impacto.",
      gitlab: "Conecta proyectos de GitLab y analiza cambios con IA.",
      azure_devops: "Integra repositorios de Azure DevOps y crea tickets directamente.",
      bitbucket: "Soporte para repositorios Bitbucket en desarrollo.",
    },
    default_platform_desc: "Conecta esta plataforma para empezar.",
    toast_connected: "Conectado con exito a",
    toast_error: "Error al conectar con",
  },
  workflow: {
    step_prefix: "Paso",
    step_of: "de",
    new_requirement: "Nuevo requerimiento",
    subtitle: "Convierte un requerimiento en un ticket listo para tu gestor de proyectos.",
    stepper: {
      current: "actual",
      steps: {
        requirement: { label: "Requerimiento", hint: "Analiza la intencion y complejidad" },
        impact: { label: "Impacto", hint: "Identifica archivos y modulos afectados" },
        story: { label: "Historia", hint: "Genera la historia de usuario completa" },
        ticket: { label: "Ticket", hint: "Crea el ticket en tu gestor de proyectos" },
      },
    },
    step1: {
      title: "Entender el requerimiento",
      description: "Pega el texto del requerimiento y BridgeAI lo analizara para identificar intencion, complejidad y tipo de funcionalidad.",
      requirement_label: "Texto del requerimiento",
      placeholder: "Ej: Implementar sistema de autenticacion con OAuth2 y soporte para MFA...",
      min_chars: "El requerimiento debe tener al menos 10 caracteres.",
      story_language: "Idioma de la historia",
      analyzing: "Analizando...",
      analyze_btn: "Analizar requerimiento",
    },
    step2: {
      title: "Analisis de impacto",
      description: "BridgeAI escaneara el codigo indexado para determinar que archivos y modulos se veran afectados por este cambio.",
      files: "Archivos afectados",
      risk: "Nivel de riesgo",
      affected_modules: "Modulos afectados",
      complexity: "Complejidad:",
      step1_summary: "Requerimiento analizado",
      analyzing: "Analizando impacto...",
      analyze_btn: "Analizar impacto",
      re_analyze: "Re-analizar",
    },
    step3: {
      title: "Generar historia de usuario",
      description: "BridgeAI creara una historia de usuario completa con criterios de aceptacion, subtareas y definicion de terminado.",
      step1_summary: "Requerimiento",
      step2_summary: "Impacto analizado",
      files: "Archivos:",
      complexity: "Complejidad:",
      description_label: "Descripcion",
      acceptance_criteria: "Criterios de aceptacion",
      subtasks_frontend: "Subtareas Frontend",
      subtasks_backend: "Subtareas Backend",
      subtasks_configuration: "Subtareas Configuracion",
      definition_of_done: "Definicion de terminado",
      risk_notes: "Notas de riesgo",
      point: "punto",
      points: "puntos",
      generating: "Generando historia...",
      generate_btn: "Generar historia",
      regenerating: "Regenerando...",
      regenerate_btn: "Regenerar",
    },
    step4: {
      title: "Crear ticket",
      description: "Crea el ticket en tu gestor de proyectos con toda la informacion generada.",
      step1_summary: "Requerimiento",
      step2_summary: "Impacto analizado",
      step3_summary: "Historia generada",
      files: "Archivos:",
      complexity: "Complejidad:",
      description_label: "Descripcion",
      acceptance_criteria: "Criterios de aceptacion",
      subtasks_frontend: "Subtareas Frontend",
      subtasks_backend: "Subtareas Backend",
      subtasks_configuration: "Subtareas Configuracion",
      definition_of_done: "Definicion de terminado",
      risk_notes: "Notas de riesgo",
      point: "punto",
      points: "puntos",
      loading_story: "Cargando historia...",
      ticket_title: "Crear ticket",
      ticket_description: "Selecciona el proveedor y el proyecto donde crear el ticket.",
      ticket_success: "Ticket creado con exito",
      open_in: "Abrir en",
      provider_label: "Proveedor:",
      provider_select: "Proveedor",
      project_key_label: "Clave del proyecto",
      issue_type_label: "Tipo de issue",
      create_subtasks_label: "Crear subtareas automaticamente",
      creating: "Creando ticket...",
      create_btn: "Crear ticket",
      new_story: "Nueva historia",
      integration_status: "Estado de integraciones",
      subtasks_created: "Subtareas creadas",
      subtasks_failed: "Subtareas con error",
    },
  },
  indexing: {
    title: "Indexacion de codigo",
    description: "Indexa el repositorio activo para que BridgeAI pueda analizar el impacto de tus requerimientos.",
    active_repo: "Repositorio activo",
    loading: "Cargando...",
    no_repo: "Sin repositorio activo",
    change_repo: "Cambiar repositorio",
    indexing_progress: "Indexando...",
    index_btn: "Indexar codigo",
    force_reindex: "Forzar re-indexacion",
    error_unexpected: "Error inesperado durante la indexacion.",
    completed_in: "Indexacion completada en",
    source: "Fuente:",
    no_repo_title: "Sin repositorio activo",
    no_repo_desc_pre: "Ve a",
    no_repo_desc_post: "y activa un repositorio para poder indexarlo.",
    no_data_title: "Listo para indexar",
    no_data_desc: "Haz clic en 'Indexar codigo' para escanear el repositorio activo.",
  },
  settings: {
    sections: {
      integrations: "Integraciones",
      generation: "Generacion",
      language: "Idioma",
      theme: "Apariencia",
    },
    integrations: {
      title: "Gestionar integraciones",
      save: "Guardar",
      badge_active: "activo",
      badge_token_expiry: "token por expirar",
      jira: {
        subtitle: "Crea tickets en Jira Cloud automaticamente.",
        workspace_url: "URL del workspace",
        project_key: "Clave del proyecto",
        issue_type: "Tipo de issue",
        default_labels: "Etiquetas por defecto",
        draft_label: "Crear como borrador",
        draft_desc: "Los tickets se crean en estado borrador hasta que los revises.",
      },
      azure: {
        subtitle: "Sincroniza con Azure DevOps Boards.",
        org_url: "URL de la organizacion",
        project: "Proyecto",
        area_path: "Area path",
        iteration_path: "Iteration path",
      },
    },
    generation: {
      title: "Reglas de generacion",
      rules: {
        max_stories: {
          label: "Max. historias por requerimiento",
          description: "Numero maximo de historias generadas por analisis.",
        },
        gherkin: {
          label: "Formato Gherkin en criterios",
          description: "Los criterios de aceptacion se escriben en Given/When/Then.",
        },
        story_points: {
          label: "Incluir story points",
          description: "Estima automaticamente los puntos de esfuerzo.",
        },
        link_files: {
          label: "Enlazar archivos afectados",
          description: "Adjunta la lista de archivos impactados al ticket.",
        },
        auto_assign: {
          label: "Auto-asignar al creador",
          description: "Asigna el ticket al usuario que lo genera.",
        },
      },
    },
    language: {
      title: "Idioma de la interfaz",
      description: "Cambia el idioma en que se muestra la aplicacion.",
    },
    theme: {
      title: "Apariencia",
      description: "Selecciona entre el tema claro y oscuro.",
      options: {
        light: "Claro",
        dark: "Oscuro",
      },
    },
  },
}

// ---------------------------------------------------------------------------
// English translations
// ---------------------------------------------------------------------------

const en: Translations = {
  nav: {
    home: "Home",
    workflow: "Workflow",
    indexing: "Indexing",
    connections: "Connections",
    settings: "Settings",
  },
  connections: {
    title: "Connections",
    description: "Connect your source code platforms to analyze impact and generate stories.",
    connected_accounts: "Connected accounts",
    coming_soon: "Coming soon",
    status: {
      connected: "Connected",
      configured: "Configured",
      disconnected: "Not configured",
    },
    actions: {
      connect: "Connect",
      connecting: "Connecting...",
      disconnect: "Disconnect",
      disconnecting: "Disconnecting...",
      configure: "Configure",
      edit: "Edit",
      save: "Save",
      saving: "Saving...",
      cancel: "Cancel",
      delete: "Delete config",
      connect_first: "Configure first",
    },
    oauth: {
      bridge_title: "BridgeAI OAuth",
      bridge_desc: "Use the OAuth app managed by BridgeAI.",
      active_tag: "active",
      fallback_tag: "fallback",
      own_app_title: "Your own OAuth app",
      not_configured: "Not configured — enter Client ID and Secret.",
    },
    errors: {
      oauth: "Error starting OAuth flow.",
      save: "Error saving configuration.",
      delete: "Error deleting configuration.",
      disconnect: "Error disconnecting account.",
    },
    card: {
      active_badge: "active",
      select_repo: "Select repo",
      disconnect_title: "Disconnect account",
    },
    repo_selector: {
      title: "Select repository",
      filter_placeholder: "Search repository...",
      loading: "Loading repositories...",
      not_found: "No repositories found.",
      error_load: "Error loading repositories.",
      error_activate: "Error activating repository.",
      close: "Cancel",
    },
    platform_desc: {
      github: "Connect GitHub repositories to analyze code and estimate impact.",
      gitlab: "Connect GitLab projects and analyze changes with AI.",
      azure_devops: "Integrate Azure DevOps repositories and create tickets directly.",
      bitbucket: "Bitbucket repository support coming soon.",
    },
    default_platform_desc: "Connect this platform to get started.",
    toast_connected: "Successfully connected to",
    toast_error: "Error connecting to",
  },
  workflow: {
    step_prefix: "Step",
    step_of: "of",
    new_requirement: "New requirement",
    subtitle: "Convert a requirement into a ticket ready for your project manager.",
    stepper: {
      current: "current",
      steps: {
        requirement: { label: "Requirement", hint: "Analyze intent and complexity" },
        impact: { label: "Impact", hint: "Identify affected files and modules" },
        story: { label: "Story", hint: "Generate the complete user story" },
        ticket: { label: "Ticket", hint: "Create the ticket in your project manager" },
      },
    },
    step1: {
      title: "Understand the requirement",
      description: "Paste the requirement text and BridgeAI will analyze it to identify intent, complexity and feature type.",
      requirement_label: "Requirement text",
      placeholder: "E.g.: Implement authentication system with OAuth2 and MFA support...",
      min_chars: "The requirement must be at least 10 characters long.",
      story_language: "Story language",
      analyzing: "Analyzing...",
      analyze_btn: "Analyze requirement",
    },
    step2: {
      title: "Impact analysis",
      description: "BridgeAI will scan the indexed code to determine which files and modules will be affected by this change.",
      files: "Affected files",
      risk: "Risk level",
      affected_modules: "Affected modules",
      complexity: "Complexity:",
      step1_summary: "Analyzed requirement",
      analyzing: "Analyzing impact...",
      analyze_btn: "Analyze impact",
      re_analyze: "Re-analyze",
    },
    step3: {
      title: "Generate user story",
      description: "BridgeAI will create a complete user story with acceptance criteria, subtasks and definition of done.",
      step1_summary: "Requirement",
      step2_summary: "Analyzed impact",
      files: "Files:",
      complexity: "Complexity:",
      description_label: "Description",
      acceptance_criteria: "Acceptance criteria",
      subtasks_frontend: "Frontend subtasks",
      subtasks_backend: "Backend subtasks",
      subtasks_configuration: "Configuration subtasks",
      definition_of_done: "Definition of done",
      risk_notes: "Risk notes",
      point: "point",
      points: "points",
      generating: "Generating story...",
      generate_btn: "Generate story",
      regenerating: "Regenerating...",
      regenerate_btn: "Regenerate",
    },
    step4: {
      title: "Create ticket",
      description: "Create the ticket in your project manager with all the generated information.",
      step1_summary: "Requirement",
      step2_summary: "Analyzed impact",
      step3_summary: "Generated story",
      files: "Files:",
      complexity: "Complexity:",
      description_label: "Description",
      acceptance_criteria: "Acceptance criteria",
      subtasks_frontend: "Frontend subtasks",
      subtasks_backend: "Backend subtasks",
      subtasks_configuration: "Configuration subtasks",
      definition_of_done: "Definition of done",
      risk_notes: "Risk notes",
      point: "point",
      points: "points",
      loading_story: "Loading story...",
      ticket_title: "Create ticket",
      ticket_description: "Select the provider and project where to create the ticket.",
      ticket_success: "Ticket created successfully",
      open_in: "Open in",
      provider_label: "Provider:",
      provider_select: "Provider",
      project_key_label: "Project key",
      issue_type_label: "Issue type",
      create_subtasks_label: "Create subtasks automatically",
      creating: "Creating ticket...",
      create_btn: "Create ticket",
      new_story: "New story",
      integration_status: "Integration status",
      subtasks_created: "Subtasks created",
      subtasks_failed: "Failed subtasks",
    },
  },
  indexing: {
    title: "Code indexing",
    description: "Index the active repository so BridgeAI can analyze the impact of your requirements.",
    active_repo: "Active repository",
    loading: "Loading...",
    no_repo: "No active repository",
    change_repo: "Change repository",
    indexing_progress: "Indexing...",
    index_btn: "Index code",
    force_reindex: "Force re-indexing",
    error_unexpected: "Unexpected error during indexing.",
    completed_in: "Indexing completed in",
    source: "Source:",
    no_repo_title: "No active repository",
    no_repo_desc_pre: "Go to",
    no_repo_desc_post: "and activate a repository to index it.",
    no_data_title: "Ready to index",
    no_data_desc: "Click 'Index code' to scan the active repository.",
  },
  settings: {
    sections: {
      integrations: "Integrations",
      generation: "Generation",
      language: "Language",
      theme: "Appearance",
    },
    integrations: {
      title: "Manage integrations",
      save: "Save",
      badge_active: "active",
      badge_token_expiry: "token expiring",
      jira: {
        subtitle: "Automatically create tickets in Jira Cloud.",
        workspace_url: "Workspace URL",
        project_key: "Project key",
        issue_type: "Issue type",
        default_labels: "Default labels",
        draft_label: "Create as draft",
        draft_desc: "Tickets are created in draft state until you review them.",
      },
      azure: {
        subtitle: "Sync with Azure DevOps Boards.",
        org_url: "Organization URL",
        project: "Project",
        area_path: "Area path",
        iteration_path: "Iteration path",
      },
    },
    generation: {
      title: "Generation rules",
      rules: {
        max_stories: {
          label: "Max. stories per requirement",
          description: "Maximum number of stories generated per analysis.",
        },
        gherkin: {
          label: "Gherkin format in criteria",
          description: "Acceptance criteria written in Given/When/Then format.",
        },
        story_points: {
          label: "Include story points",
          description: "Automatically estimate effort points.",
        },
        link_files: {
          label: "Link affected files",
          description: "Attach the list of impacted files to the ticket.",
        },
        auto_assign: {
          label: "Auto-assign to creator",
          description: "Assign the ticket to the user who generates it.",
        },
      },
    },
    language: {
      title: "Interface language",
      description: "Change the language the app is displayed in.",
    },
    theme: {
      title: "Appearance",
      description: "Switch between light and dark theme.",
      options: {
        light: "Light",
        dark: "Dark",
      },
    },
  },
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const TRANSLATIONS: Record<Locale, Translations> = { es, en }
const STORAGE_KEY = "bridgeai-locale"

interface LanguageContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: Translations
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("es")

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Locale | null
    if (saved && (saved === "es" || saved === "en")) {
      setLocaleState(saved)
    }
  }, [])

  function setLocale(next: Locale) {
    setLocaleState(next)
    localStorage.setItem(STORAGE_KEY, next)
  }

  return (
    <LanguageContext.Provider value={{ locale, setLocale, t: TRANSLATIONS[locale] }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider")
  return ctx
}
