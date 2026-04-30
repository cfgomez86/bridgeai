# BridgeAI Security Architecture Review

## Scope
FastAPI + SQLAlchemy + Auth0 backend (`app/`) and Next.js frontend (`frontend/`).
Multi-tenant SaaS — tenant isolation is the primary attack surface.

---

## Review History

| Date | Reviewer | Notes |
|------|----------|-------|
| 2026-04-29 | Security Guardian (Claude) | Initial audit — v1 |

---

## Findings

### [x] FIXED — HIGH-1: Cross-tenant title leak via unguarded JOIN in StoryFeedbackRepository

**File:** `app/repositories/story_feedback_repository.py:89`  
**Description:** `list_with_comments()` joined `StoryFeedback` to `UserStory` on `id` only, without a `UserStory.tenant_id == self._tid()` condition. Because `story_id` values are UUIDs without a database-level FK uniqueness constraint spanning tenants, a crafted scenario where two tenants happen to have the same story UUID (or under a future bulk-insert vulnerability) could return the title of a story belonging to another tenant.  
**Evidencia (before fix):**
```python
.join(UserStory, UserStory.id == StoryFeedback.story_id)
```
**Fix applied:** Added `& (UserStory.tenant_id == tid)` to the JOIN condition.
```python
.join(
    UserStory,
    (UserStory.id == StoryFeedback.story_id)
    & (UserStory.tenant_id == tid),
)
```
**Test:** `python -m pytest tests/unit/test_story_feedback_repository.py -v`

---

### [x] FIXED — HIGH-2: Exception message disclosure in HTTP 500 responses

**Files:**
- `app/api/routes/understand_requirement.py:79` — `detail=f"Understanding failed: {exc}"`
- `app/api/routes/ticket_integration.py:147` — `detail=f"Ticket creation failed: {exc}"`
- `app/api/routes/story_generation.py:441` — `detail=f"Quality evaluation failed: {exc}"`

**Description:** Unhandled exceptions from downstream services (AI provider, Jira, Azure DevOps) were interpolated into HTTP response details. These strings may contain internal service names, API endpoint URLs, HTTP status lines from third-party APIs, or stack traces, constituting information disclosure.  
**Fix applied:** All three catch-all `except Exception` handlers now return a fixed opaque string; the original exception is still logged server-side.  
**Test:** The global `unhandled_exception_handler` in `app/main.py` already returns `"Internal server error."` for truly unhandled exceptions — this fix brings the caught-but-leaking paths in line with that policy.

---

### [x] FIXED — HIGH-3: PAT provider error exposed in 400 response

**File:** `app/api/routes/connections.py:194`  
**Description:** `connect_pat()` caught `ValueError` from `SourceConnectionService.create_pat_connection()` and returned `detail=str(exc)`. The service wraps provider exceptions as `ValueError(f"PAT validation failed: {original_exc}")`, which could expose underlying HTTP error messages from external SCM/ticketing APIs (e.g., authentication failure bodies from GitHub or Jira).  
**Fix applied:** The `except ValueError` block now returns a fixed `"PAT validation failed — check the token, URL, and try again."` without re-exposing the inner message.  
**Test:** `python -m pytest tests/integration/test_indexing_endpoint.py tests/integration/test_ticket_integration_endpoint.py -v`

---

### [x] FIXED — HIGH-4: Bulk ticket failure message leaks internal exceptions

**File:** `app/api/routes/ticket_integration.py:200-203`  
**Description:** `_create_one()` in the bulk endpoint returned `error=str(exc)` for any exception, including unhandled internal errors that could expose DB state, provider responses, or stack information.  
**Fix applied:** Domain exceptions (`StoryNotFoundError`, `UnsupportedProviderError`, `ProviderNotConfiguredError`) are still stringified because they carry safe user-facing messages. A separate `except Exception` handler returns a fixed opaque string.  
**Test:** `python -m pytest tests/integration/test_ticket_integration_endpoint.py -v`

---

### [x] FIXED — MEDIUM-1: JWKS cache does not refresh on unknown `kid`

**File:** `app/core/auth0_auth.py`  
**Description:** The JWKS cache was TTL-only (1 hour). If Auth0 rotated signing keys during the TTL window, tokens signed with the new key (carrying an unknown `kid`) would fail validation permanently until the cache expired. This could cause a hard authentication outage for all users.  
**Fix applied:** `verify_auth0_jwt()` now extracts the `kid` from the unverified token header. If the kid is absent from the cached JWKS, a single cache-bypass refresh is performed before attempting decode. This is the standard "cache-then-refresh" JWKS pattern and does not enable DoS (the refresh is bounded to one per unknown kid per decode call, not per request).  
**Test:** `python -m pytest tests/integration/test_health.py tests/unit/test_user_provisioning_service.py -v`

---

## Items Verified — No Issue Found

| Check | Result |
|-------|--------|
| Hardcoded secrets in `app/` | None found (grep for `sk-`, `ghp_`, `glpat-`, `xoxb-`, `AKIA`, literal `api_key =`, `password =`) |
| SQL injection via `text()` with f-strings | Not present; only `text("SELECT 1")` (literal) in `session.py` health check |
| Command injection (subprocess/os.system with user data) | No subprocess/os.system/os.popen calls in `app/` |
| Path traversal in local indexing (`_walk_files`) | Protected by `os.path.realpath` + `os.path.commonpath` guard (line 144-151 of `code_indexing_service.py`) |
| ContextVar bare `.get()` outside `context.py` | Only `current_tenant_id.set()` calls in auth and OAuth callback — no unguarded `.get()` |
| ORM model imports in services | Only `SourceConnection` (domain mapping) and `User`/`Tenant` (provisioning) — acceptable |
| All non-health routes guarded by `get_current_user` | Yes — `connections.py` applies auth per-endpoint; OAuth callback explicitly sets tenant from stored state |
| `dashboard.py` router auth | Router-level `dependencies=[Depends(get_current_user)]` — confirmed |
| FIELD_ENCRYPTION_KEY guard in prod | `app/main.py:35` — RuntimeError raised if `APP_ENV=prod` and key is empty |
| `access_token`/`refresh_token` encrypted at rest | `SourceConnection.access_token` and `.refresh_token` use `EncryptedText` TypeDecorator |
| `.env` in `.gitignore` | Confirmed — `.env`, `.env.local`, `.env.*.local`, `.env.prod` all listed |
| `.env` in git history | No commits found for `.env` |
| CORS configuration | Explicit origins required; wildcard raises RuntimeError; `allow_credentials=True` |
| Security headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy all set; HSTS on HTTPS non-localhost |
| NEXT_PUBLIC_ secrets | Only `NEXT_PUBLIC_API_URL` (API base URL — not a secret) |
| `dangerouslySetInnerHTML` | Only in `layout.tsx` — static, hardcoded theme-init script with no user input |
| Open redirect via `router.push` | Only hardcoded paths (`/workflow`) or server-sourced activity feed links |
| OAuth callback redirect | Redirects only to `settings.FRONTEND_URL` (server-controlled config) |
| SQL — `.query().all()/.count()` without tenant filter | All repositories filter `tenant_id == self._tid()` before any query |

---

## Outstanding Items (MEDIUM / LOW — No Auto-Fix)

### MEDIUM-1: `python-jose` 3.5.0 — no published CVEs fixed, but library is unmaintained

**Description:** `python-jose` has not had a release since 2023. CVE-2024-33663 (algorithm confusion) and CVE-2022-29217 (EC key type confusion) affect earlier versions. The current configuration (`algorithms=["RS256"]`, JWKS public keys) mitigates both known CVEs. Consider migrating to `PyJWT` or `joserfc` which are actively maintained.  
**Recommended action:** Evaluate migration to `PyJWT>=2.8.0` before next major version release.

### LOW-1: `pip` CVE-2026-3219 — confusing tar+zip install behavior

**Description:** Affects `pip` at install time when handling ambiguous archive formats. No fix available yet. Not a runtime vulnerability.  
**Recommended action:** Update `pip` when a fix is released.

### LOW-2: `postcss <8.5.10` in npm dependency chain (moderate XSS)

**Description:** `npm audit` reports `postcss` < 8.5.10 via `next` → `@auth0/nextjs-auth0`. The vulnerability (GHSA-qx2v-qp2m-jg93) is a CSS XSS in stringify output. The fix requires `npm audit fix --force` which would downgrade Next.js to 9.x (breaking change). No user-controlled CSS is stringified in BridgeAI.  
**Recommended action:** Track Next.js updates; apply fix when a non-breaking path is available.

### LOW-3: `error_description` from OAuth provider logged (not in response)

**File:** `app/api/routes/connections.py:149-150`  
**Description:** The `error_description` query parameter (set by the OAuth provider, not user-controllable in practice) is logged. If a malicious authorization server were used, it could inject content into log files. The value is NOT included in the HTTP response.  
**Recommended action:** Sanitize logged `error_description` to alphanumeric + spaces (low priority).

---

## Summary Table

| Severity | Total Found | Fixed | Outstanding |
|----------|------------|-------|-------------|
| CRITICAL | 0 | — | — |
| HIGH | 4 | 4 | 0 |
| MEDIUM | 2 | 1 | 1 |
| LOW | 3 | 0 | 3 |
| **Total** | **9** | **5** | **4** |
