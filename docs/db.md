# Modelo de base de datos — BridgeAI

Motor: **PostgreSQL** (único soportado). ORM: **SQLAlchemy 2.0** con sintaxis `Mapped[...]`. Migraciones: **Alembic**. La `Base` declarativa vive en `app/database/session.py` y todos los modelos se importan en `app/main.py` para que `Base.metadata` los registre automáticamente.

> Para la arquitectura general ver [`arquitectura.md`](./arquitectura.md). Para los flujos de IA ver [`specs/ai.md`](./specs/ai.md).

---

## 1. Principios del esquema

1. **Multi-tenant duro**: prácticamente todas las tablas tienen `tenant_id` como FK a `tenants.id` y un índice sobre esa columna. El acceso pasa siempre por un repository que filtra por `tenant_id` desde el `ContextVar` poblado por Auth0.
2. **Aislamiento por conexión**: archivos, requerimientos, análisis e historias añaden `source_connection_id` para evitar mezclar repos de un mismo tenant. Los índices compuestos son `(tenant_id, source_connection_id, ...)`.
3. **IDs**: `String(36)` para UUIDs textuales en tablas principales; `Integer` autoincrement solo en tablas de relación de alta cardinalidad (`code_files`, `impacted_files`). Las tablas de feedback/quality usan `UUID(as_uuid=True)` nativo de PostgreSQL.
4. **Encriptación de campo**: tokens OAuth se almacenan con tipo `EncryptedText` (Fernet) — `app/database/encrypted_types.py`.
5. **Auditoría que sobrevive al borrado**: `connection_audit_logs.connection_id` es texto plano (sin FK) para preservar trazabilidad incluso si la conexión se borra. Las conexiones usan *soft delete* (`deleted_at`).

---

## 2. Diagrama Entidad-Relación

```mermaid
erDiagram
    tenants ||--o{ users : "tiene"
    tenants ||--o{ source_connections : "posee"
    tenants ||--o{ code_files : "agrupa"
    tenants ||--o{ requirements : "agrupa"
    tenants ||--o{ impact_analysis : "agrupa"
    tenants ||--o{ user_stories : "agrupa"
    tenants ||--o{ ticket_integrations : "agrupa"
    tenants ||--o{ integration_audit_logs : "agrupa"
    tenants ||--o{ connection_audit_logs : "agrupa"
    tenants ||--o{ oauth_states : "agrupa"

    source_connections ||--o{ code_files : "indexa"
    source_connections ||--o{ requirements : "scope"
    source_connections ||--o{ impact_analysis : "scope"
    source_connections ||--o{ user_stories : "scope"

    impact_analysis ||--o{ impacted_files : "incluye"

    user_stories ||--o{ story_feedback : "recibe"
    user_stories ||--|| story_quality_score : "evalúa"

    tenants {
        string id PK "uuid"
        string auth0_user_id UK
        string name
        string plan "free|..."
        datetime created_at
    }

    users {
        string id PK
        string auth0_user_id UK
        string tenant_id FK
        string email
        string name
        string role "member|..."
        datetime created_at
    }

    source_connections {
        string id PK
        string tenant_id FK
        string platform "github|gitlab|azure_repos|bitbucket|jira|azure_boards"
        string display_name
        text access_token "Fernet"
        text refresh_token "Fernet, nullable"
        datetime token_expires_at
        string auth_method "oauth|pat"
        string owner
        string repo_name
        string repo_full_name
        string boards_project
        string default_branch
        string base_url
        bool is_active
        string oauth_state
        datetime created_at
        datetime deleted_at "soft-delete"
    }

    oauth_states {
        string id PK
        string tenant_id FK
        string platform
        string state_token UK
        string redirect_uri
        datetime expires_at
        bool consumed
    }

    code_files {
        int id PK
        string tenant_id FK
        string source_connection_id FK
        text file_path
        string file_name
        string extension
        string language
        bigint size
        datetime last_modified
        string hash "sha256"
        int lines_of_code
        datetime indexed_at
        text content "capped"
    }

    requirements {
        string id PK
        string tenant_id FK
        string source_connection_id FK
        text requirement_text
        string requirement_text_hash
        string project_id
        string intent
        string action
        string entity
        string feature_type
        string priority
        string business_domain
        string technical_scope
        string estimated_complexity
        text keywords "JSON list"
        float processing_time_seconds
        datetime created_at
    }

    impact_analysis {
        string id PK
        string tenant_id FK
        string source_connection_id FK
        text requirement
        string risk_level "LOW|MEDIUM|HIGH"
        int files_impacted
        int modules_impacted
        text analysis_summary
        datetime created_at
    }

    impacted_files {
        int id PK
        string analysis_id FK
        string tenant_id FK
        string source_connection_id FK
        text file_path
        text reason "keyword_match|imports_impacted_file|imported_by_impacted_file"
    }

    user_stories {
        string id PK
        string tenant_id FK
        string source_connection_id FK
        string requirement_id
        string impact_analysis_id
        string project_id
        string language "es|en|pt|fr|de"
        string title
        text story_description
        text acceptance_criteria "JSON list"
        text subtasks "JSON {frontend,backend,configuration}"
        text definition_of_done "JSON list"
        text risk_notes "JSON list"
        int story_points
        string risk_level
        float generation_time_seconds
        bool entity_not_found
        string generator_model
        datetime created_at
    }

    story_feedback {
        uuid id PK
        string tenant_id
        string story_id FK
        string user_id
        string rating "thumbs_up|thumbs_down"
        text comment
        datetime created_at
        datetime updated_at
    }

    story_quality_score {
        uuid id PK
        string tenant_id
        string story_id FK
        float completeness "0-10"
        float specificity "0-10"
        float feasibility "0-10"
        float risk_coverage "0-10"
        float language_consistency "0-10"
        float overall
        text justification
        string judge_model
        float dispersion
        int samples_used
        text evidence "JSON dim->cita"
        datetime evaluated_at
    }

    ticket_integrations {
        string id PK
        string tenant_id FK
        string story_id
        string provider "jira|azure_devops"
        string project_key
        string issue_type
        string external_ticket_id
        string status "PENDING|SUCCESS|FAILED"
        int retry_count
        text error_message
        datetime created_at
        datetime updated_at
    }

    integration_audit_logs {
        string id PK
        string tenant_id FK
        string story_id
        string provider
        string action
        text payload "JSON"
        text response "JSON"
        string status
        datetime timestamp
    }

    connection_audit_logs {
        string id PK
        string tenant_id FK
        string connection_id "no FK, sobrevive a delete"
        string platform
        string auth_method
        string event "connection_created|repo_activated|connection_deleted|..."
        string actor
        text detail "JSON"
        datetime timestamp
    }
```

---

## 3. Catálogo de tablas

### 3.1 Identidad y tenancy

| Tabla | Propósito | Puntos clave |
|---|---|---|
| `tenants` | Organización lógica de un usuario en BridgeAI | `auth0_user_id` único; un tenant ↔ un Auth0 user |
| `users` | Perfil resuelto del JWT | `auth0_user_id` único; FK a `tenants.id` |
| `oauth_states` | Estado anti-CSRF para flujos OAuth | `state_token` único; `consumed` evita replay |

### 3.2 Conexiones SCM y de tickets

| Tabla | Propósito | Puntos clave |
|---|---|---|
| `source_connections` | Conexión a un repo (GitHub/GitLab/Azure Repos/Bitbucket) o a un proyecto de tickets (Jira/Azure DevOps) | Tokens encriptados (`EncryptedText`); soporta OAuth y PAT; soft-delete con `deleted_at` |
| `connection_audit_logs` | Eventos sobre conexiones (creada, repo activado, eliminada…) | `connection_id` es texto plano para no perder trazabilidad cuando la conexión se borra |

### 3.3 Indexación de código

| Tabla | Propósito | Puntos clave |
|---|---|---|
| `code_files` | Inventario de archivos del repo indexado | `UNIQUE (tenant_id, source_connection_id, file_path)`; `hash` SHA-256 como detector de cambios; `content` *capped* a 50KB para alimentar análisis y filtrado semántico |

### 3.4 Pipeline de IA

| Tabla | Propósito | Puntos clave |
|---|---|---|
| `requirements` | Clasificación LLM del texto de requerimiento | `UNIQUE (tenant_id, source_connection_id, requirement_text_hash, project_id)` para idempotencia; `keywords` es JSON serializado |
| `impact_analysis` | Resultado del análisis de impacto | `risk_level` calculado por número de archivos impactados (LOW <3, MEDIUM 3-10, HIGH >10) |
| `impacted_files` | Detalle 1:N por análisis | `reason` ∈ `{keyword_match, imports_impacted_file, imported_by_impacted_file}` |
| `user_stories` | Historia generada (artefacto final) | Listas (AC, subtasks, DoD, risk_notes) se guardan como JSON serializado en `Text`; `entity_not_found` flagea historias forzadas sin entidad en código (clave de partición de métricas — ver §4.1); `generator_model` registra el modelo IA usado |
| `story_quality_score` | Output del LLM-as-Judge (5 dimensiones + agregados) | `dispersion` = stdev poblacional cuando hay N>1 muestras; `evidence` = JSON con citas textuales por dimensión baja. Las agregaciones se parten por `user_stories.entity_not_found` para no mezclar runs degradados con runs orgánicos (ver §4.1) |
| `story_feedback` | Reacción del usuario sobre una historia | `UNIQUE (tenant_id, story_id, user_id)` — un usuario un voto por historia |

### 3.5 Integración con sistemas de tickets

| Tabla | Propósito | Puntos clave |
|---|---|---|
| `ticket_integrations` | Estado de cada intento de creación de ticket externo | `status` ∈ `{PENDING, SUCCESS, FAILED}`, `retry_count` controla idempotencia |
| `integration_audit_logs` | Snapshot por intento con `payload` enviado y `response` recibida | Auditable end-to-end; útil para debugging de errores 4xx/5xx del proveedor externo |

---

## 4. Patrón de aislamiento (defensa en profundidad)

```mermaid
flowchart LR
    JWT[JWT Auth0] --> A[get_current_user]
    A --> B[ContextVar:<br/>current_tenant_id]
    B --> C[Repository._tid]
    C --> D[(SELECT ... WHERE tenant_id = :tid<br/>AND source_connection_id = :scid)]

    style B fill:#0f5,color:#000
    style D fill:#fa5,color:#000
```

Toda tabla con `tenant_id` se consulta a través de un repository en `app/repositories/`. La regla es: **ningún SELECT/INSERT/UPDATE/DELETE se hace sin `tenant_id`** y, cuando aplica, sin `source_connection_id`. Si el `ContextVar` no está poblado, `_tid()` lanza `RuntimeError` antes de tocar la BD.

---

### 4.1 Partición de métricas de calidad (organic vs forced)

Las consultas agregadas sobre `story_quality_score` siempre se parten por `user_stories.entity_not_found` para que las historias forzadas (donde el juez aplica caps duros por diseño) no contaminen el promedio "real". El método `StoryQualityRepository.summary_since(since)` resuelve los tres buckets en una sola query con `CASE` (portátil entre PostgreSQL y SQLite de tests):

```sql
SELECT
  AVG(CASE WHEN us.entity_not_found = false THEN sqs.overall END) AS organic_avg,
  AVG(CASE WHEN us.entity_not_found = true  THEN sqs.overall END) AS forced_avg,
  COUNT(CASE WHEN us.entity_not_found = false THEN 1 END)         AS organic_count,
  COUNT(CASE WHEN us.entity_not_found = true  THEN 1 END)         AS forced_count,
  AVG(sqs.overall) AS all_avg,
  COUNT(*)         AS all_count
FROM story_quality_score sqs
JOIN user_stories us
  ON us.id = sqs.story_id
 AND us.tenant_id = sqs.tenant_id     -- defensa en profundidad
WHERE sqs.tenant_id = :tid
  AND sqs.evaluated_at >= :since;
```

Notas operativas:

- El JOIN incluye doble tenant check (lado score y lado story) — defensa en profundidad para que un score huérfano de otro tenant nunca se cuele.
- `AVG()` ignora NULLs, así que el `CASE` sin `ELSE` produce el filtro correcto.
- Mismo patrón en `avg_overall_since(since, forced=...)` y `count_evaluated_since(since, forced=...)` cuando se necesita un solo bucket.
- Endpoint que materializa la consulta: `GET /api/v1/system/quality/live?days=N` (con `N` clamped a `[1, 365]`).

---

## 5. Índices y restricciones notables

| Tabla | Índice / Constraint | Por qué |
|---|---|---|
| `code_files` | `uq_code_files_tenant_connection_path` UNIQUE | No duplicar el mismo path dentro de un mismo repo |
| `requirements` | `uq_requirements_tenant_connection_hash_project` UNIQUE | Idempotencia: misma frase + proyecto = misma fila |
| `impact_analysis` | `ix_impact_analysis_tenant_connection` | Listar análisis del repo activo |
| `impacted_files` | `ix_impacted_files_tenant_connection` | Joins rápidos al construir la whitelist de paths para la generación |
| `user_stories` | `ix_user_stories_req_analysis_conn`, `ix_user_stories_tenant_connection` | Cache hit por `(req, analysis, conn)` y listados por repo |
| `story_feedback` | `uq_story_feedback_per_user` | Un usuario, un rating por historia |
| `story_quality_score` | `story_id` UNIQUE | Una evaluación vigente por historia |
| `ticket_integrations` | `ix_ticket_integrations_story_provider` | Idempotencia: verificar si la historia ya tiene ticket en ese provider |

---

## 6. Encriptación de campos sensibles

```mermaid
flowchart LR
    APP[Servicio] -- access_token plano --> ORM[EncryptedText]
    ORM -- Fernet encrypt --> PG[(PostgreSQL)]
    PG -- bytes encriptados --> ORM
    ORM -- Fernet decrypt --> APP

    KEY[FIELD_ENCRYPTION_KEY] -.usa.-> ORM
```

- `source_connections.access_token` y `refresh_token` usan `EncryptedText` (Fernet, simétrico, AES-128 + HMAC).
- La clave se inyecta vía `Settings.FIELD_ENCRYPTION_KEY`. En **prod** la app no arranca si está vacía (validación en `create_app()`).
- Generación: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

---

## 7. Migraciones (Alembic)

```bash
# Crear migración a partir de cambios en modelos
python -m alembic revision --autogenerate -m "descripcion"

# Aplicar al último head
python -m alembic upgrade head

# Revertir una
python -m alembic downgrade -1
```

### Hitos importantes en `alembic/versions/`

| Migración | Cambio |
|---|---|
| `332bc705e042_initial_multitenant_schema` | Esquema inicial multi-tenant |
| `a3f9d2c1b845_user_based_tenancy` | Migración de tenancy basada en usuario |
| `b7e4f3a2c910_clerk_to_auth0` | Reemplazo de Clerk por Auth0 |
| `c3f1a2b4d567_add_source_connection_id_to_code_files` | Phase 7 — `source_connection_id` en `code_files` |
| `d8a1c3f5e912_scope_stories_analysis_req_to_connection` | Phase 7 — propagar el scope a stories/analysis/requirements |
| `b5e2c3d4f901_encrypt_token_fields` | Encriptación Fernet de tokens OAuth |
| `9e9759024c61_widen_token_columns_to_text` | Tokens OAuth pasan a `Text` por longitudes variables |
| `a03dd37be40a_story_feedback_and_quality_score` | Tablas de feedback y quality score |
| `b9d4f7e2c815_add_dispersion_samples_evidence` | LLM-as-Judge: dispersión, samples y evidencia |
| `e7b1c4a3d925_add_entity_not_found_to_user_stories` | Flag de generación forzada sin entidad |
| `f3a2b5c1d847_add_generator_model_to_user_stories` | Persistir el modelo IA usado por historia |
| `a1b2c3d4e5f6_preserve_history_on_connection_delete` | Quitar FK estricta del audit log |
| `b2c3d4e5f6a7_soft_delete_connections` | `deleted_at` en `source_connections` |
| `c6d3e4f5a012_add_connection_audit_log` / `d1e2f3a4b567_ensure_connection_audit_logs` | Audit log de conexiones |

---

## 8. Conexiones y pool

```python
# app/database/session.py
create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # detecta conexiones rotas
    future=True,
)
```

- `pool_size=5`, `max_overflow=10` — adecuado para cargas medias; ajustar si el deploy escala horizontalmente.
- `pool_pre_ping=True` — emite un `SELECT 1` antes de devolver una conexión para evitar `OperationalError` por timeouts del lado servidor.
- `get_db()` se usa como dependencia FastAPI; `check_db_connection()` solo para health checks.

---

## 9. Operación

```bash
# Levantar PostgreSQL local
docker compose up -d

# Aplicar migraciones (primer arranque o tras pull)
python -m alembic upgrade head

# Cadena de conexión por defecto (.env.example)
DATABASE_URL=postgresql://bridgeai:bridgeai@localhost:5432/bridgeai
```

Backups y borrado masivo: están fuera del alcance de la app. Para producción, usar el snapshot del proveedor cloud y/o `pg_dump`. El soft-delete de `source_connections` permite restaurar accesos sin recrear el OAuth.
