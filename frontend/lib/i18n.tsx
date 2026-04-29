"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Locale = "es" | "en" | "ca"

interface Translations {
  nav: {
    home: string
    workflow: string
    indexing: string
    connections: string
    settings: string
    feedback: string
  }
  connections: {
    title: string
    description: string
    connected_accounts: string
    coming_soon: string
    sections: {
      repositories: string
      management_tools: string
    }
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
      one_active: string
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
    pat: {
      modal_title: string
      token_label: string
      token_placeholder: string
      org_url_label: string
      org_url_placeholder: string
      base_url_label: string
      base_url_placeholder: string
      base_url_optional: string
      connect_btn: string
      connecting: string
      use_pat: string
    }
    card: {
      active_badge: string
      select_repo: string
      select_site: string
      select_project: string
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
      azure_boards: string
      bitbucket: string
    }
    default_platform_desc: string
    toast_connected: string
    toast_error: string
    tabs: { oauth: string; pat: string }
    viewGuide: string
    oauthPanel: {
      info: string
      connect: string
      disconnect: string
      notConfigured: string
    }
    patPanel: {
      info: string
      tokenLabel: string
      instanceLabel: string
      instanceOptional: string
      scopesLabel: string
      connect: string
      validating: string
    }
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
      config_title: string
      ticket_provider_label: string
      ticket_provider_not_configured: string
      ticket_site_not_selected: string
      ticket_project_label: string
      ticket_project_input_label: string
      ticket_project_not_set: string
      repo_label: string
      index_label: string
      not_configured: string
      not_indexed: string
      files_indexed: string
      blocked_hint: string
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
      continue_btn: string
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
      project_key_hint: string
      project_key_loading: string
      issue_type_label: string
      create_subtasks_label: string
      creating: string
      create_btn: string
      new_story: string
      integration_status: string
      connected_provider: string
      connected_repo: string
      no_ticket_provider: string
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
    index_status: string
    indexed_files: string
    last_indexed: string
    not_indexed_yet: string
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
  dashboard: {
    title: string
    subtitle: string
    start_story: { title: string; description: string; btn: string }
    index_code: { title: string; description: string; btn: string }
    how_it_works: string
    steps: {
      understand: { title: string; description: string }
      impact: { title: string; description: string }
      generate: { title: string; description: string }
      ticket: { title: string; description: string }
    }
    greeting: string
    greetingNoName: string
    quickStartTitle: string
    quickStartLead: string
    startWorkflow: string
    stats: {
      requirements: string
      stories: string
      tickets: string
      approval: string
      approvalMeta: string
      quality: string
      qualityMeta: string
      qualityEmpty: string
      conversion: string
      conversionMeta: string
      conversionEmpty: string
      riskTitle: string
      riskLow: string
      riskMedium: string
      riskHigh: string
      riskMeta: string
      riskEmpty: string
      last30days: string
      allTime: string
      jiraAzure: string
      jiraOnly: string
      azureOnly: string
      noFeedback: string
    }
    activity: {
      title: string
      meta: string
      empty: string
    }
    empty: {
      title: string
      desc: string
      cta: string
    }
  }
  feedbackPage: {
    title: string
    subtitle: string
    empty: string
    load_more: string
    loading_more: string
    open_story: string
    comment_label: string
    error_load: string
    filter_all: string
    filter_positive: string
    filter_negative: string
  }
  stories: {
    edit_title: string
    edit_btn: string
    edit_saved: string
    locked_badge: string
    locked_error: string
    field_title: string
    field_description: string
    field_ac: string
    field_dod: string
    field_risk_notes: string
    field_story_points: string
    field_risk_level: string
    subtasks_frontend: string
    subtasks_backend: string
    subtasks_configuration: string
    subtask: string
    subtask_title_placeholder: string
    subtask_desc_placeholder: string
    add_item: string
    add_subtask: string
    save_changes: string
    story_ready: string
    ready_badge: string
    story_hint: string
    unsaved: string
    discard: string
    quality: {
      title: string
      loading: string
      structural_title: string
      judge_title: string
      schema_valid: string
      schema_invalid: string
      ac_count: string
      risk_notes_count: string
      subtask_count: string
      cited_paths: string
      no_citations: string
      evaluate_btn: string
      re_evaluate_btn: string
      per_dimension: string
      evaluating: string
      completeness: string
      specificity: string
      feasibility: string
      risk_coverage: string
      language_consistency: string
      overall: string
      score_good: string
      score_ok: string
      score_low: string
      dispersion_label: string
      dispersion_unstable: string
      evidence_label: string
      help: {
        schema_valid: string
        ac_count: string
        risk_notes_count: string
        subtask_count: string
        citation_grounding: string
        completeness: string
        specificity: string
        feasibility: string
        risk_coverage: string
        language_consistency: string
        overall: string
        dispersion: string
      }
    }
    feedback: {
      title: string
      thumbs_up: string
      thumbs_down: string
      comment_placeholder: string
      submit_btn: string
      update_btn: string
      submitting: string
      submitted_ok: string
      submit_error: string
    }
    system_quality: {
      precision_label: string
      evaluated_label: string
      dataset_size: string
      evaluated_at: string
    }
  }
}

// ---------------------------------------------------------------------------
// Spanish translations
// ---------------------------------------------------------------------------

const es: Translations = {
  nav: {
    home: "Dashboard",
    workflow: "Workflow",
    indexing: "Indexacion",
    connections: "Conexiones",
    settings: "Ajustes",
    feedback: "Feedback",
  },
  connections: {
    title: "Conexiones",
    description: "Integra las plataformas de codigo fuente para analizar impacto y generar historias.",
    connected_accounts: "Cuentas conectadas",
    coming_soon: "Proximamente",
    sections: {
      repositories: "Repositorios",
      management_tools: "Herramientas de gestión",
    },
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
      one_active: "Desconecta la conexión activa primero",
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
    pat: {
      modal_title: "Conectar con Token de Acceso Personal",
      token_label: "Token de Acceso Personal",
      token_placeholder: "Pega tu token aqui...",
      org_url_label: "URL de la organizacion",
      org_url_placeholder: "https://dev.azure.com/mi-org",
      base_url_label: "URL base (instancia propia)",
      base_url_placeholder: "https://gitlab.miempresa.com",
      base_url_optional: "Opcional — solo para GitLab auto-hospedado",
      connect_btn: "Conectar",
      connecting: "Conectando...",
      use_pat: "Usar PAT",
    },
    card: {
      active_badge: "activo",
      select_repo: "Seleccionar Repositorio",
      select_site: "Seleccionar Organización",
      select_project: "Seleccionar proyecto",
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
      gitlab: "Conecta repositorios de GitLab para analizar codigo y estimar impacto.",
      azure_devops: "Conecta repositorios de Azure Repos para analizar codigo y estimar impacto.",
      azure_boards: "Gestiona work items y tableros de Azure Boards. Usa la misma conexión de Azure DevOps.",
      bitbucket: "Conecta repositorios de Bitbucket para analizar codigo y estimar impacto.",
    },
    default_platform_desc: "Conecta gestor de tickets para registrar historias.",
    toast_connected: "Conectado con exito a",
    toast_error: "Error al conectar con",
    tabs: { oauth: "OAuth", pat: "PAT" },
    viewGuide: "Ver guía",
    oauthPanel: {
      info: "Te llevamos a {platform} para autorizar BridgeAI. Sin tokens manuales, los permisos los gestionas desde tu cuenta.",
      connect: "Conectar",
      disconnect: "Desconectar",
      notConfigured: "OAuth no está configurado en este servidor. Pide al admin que registre la app de {platform} o usa un PAT.",
    },
    patPanel: {
      info: "Pega tu Personal Access Token. Se almacena en el servidor y se cifra si el administrador ha configurado la clave de cifrado.",
      tokenLabel: "Personal Access Token",
      instanceLabel: "URL de la instancia",
      instanceOptional: "(opcional)",
      scopesLabel: "Necesitas estos scopes:",
      connect: "Conectar",
      validating: "se valida en tiempo real",
    },
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
      config_title: "Configuracion requerida",
      ticket_provider_label: "Proveedor de tickets",
      ticket_provider_not_configured: "Sin configurar — conecta y selecciona la organizacion en Conexiones",
      ticket_site_not_selected: "Sin organizacion seleccionada — selecciona el sitio en Conexiones",
      ticket_project_label: "Proyecto de tickets",
      ticket_project_input_label: "Clave del proyecto",
      ticket_project_not_set: "Sin configurar — selecciona el proyecto en tu herramienta de gestion",
      repo_label: "Repositorio de codigo",
      index_label: "Indice del repositorio",
      not_configured: "Sin configurar — ve al modulo de Conexiones",
      not_indexed: "Sin datos — ejecuta el indice en el modulo de Indexacion",
      files_indexed: "archivos indexados",
      blocked_hint: "Completa la configuracion anterior para continuar.",
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
      continue_btn: "Continuar al ticket →",
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
      ticket_description: "El ticket se creará con el proveedor de tickets conectado.",
      ticket_success: "Ticket creado con exito",
      open_in: "Abrir en",
      provider_label: "Proveedor:",
      provider_select: "Proveedor",
      project_key_label: "Clave del proyecto",
      project_key_hint: "Selecciona un proyecto...",
      project_key_loading: "Cargando proyectos...",
      issue_type_label: "Tipo de issue",
      create_subtasks_label: "Crear subtareas automaticamente",
      creating: "Creando ticket...",
      create_btn: "Crear ticket",
      new_story: "Nueva historia",
      integration_status: "Estado de integraciones",
      connected_provider: "Proveedor conectado",
      connected_repo: "Repositorio activo",
      no_ticket_provider: "No hay proveedor de tickets conectado. Ve a Conexiones para configurarlo.",
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
    index_status: "Estado del indice",
    indexed_files: "archivos indexados",
    last_indexed: "actualizado hace",
    not_indexed_yet: "Sin datos en el indice",
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
  stories: {
    edit_title: "Editar historia",
    edit_btn: "Editar",
    edit_saved: "Historia actualizada",
    locked_badge: "Enviado",
    locked_error: "Esta historia ya fue enviada a Jira/Azure y no puede editarse",
    field_title: "Titulo",
    field_description: "Descripcion",
    field_ac: "Criterios de aceptacion",
    field_dod: "Definicion de terminado",
    field_risk_notes: "Notas de riesgo",
    field_story_points: "Story points",
    field_risk_level: "Nivel de riesgo",
    subtasks_frontend: "Subtareas Frontend",
    subtasks_backend: "Subtareas Backend",
    subtasks_configuration: "Subtareas Configuracion",
    subtask: "Subtarea",
    subtask_title_placeholder: "Titulo de la subtarea",
    subtask_desc_placeholder: "Descripcion detallada de la subtarea",
    add_item: "Agregar elemento",
    add_subtask: "Agregar subtarea",
    save_changes: "Guardar cambios",
    story_ready: "Historia generada",
    ready_badge: "LISTA",
    story_hint: "Editá cualquier campo en línea. Los cambios se guardan en lote al pulsar Guardar.",
    unsaved: "Cambios sin guardar",
    discard: "Descartar",
    quality: {
      title: "Calidad de la historia",
      loading: "Cargando metricas...",
      structural_title: "Metricas estructurales",
      judge_title: "Evaluacion IA",
      schema_valid: "Esquema valido",
      schema_invalid: "Esquema invalido",
      ac_count: "Criterios de aceptacion",
      risk_notes_count: "Notas de riesgo",
      subtask_count: "Subtareas tecnicas",
      cited_paths: "Archivos en repo",
      no_citations: "Sin citas externas",
      evaluate_btn: "Evaluar con IA",
      re_evaluate_btn: "Re-evaluar",
      per_dimension: "Por dimensión",
      evaluating: "Evaluando...",
      completeness: "Completitud",
      specificity: "Especificidad",
      feasibility: "Viabilidad",
      risk_coverage: "Cobertura de riesgos",
      language_consistency: "Consistencia de idioma",
      overall: "Puntuacion general",
      score_good: "Bueno",
      score_ok: "Aceptable",
      score_low: "Bajo",
      dispersion_label: "muestras",
      dispersion_unstable: "Resultado inestable",
      evidence_label: "Evidencia",
      help: {
        schema_valid: "La historia tiene titulo, descripcion, al menos 1 criterio de aceptacion y 1 subtarea tecnica",
        ac_count: "Numero de condiciones que deben cumplirse para dar la historia por completada",
        risk_notes_count: "Riesgos tecnicos o de negocio identificados y documentados en la historia",
        subtask_count: "Total de tareas tecnicas de implementacion entre frontend, backend y configuracion",
        citation_grounding: "De las rutas de archivos mencionadas en subtareas, cuantas existen realmente en el repositorio. Si no hay citas se considera 100%. Detecta rutas inventadas por el modelo",
        completeness: "La historia cubre todos los casos de uso del requerimiento original",
        specificity: "Los criterios y subtareas son suficientemente detallados para implementarse sin ambiguedad",
        feasibility: "La historia es implementable con el stack y el equipo actuales",
        risk_coverage: "Se identificaron y documentaron todos los riesgos tecnicos relevantes",
        language_consistency: "Toda la historia esta escrita consistentemente en el mismo idioma",
        overall: "Puntuacion integrada que considera todos los criterios de evaluacion",
        dispersion: "Desviacion entre las muestras del juez. Cerca de 0 indica un juicio estable; valores altos (>=1.0) avisan de que el modelo dudo y conviene re-evaluar",
      },
    },
    feedback: {
      title: "Tu opinion",
      thumbs_up: "Util",
      thumbs_down: "Mejorable",
      comment_placeholder: "Comentario opcional...",
      submit_btn: "Enviar",
      update_btn: "Actualizar",
      submitting: "Enviando...",
      submitted_ok: "Feedback enviado",
      submit_error: "Error al enviar feedback",
    },
    system_quality: {
      precision_label: "Precision historica del analisis: {pct}%",
      evaluated_label: "Evaluado",
      dataset_size: "Dataset",
      evaluated_at: "Evaluado el",
    },
  },
  dashboard: {
    title: "Dashboard",
    subtitle: "Automatiza tu flujo de requerimiento a ticket con IA.",
    start_story: {
      title: "Iniciar nueva historia",
      description: "Convierte un requerimiento en una historia de usuario completa con criterios de aceptación, tareas técnicas y story points.",
      btn: "Iniciar Workflow",
    },
    index_code: {
      title: "Indexar código",
      description: "Escanea e indexa tu código fuente para que BridgeAI pueda realizar un análisis de impacto preciso.",
      btn: "Abrir índice",
    },
    how_it_works: "Cómo funciona",
    steps: {
      understand: {
        title: "Entender",
        description: "La IA extrae la intención, tipo de funcionalidad, complejidad y términos clave del requerimiento.",
      },
      impact: {
        title: "Impacto",
        description: "Cruza el índice de tu codebase para identificar archivos, módulos y nivel de riesgo afectados.",
      },
      generate: {
        title: "Generar",
        description: "Produce una historia de usuario completa con criterios de aceptación, tareas técnicas y definición de terminado.",
      },
      ticket: {
        title: "Ticket",
        description: "Crea el ticket directamente en Jira o Azure DevOps con un solo clic, sin copiar ni pegar.",
      },
    },
    greeting: "Buenas tardes,",
    greetingNoName: "Buenas tardes",
    quickStartTitle: "Nueva historia desde un requerimiento",
    quickStartLead: "Pega el requisito, BridgeAI calcula el impacto y genera la historia con criterios de aceptación.",
    startWorkflow: "Iniciar workflow →",
    stats: {
      requirements: "Requerimientos",
      stories: "Historias generadas",
      tickets: "Tickets creados",
      approval: "Aprobación",
      approvalMeta: "{n} valoraciones",
      quality: "Calidad media",
      qualityMeta: "{n} evaluadas",
      qualityEmpty: "Sin evaluar",
      conversion: "Conversión",
      conversionMeta: "{n} historias",
      conversionEmpty: "sin historias",
      riskTitle: "Distribución de riesgo",
      riskLow: "LOW",
      riskMedium: "MEDIUM",
      riskHigh: "HIGH",
      riskMeta: "total de historias",
      riskEmpty: "sin historias aún",
      last30days: "últimos 30 días",
      allTime: "total",
      jiraAzure: "Jira · Azure DevOps",
      jiraOnly: "Jira",
      azureOnly: "Azure DevOps",
      noFeedback: "sin feedback aún",
    },
    activity: {
      title: "Actividad reciente",
      meta: "últimos eventos",
      empty: "Sin actividad aún. Empieza un workflow para verla aquí.",
    },
    empty: {
      title: "Aún no hay actividad",
      desc: "Pega un requerimiento y crea tu primera historia con criterios de aceptación, subtareas y ticket.",
      cta: "Iniciar primer workflow →",
    },
  },
  feedbackPage: {
    title: "Feedback",
    subtitle: "Comentarios de los usuarios para revisar y mejorar el sistema.",
    empty: "Sin comentarios por ahora.",
    load_more: "Cargar más",
    loading_more: "Cargando...",
    open_story: "Abrir historia →",
    comment_label: "Comentario",
    error_load: "No se pudo cargar el feedback.",
    filter_all: "Todos",
    filter_positive: "👍 Positivos",
    filter_negative: "👎 Negativos",
  },
}

// ---------------------------------------------------------------------------
// English translations
// ---------------------------------------------------------------------------

const en: Translations = {
  nav: {
    home: "Dashboard",
    workflow: "Workflow",
    indexing: "Indexing",
    connections: "Connections",
    settings: "Settings",
    feedback: "Feedback",
  },
  connections: {
    title: "Connections",
    description: "Connect your source code platforms to analyze impact and generate stories.",
    connected_accounts: "Connected accounts",
    coming_soon: "Coming soon",
    sections: {
      repositories: "Repositories",
      management_tools: "Management tools",
    },
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
      one_active: "Disconnect the active connection first",
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
    pat: {
      modal_title: "Connect with Personal Access Token",
      token_label: "Personal Access Token",
      token_placeholder: "Paste your token here...",
      org_url_label: "Organization URL",
      org_url_placeholder: "https://dev.azure.com/my-org",
      base_url_label: "Base URL (self-hosted)",
      base_url_placeholder: "https://gitlab.mycompany.com",
      base_url_optional: "Optional — only for self-hosted GitLab",
      connect_btn: "Connect",
      connecting: "Connecting...",
      use_pat: "Use PAT",
    },
    card: {
      active_badge: "active",
      select_repo: "Select repo",
      select_site: "Select organization",
      select_project: "Select project",
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
      gitlab: "Connect GitLab repositories to analyze code and estimate impact.",
      azure_devops: "Connect Azure Repos repositories to analyze code and estimate impact.",
      azure_boards: "Manage work items and Azure Boards. Shares the existing Azure DevOps connection.",
      bitbucket: "Connect Bitbucket repositories to analyze code and estimate impact.",
    },
    default_platform_desc: "Connect this platform to get started.",
    toast_connected: "Successfully connected to",
    toast_error: "Error connecting to",
    tabs: { oauth: "OAuth", pat: "PAT" },
    viewGuide: "View guide",
    oauthPanel: {
      info: "We take you to {platform} to authorize BridgeAI. No manual tokens — you manage permissions from your account.",
      connect: "Connect",
      disconnect: "Disconnect",
      notConfigured: "OAuth is not configured on this server. Ask your admin to register the {platform} app or use a PAT.",
    },
    patPanel: {
      info: "Paste your Personal Access Token. It is stored on the server and encrypted if the administrator has configured the encryption key.",
      tokenLabel: "Personal Access Token",
      instanceLabel: "Instance URL",
      instanceOptional: "(optional)",
      scopesLabel: "You need these scopes:",
      connect: "Connect",
      validating: "validated in real time",
    },
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
      config_title: "Required setup",
      ticket_provider_label: "Ticket provider",
      ticket_provider_not_configured: "Not set up — connect and select the organization in Connections",
      ticket_site_not_selected: "No site selected — choose a site in Connections",
      ticket_project_label: "Ticket project",
      ticket_project_input_label: "Project key",
      ticket_project_not_set: "Not set — select the project in your management tool",
      repo_label: "Code repository",
      index_label: "Repository index",
      not_configured: "Not set up — go to the Connections module",
      not_indexed: "No data — run the index in the Indexing module",
      files_indexed: "files indexed",
      blocked_hint: "Complete the setup above to continue.",
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
      continue_btn: "Continue to ticket →",
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
      ticket_description: "The ticket will be created with the connected ticket provider.",
      ticket_success: "Ticket created successfully",
      open_in: "Open in",
      provider_label: "Provider:",
      provider_select: "Provider",
      project_key_label: "Project key",
      project_key_hint: "Select a project...",
      project_key_loading: "Loading projects...",
      issue_type_label: "Issue type",
      create_subtasks_label: "Create subtasks automatically",
      creating: "Creating ticket...",
      create_btn: "Create ticket",
      new_story: "New story",
      integration_status: "Integration status",
      connected_provider: "Connected provider",
      connected_repo: "Active repository",
      no_ticket_provider: "No ticket provider connected. Go to Connections to set it up.",
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
    index_status: "Index status",
    indexed_files: "files indexed",
    last_indexed: "updated",
    not_indexed_yet: "No data in index",
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
  dashboard: {
    title: "Dashboard",
    subtitle: "Automate your requirement-to-ticket workflow with AI.",
    start_story: {
      title: "Start New Story",
      description: "Transform a requirement into a fully-formed user story with acceptance criteria, technical tasks, and story points.",
      btn: "Launch Workflow",
    },
    index_code: {
      title: "Index Codebase",
      description: "Scan and index your source code so BridgeAI can perform accurate impact analysis when requirements are processed.",
      btn: "Open Code Index",
    },
    how_it_works: "How it works",
    steps: {
      understand: {
        title: "Understand",
        description: "AI parses your requirement text to extract intent, feature type, complexity, and key domain terms.",
      },
      impact: {
        title: "Impact",
        description: "Cross-references your codebase index to identify affected files, modules, and overall risk level.",
      },
      generate: {
        title: "Generate",
        description: "Produces a complete user story with acceptance criteria, technical tasks, definition of done, and story points.",
      },
      ticket: {
        title: "Ticket",
        description: "Pushes the generated story directly to Jira or Azure DevOps with a single click — no copy-paste needed.",
      },
    },
    greeting: "Good afternoon,",
    greetingNoName: "Good afternoon",
    quickStartTitle: "New story from a requirement",
    quickStartLead: "Paste the requirement, BridgeAI computes the impact and generates the story with acceptance criteria.",
    startWorkflow: "Start workflow →",
    stats: {
      requirements: "Requirements",
      stories: "Stories generated",
      tickets: "Tickets created",
      approval: "Approval rate",
      approvalMeta: "{n} ratings",
      quality: "Average quality",
      qualityMeta: "{n} evaluated",
      qualityEmpty: "Not evaluated yet",
      conversion: "Conversion",
      conversionMeta: "{n} stories",
      conversionEmpty: "no stories yet",
      riskTitle: "Risk distribution",
      riskLow: "LOW",
      riskMedium: "MEDIUM",
      riskHigh: "HIGH",
      riskMeta: "total stories",
      riskEmpty: "no stories yet",
      last30days: "last 30 days",
      allTime: "all time",
      jiraAzure: "Jira · Azure DevOps",
      jiraOnly: "Jira",
      azureOnly: "Azure DevOps",
      noFeedback: "no feedback yet",
    },
    activity: {
      title: "Recent activity",
      meta: "latest events",
      empty: "No activity yet. Start a workflow to see it here.",
    },
    empty: {
      title: "Nothing here yet",
      desc: "Paste a requirement and create your first story with acceptance criteria, subtasks and ticket.",
      cta: "Start first workflow →",
    },
  },
  feedbackPage: {
    title: "Feedback",
    subtitle: "User comments to review and improve the system.",
    empty: "No comments yet.",
    load_more: "Load more",
    loading_more: "Loading...",
    open_story: "Open story →",
    comment_label: "Comment",
    error_load: "Could not load feedback.",
    filter_all: "All",
    filter_positive: "👍 Positive",
    filter_negative: "👎 Negative",
  },
  stories: {
    edit_title: "Edit story",
    edit_btn: "Edit",
    edit_saved: "Story updated",
    locked_badge: "Sent",
    locked_error: "This story was already sent to Jira/Azure and cannot be edited",
    field_title: "Title",
    field_description: "Description",
    field_ac: "Acceptance criteria",
    field_dod: "Definition of done",
    field_risk_notes: "Risk notes",
    field_story_points: "Story points",
    field_risk_level: "Risk level",
    subtasks_frontend: "Frontend subtasks",
    subtasks_backend: "Backend subtasks",
    subtasks_configuration: "Configuration subtasks",
    subtask: "Subtask",
    subtask_title_placeholder: "Subtask title",
    subtask_desc_placeholder: "Detailed subtask description",
    add_item: "Add item",
    add_subtask: "Add subtask",
    save_changes: "Save changes",
    story_ready: "Story generated",
    ready_badge: "READY",
    story_hint: "Edit any field inline. Changes are saved in bulk when you press Save.",
    unsaved: "Unsaved changes",
    discard: "Discard",
    quality: {
      title: "Story quality",
      loading: "Loading metrics...",
      structural_title: "Structural metrics",
      judge_title: "AI Evaluation",
      schema_valid: "Schema valid",
      schema_invalid: "Schema invalid",
      ac_count: "Acceptance criteria",
      risk_notes_count: "Risk notes",
      subtask_count: "Technical subtasks",
      cited_paths: "Files in repo",
      no_citations: "No external citations",
      evaluate_btn: "Evaluate with AI",
      re_evaluate_btn: "Re-evaluate",
      per_dimension: "By dimension",
      evaluating: "Evaluating...",
      completeness: "Completeness",
      specificity: "Specificity",
      feasibility: "Feasibility",
      risk_coverage: "Risk coverage",
      language_consistency: "Language consistency",
      overall: "Overall score",
      score_good: "Good",
      score_ok: "Acceptable",
      score_low: "Low",
      dispersion_label: "samples",
      dispersion_unstable: "Unstable result",
      evidence_label: "Evidence",
      help: {
        schema_valid: "The story has a title, description, at least 1 acceptance criterion and 1 subtask",
        ac_count: "Number of conditions that must be met for the story to be considered complete",
        risk_notes_count: "Technical or business risks identified and documented in the story",
        subtask_count: "Total implementation tasks across frontend, backend, and configuration",
        citation_grounding: "Of the file paths mentioned in subtasks, how many actually exist in the repository. 100% if no citations. Detects hallucinated paths",
        completeness: "Does the story cover all use cases from the original requirement?",
        specificity: "Are the criteria and subtasks detailed enough to implement without ambiguity?",
        feasibility: "Is the story implementable with the current stack and team?",
        risk_coverage: "Were all relevant technical risks identified and documented?",
        language_consistency: "Is the entire story written consistently in the same language?",
        overall: "Integrated score considering all evaluation criteria",
        dispersion: "Spread across judge samples. Near 0 means a stable judgment; high values (>=1.0) flag uncertainty and suggest re-evaluating",
      },
    },
    feedback: {
      title: "Your feedback",
      thumbs_up: "Useful",
      thumbs_down: "Needs improvement",
      comment_placeholder: "Optional comment...",
      submit_btn: "Submit",
      update_btn: "Update",
      submitting: "Submitting...",
      submitted_ok: "Feedback submitted",
      submit_error: "Error submitting feedback",
    },
    system_quality: {
      precision_label: "Historical analysis precision: {pct}%",
      evaluated_label: "Evaluated",
      dataset_size: "Dataset",
      evaluated_at: "Evaluated on",
    },
  },
}

// ---------------------------------------------------------------------------
// Catalan translations
// ---------------------------------------------------------------------------

const ca: Translations = {
  nav: {
    home: "Tauler",
    workflow: "Flux de treball",
    indexing: "Indexació",
    connections: "Connexions",
    settings: "Configuració",
    feedback: "Feedback",
  },
  connections: {
    title: "Connexions",
    description: "Integra les plataformes de codi font per analitzar l'impacte i generar històries.",
    connected_accounts: "Comptes connectats",
    coming_soon: "Pròximament",
    sections: {
      repositories: "Repositoris",
      management_tools: "Eines de gestió",
    },
    status: {
      connected: "Connectat",
      configured: "Configurat",
      disconnected: "Sense configurar",
    },
    actions: {
      connect: "Connectar",
      connecting: "Connectant...",
      disconnect: "Desconnectar",
      disconnecting: "Desconnectant...",
      configure: "Configurar",
      edit: "Editar",
      save: "Desar",
      saving: "Desant...",
      cancel: "Cancel·lar",
      delete: "Eliminar configuració",
      connect_first: "Configura primer",
      one_active: "Desconnecta la connexió activa primer",
    },
    oauth: {
      bridge_title: "OAuth de BridgeAI",
      bridge_desc: "Utilitza l'app OAuth gestionada per BridgeAI.",
      active_tag: "actiu",
      fallback_tag: "secundari",
      own_app_title: "La teva pròpia app OAuth",
      not_configured: "No configurat — introdueix Client ID i Secret.",
    },
    errors: {
      oauth: "Error en iniciar el flux OAuth.",
      save: "Error en desar la configuració.",
      delete: "Error en eliminar la configuració.",
      disconnect: "Error en desconnectar el compte.",
    },
    pat: {
      modal_title: "Connectar amb Token d'Accés Personal",
      token_label: "Token d'Accés Personal",
      token_placeholder: "Enganxa el teu token aquí...",
      org_url_label: "URL de l'organització",
      org_url_placeholder: "https://dev.azure.com/la-meva-org",
      base_url_label: "URL base (instància pròpia)",
      base_url_placeholder: "https://gitlab.lamevaempresa.com",
      base_url_optional: "Opcional — només per a GitLab auto-allotjat",
      connect_btn: "Connectar",
      connecting: "Connectant...",
      use_pat: "Usar PAT",
    },
    card: {
      active_badge: "actiu",
      select_repo: "Seleccionar Repositori",
      select_site: "Seleccionar Organització",
      select_project: "Seleccionar projecte",
      disconnect_title: "Desconnectar compte",
    },
    repo_selector: {
      title: "Seleccionar repositori",
      filter_placeholder: "Cercar repositori...",
      loading: "Carregant repositoris...",
      not_found: "No s'han trobat repositoris.",
      error_load: "Error en carregar repositoris.",
      error_activate: "Error en activar el repositori.",
      close: "Cancel·lar",
    },
    platform_desc: {
      github: "Connecta repositoris de GitHub per analitzar codi i estimar impacte.",
      gitlab: "Connecta repositoris de GitLab per analitzar codi i estimar impacte.",
      azure_devops: "Connecta repositoris d'Azure Repos per analitzar codi i estimar impacte.",
      azure_boards: "Gestiona elements de treball i taulers d'Azure Boards. Utilitza la mateixa connexió d'Azure DevOps.",
      bitbucket: "Connecta repositoris de Bitbucket per analitzar codi i estimar impacte.",
    },
    default_platform_desc: "Connecta el gestor de tiquets per registrar històries.",
    toast_connected: "Connectat amb èxit a",
    toast_error: "Error en connectar amb",
    tabs: { oauth: "OAuth", pat: "PAT" },
    viewGuide: "Veure guia",
    oauthPanel: {
      info: "Et portem a {platform} per autoritzar BridgeAI. Sense tokens manuals, els permisos els gestiones des del teu compte.",
      connect: "Connectar",
      disconnect: "Desconnectar",
      notConfigured: "OAuth no està configurat en aquest servidor. Demana a l'admin que registri l'app de {platform} o usa un PAT.",
    },
    patPanel: {
      info: "Enganxa el teu Personal Access Token. S'emmagatzema al servidor i es xifra si l'administrador ha configurat la clau de xifratge.",
      tokenLabel: "Personal Access Token",
      instanceLabel: "URL de la instància",
      instanceOptional: "(opcional)",
      scopesLabel: "Necessites aquests scopes:",
      connect: "Connectar",
      validating: "es valida en temps real",
    },
  },
  workflow: {
    step_prefix: "Pas",
    step_of: "de",
    new_requirement: "Nou requeriment",
    subtitle: "Converteix un requeriment en un tiquet llest per al teu gestor de projectes.",
    stepper: {
      current: "actual",
      steps: {
        requirement: { label: "Requeriment", hint: "Analitza la intenció i complexitat" },
        impact: { label: "Impacte", hint: "Identifica arxius i mòduls afectats" },
        story: { label: "Història", hint: "Genera la història d'usuari completa" },
        ticket: { label: "Tiquet", hint: "Crea el tiquet al teu gestor de projectes" },
      },
    },
    step1: {
      title: "Entendre el requeriment",
      description: "Enganxa el text del requeriment i BridgeAI l'analitzarà per identificar la intenció, complexitat i tipus de funcionalitat.",
      requirement_label: "Text del requeriment",
      placeholder: "Ex: Implementar sistema d'autenticació amb OAuth2 i suport per a MFA...",
      min_chars: "El requeriment ha de tenir almenys 10 caràcters.",
      story_language: "Idioma de la història",
      analyzing: "Analitzant...",
      analyze_btn: "Analitzar requeriment",
      config_title: "Configuració requerida",
      ticket_provider_label: "Proveïdor de tiquets",
      ticket_provider_not_configured: "Sense configurar — connecta i selecciona l'organització a Connexions",
      ticket_site_not_selected: "Sense organització seleccionada — selecciona el lloc a Connexions",
      ticket_project_label: "Projecte de tiquets",
      ticket_project_input_label: "Clau del projecte",
      ticket_project_not_set: "Sense configurar — selecciona el projecte a la teva eina de gestió",
      repo_label: "Repositori de codi",
      index_label: "Índex del repositori",
      not_configured: "Sense configurar — ves al mòdul de Connexions",
      not_indexed: "Sense dades — executa l'índex al mòdul d'Indexació",
      files_indexed: "arxius indexats",
      blocked_hint: "Completa la configuració anterior per continuar.",
    },
    step2: {
      title: "Anàlisi d'impacte",
      description: "BridgeAI escanejarà el codi indexat per determinar quins arxius i mòduls es veuran afectats per aquest canvi.",
      files: "Arxius afectats",
      risk: "Nivell de risc",
      affected_modules: "Mòduls afectats",
      complexity: "Complexitat:",
      step1_summary: "Requeriment analitzat",
      analyzing: "Analitzant impacte...",
      analyze_btn: "Analitzar impacte",
      re_analyze: "Re-analitzar",
    },
    step3: {
      title: "Generar història d'usuari",
      description: "BridgeAI crearà una història d'usuari completa amb criteris d'acceptació, subtasques i definició d'acabat.",
      step1_summary: "Requeriment",
      step2_summary: "Impacte analitzat",
      files: "Arxius:",
      complexity: "Complexitat:",
      description_label: "Descripció",
      acceptance_criteria: "Criteris d'acceptació",
      subtasks_frontend: "Subtasques Frontend",
      subtasks_backend: "Subtasques Backend",
      subtasks_configuration: "Subtasques Configuració",
      definition_of_done: "Definició d'acabat",
      risk_notes: "Notes de risc",
      point: "punt",
      points: "punts",
      generating: "Generant història...",
      generate_btn: "Generar història",
      regenerating: "Regenerant...",
      regenerate_btn: "Regenerar",
      continue_btn: "Continuar al tiquet →",
    },
    step4: {
      title: "Crear tiquet",
      description: "Crea el tiquet al teu gestor de projectes amb tota la informació generada.",
      step1_summary: "Requeriment",
      step2_summary: "Impacte analitzat",
      step3_summary: "Història generada",
      files: "Arxius:",
      complexity: "Complexitat:",
      description_label: "Descripció",
      acceptance_criteria: "Criteris d'acceptació",
      subtasks_frontend: "Subtasques Frontend",
      subtasks_backend: "Subtasques Backend",
      subtasks_configuration: "Subtasques Configuració",
      definition_of_done: "Definició d'acabat",
      risk_notes: "Notes de risc",
      point: "punt",
      points: "punts",
      loading_story: "Carregant història...",
      ticket_title: "Crear tiquet",
      ticket_description: "El tiquet es crearà amb el proveïdor de tiquets connectat.",
      ticket_success: "Tiquet creat amb èxit",
      open_in: "Obrir a",
      provider_label: "Proveïdor:",
      provider_select: "Proveïdor",
      project_key_label: "Clau del projecte",
      project_key_hint: "Selecciona un projecte...",
      project_key_loading: "Carregant projectes...",
      issue_type_label: "Tipus d'issue",
      create_subtasks_label: "Crear subtasques automàticament",
      creating: "Creant tiquet...",
      create_btn: "Crear tiquet",
      new_story: "Nova història",
      integration_status: "Estat de les integracions",
      connected_provider: "Proveïdor connectat",
      connected_repo: "Repositori actiu",
      no_ticket_provider: "No hi ha proveïdor de tiquets connectat. Ves a Connexions per configurar-lo.",
      subtasks_created: "Subtasques creades",
      subtasks_failed: "Subtasques amb error",
    },
  },
  indexing: {
    title: "Indexació de codi",
    description: "Indexa el repositori actiu perquè BridgeAI pugui analitzar l'impacte dels teus requeriments.",
    active_repo: "Repositori actiu",
    loading: "Carregant...",
    no_repo: "Sense repositori actiu",
    change_repo: "Canviar repositori",
    index_status: "Estat de l'índex",
    indexed_files: "arxius indexats",
    last_indexed: "actualitzat fa",
    not_indexed_yet: "Sense dades a l'índex",
    indexing_progress: "Indexant...",
    index_btn: "Indexar codi",
    force_reindex: "Forçar re-indexació",
    error_unexpected: "Error inesperat durant la indexació.",
    completed_in: "Indexació completada en",
    source: "Font:",
    no_repo_title: "Sense repositori actiu",
    no_repo_desc_pre: "Ves a",
    no_repo_desc_post: "i activa un repositori per poder indexar-lo.",
    no_data_title: "Llest per indexar",
    no_data_desc: "Fes clic a 'Indexar codi' per escanejar el repositori actiu.",
  },
  settings: {
    sections: {
      integrations: "Integracions",
      language: "Idioma",
      theme: "Aparença",
    },
    integrations: {
      title: "Gestionar integracions",
      save: "Desar",
      badge_active: "actiu",
      badge_token_expiry: "token per expirar",
      jira: {
        subtitle: "Crea tiquets a Jira Cloud automàticament.",
        workspace_url: "URL del workspace",
        project_key: "Clau del projecte",
        issue_type: "Tipus d'issue",
        default_labels: "Etiquetes per defecte",
        draft_label: "Crear com a esborrany",
        draft_desc: "Els tiquets es creen en estat esborrany fins que els revisis.",
      },
      azure: {
        subtitle: "Sincronitza amb Azure DevOps Boards.",
        org_url: "URL de l'organització",
        project: "Projecte",
        area_path: "Area path",
        iteration_path: "Iteration path",
      },
    },
    language: {
      title: "Idioma de la interfície",
      description: "Canvia l'idioma en què es mostra l'aplicació.",
    },
    theme: {
      title: "Aparença",
      description: "Selecciona entre el tema clar i fosc.",
      options: {
        light: "Clar",
        dark: "Fosc",
      },
    },
  },
  dashboard: {
    title: "Tauler",
    subtitle: "Automatitza el teu flux de requeriment a tiquet amb IA.",
    start_story: {
      title: "Iniciar nova història",
      description: "Converteix un requeriment en una història d'usuari completa amb criteris d'acceptació, tasques tècniques i story points.",
      btn: "Iniciar Flux de treball",
    },
    index_code: {
      title: "Indexar codi",
      description: "Escaneja i indexa el teu codi font perquè BridgeAI pugui fer una anàlisi d'impacte precisa.",
      btn: "Obrir índex",
    },
    how_it_works: "Com funciona",
    steps: {
      understand: {
        title: "Entendre",
        description: "La IA extreu la intenció, tipus de funcionalitat, complexitat i termes clau del requeriment.",
      },
      impact: {
        title: "Impacte",
        description: "Creua l'índex del teu codebase per identificar arxius, mòduls i nivell de risc afectats.",
      },
      generate: {
        title: "Generar",
        description: "Produeix una història d'usuari completa amb criteris d'acceptació, tasques tècniques i definició d'acabat.",
      },
      ticket: {
        title: "Tiquet",
        description: "Crea el tiquet directament a Jira o Azure DevOps amb un sol clic, sense copiar ni enganxar.",
      },
    },
    greeting: "Bona tarda,",
    greetingNoName: "Bona tarda",
    quickStartTitle: "Nova història a partir d'un requeriment",
    quickStartLead: "Enganxa el requisit, BridgeAI calcula l'impacte i genera la història amb criteris d'acceptació.",
    startWorkflow: "Iniciar flux de treball →",
    stats: {
      requirements: "Requeriments",
      stories: "Històries generades",
      tickets: "Tiquets creats",
      approval: "Aprovació",
      approvalMeta: "{n} valoracions",
      quality: "Qualitat mitjana",
      qualityMeta: "{n} avaluades",
      qualityEmpty: "Sense avaluar",
      conversion: "Conversió",
      conversionMeta: "{n} històries",
      conversionEmpty: "sense històries",
      riskTitle: "Distribució de risc",
      riskLow: "BAIX",
      riskMedium: "MITJÀ",
      riskHigh: "ALT",
      riskMeta: "total d'històries",
      riskEmpty: "sense històries encara",
      last30days: "últims 30 dies",
      allTime: "total",
      jiraAzure: "Jira · Azure DevOps",
      jiraOnly: "Jira",
      azureOnly: "Azure DevOps",
      noFeedback: "sense feedback encara",
    },
    activity: {
      title: "Activitat recent",
      meta: "últims esdeveniments",
      empty: "Sense activitat encara. Comença un flux de treball per veure-la aquí.",
    },
    empty: {
      title: "Encara no hi ha activitat",
      desc: "Enganxa un requeriment i crea la teva primera història amb criteris d'acceptació, subtasques i tiquet.",
      cta: "Iniciar primer flux de treball →",
    },
  },
  feedbackPage: {
    title: "Feedback",
    subtitle: "Comentaris dels usuaris per revisar i millorar el sistema.",
    empty: "Sense comentaris de moment.",
    load_more: "Carregar més",
    loading_more: "Carregant...",
    open_story: "Obrir història →",
    comment_label: "Comentari",
    error_load: "No s'ha pogut carregar el feedback.",
    filter_all: "Tots",
    filter_positive: "👍 Positius",
    filter_negative: "👎 Negatius",
  },
  stories: {
    edit_title: "Editar història",
    edit_btn: "Editar",
    edit_saved: "Història actualitzada",
    locked_badge: "Enviat",
    locked_error: "Aquesta història ja va ser enviada a Jira/Azure i no es pot editar",
    field_title: "Títol",
    field_description: "Descripció",
    field_ac: "Criteris d'acceptació",
    field_dod: "Definició d'acabat",
    field_risk_notes: "Notes de risc",
    field_story_points: "Story points",
    field_risk_level: "Nivell de risc",
    subtasks_frontend: "Subtasques Frontend",
    subtasks_backend: "Subtasques Backend",
    subtasks_configuration: "Subtasques Configuració",
    subtask: "Subtasca",
    subtask_title_placeholder: "Títol de la subtasca",
    subtask_desc_placeholder: "Descripció detallada de la subtasca",
    add_item: "Afegir element",
    add_subtask: "Afegir subtasca",
    save_changes: "Desar canvis",
    story_ready: "Història generada",
    ready_badge: "LLESTA",
    story_hint: "Edita qualsevol camp en línia. Els canvis es desen en lot en prémer Desar.",
    unsaved: "Canvis sense desar",
    discard: "Descartar",
    quality: {
      title: "Qualitat de la història",
      loading: "Carregant mètriques...",
      structural_title: "Mètriques estructurals",
      judge_title: "Avaluació IA",
      schema_valid: "Esquema vàlid",
      schema_invalid: "Esquema invàlid",
      ac_count: "Criteris d'acceptació",
      risk_notes_count: "Notes de risc",
      subtask_count: "Subtasques tècniques",
      cited_paths: "Arxius al repositori",
      no_citations: "Sense cites externes",
      evaluate_btn: "Avaluar amb IA",
      re_evaluate_btn: "Re-avaluar",
      per_dimension: "Per dimensió",
      evaluating: "Avaluant...",
      completeness: "Completitud",
      specificity: "Especificitat",
      feasibility: "Viabilitat",
      risk_coverage: "Cobertura de riscos",
      language_consistency: "Consistència d'idioma",
      overall: "Puntuació general",
      score_good: "Bo",
      score_ok: "Acceptable",
      score_low: "Baix",
      dispersion_label: "mostres",
      dispersion_unstable: "Resultat inestable",
      evidence_label: "Evidència",
      help: {
        schema_valid: "La història té títol, descripció, almenys 1 criteri d'acceptació i 1 subtasca tècnica",
        ac_count: "Nombre de condicions que s'han de complir per donar la història per completada",
        risk_notes_count: "Riscos tècnics o de negoci identificats i documentats a la història",
        subtask_count: "Total de tasques tècniques d'implementació entre frontend, backend i configuració",
        citation_grounding: "De les rutes d'arxius esmentades en subtasques, quantes existeixen realment al repositori. Si no hi ha cites es considera 100%. Detecta rutes inventades pel model",
        completeness: "La història cobreix tots els casos d'ús del requeriment original",
        specificity: "Els criteris i subtasques són prou detallats per implementar-se sense ambigüitat",
        feasibility: "La història és implementable amb l'stack i l'equip actuals",
        risk_coverage: "Es van identificar i documentar tots els riscos tècnics rellevants",
        language_consistency: "Tota la història està escrita de manera consistent en el mateix idioma",
        overall: "Puntuació integrada que considera tots els criteris d'avaluació",
        dispersion: "Desviació entre les mostres del jutge. Prop de 0 indica un judici estable; valors alts (>=1.0) avisen que el model ha dubtat i convé re-avaluar",
      },
    },
    feedback: {
      title: "La teva opinió",
      thumbs_up: "Útil",
      thumbs_down: "Millorable",
      comment_placeholder: "Comentari opcional...",
      submit_btn: "Enviar",
      update_btn: "Actualitzar",
      submitting: "Enviant...",
      submitted_ok: "Feedback enviat",
      submit_error: "Error en enviar feedback",
    },
    system_quality: {
      precision_label: "Precisió històrica de l'anàlisi: {pct}%",
      evaluated_label: "Avaluat",
      dataset_size: "Dataset",
      evaluated_at: "Avaluat el",
    },
  },
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const TRANSLATIONS: Record<Locale, Translations> = { es, en, ca }
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
    if (saved && (saved === "es" || saved === "en" || saved === "ca")) {
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
