# BridgeAI Workflow Guide — Optimized for Token Efficiency

**Updated:** May 2, 2026  
**Goal:** Maximum clarity + minimum iterations = token savings + faster delivery

---

## 🤖 All Agents Quick Reference

| You say | I invoke | Time | Triggers |
|---------|----------|------|----------|
| "Fix typo in X" | Direct (Read+Edit) | 1 min | — |
| "Update X config" | Direct (Read+Edit) | 2 min | — |
| **Create domain object X with fields Y** | **domain-modeler** | 5 min | "create domain object", "add domain entity", "model the X domain", "new value object" |
| **Create endpoint /api/v1/X that does Y** | **api-route-builder** | 15 min | "add endpoint", "create route", "new API for X", "build the X endpoint" |
| **Write tests for service X** | **test-specialist** | 10 min | "write tests for", "add test coverage", "test this service", "missing tests" |
| **Create page/component Y in frontend** | **nextjs-frontend-builder** | 15 min | "create page", "add component", "build frontend for X", "new UI for X", "conectar UI con API", "agregar pantalla", "crear componente" |
| **Check code for layer violations** | **clean-arch-guardian** | 10 min | "review architecture", "check clean arch", "validate layers" (auto-runs after `app/` edits) |
| **Audit code for security vulns** | **security-guardian** | 15 min | "security audit", "find vulnerabilities", "security review", "check for holes", "harden the API", "security best practices" |
| **Review my PR/branch** | **(review skill)** | 10 min | `/review` command or "review my changes" |

---

## 📋 Agent Details — When to Use Each

### 1️⃣ **domain-modeler** — Create pure domain objects
```
✅ Use when: You need a new frozen dataclass in app/domain/
Example: "Create domain object for AnalyticsEvent with fields: id, user_id, event_type, timestamp"
Output: Frozen dataclass with zero side effects
Includes: /simplify gate
```

### 2️⃣ **api-route-builder** — Build entire endpoints (vertical slice)
```
✅ Use when: Full endpoint needed (domain + service + route + test)
Example: "Create endpoint GET /api/v1/metrics that returns aggregated data"
Output: Domain object + Service logic + FastAPI route + Tests
Includes: /simplify + /security-review gates
```

### 3️⃣ **test-specialist** — Write quality tests
```
✅ Use when: Need test coverage for existing code
Example: "Write tests for RequirementCoherenceValidator"
Output: Pytest tests with happy path + edge cases + cross-tenant isolation
No mocking: Uses real SQLite in-memory DB
```

### 4️⃣ **nextjs-frontend-builder** — Build React components & pages
```
✅ Use when: New page, component, or feature in frontend/
Example: "Create component showing real-time user activity"
Output: TypeScript React component, styled with design tokens, i18n integrated
Includes: /simplify + /security-review gates
```

### 5️⃣ **clean-arch-guardian** — Architecture review
```
✅ Use when: Check if code violates Clean Architecture rules
Example: "Review the changes I made for layer violations"
Output: List of violations with concrete fixes
No code changes: Just analysis + recommendations
```

### 6️⃣ **security-guardian** — Security audit
```
✅ Use when: Find and fix security vulnerabilities
Example: "Run security audit on my changes"
Output: Findings by severity (CRITICAL → HIGH → MEDIUM → LOW)
Fixes: I fix CRITICAL/HIGH, you decide on MEDIUM/LOW
```

---

## Quick decision tree

```
I need to...
│
├─ Fix a bug (1-2 files)
│  └─ You: "Fix X" → Me: Direct edit → Done
│
├─ Change one file (typo, config, update)
│  └─ You: "Update X to Y" → Me: Read + Edit → Done
│
├─ Create pure domain object
│  └─ Use: domain-modeler
│
├─ Create full API endpoint
│  └─ Use: api-route-builder
│
├─ Test existing code
│  └─ Use: test-specialist
│
├─ Build React component/page
│  └─ Use: nextjs-frontend-builder
│
├─ Check architecture compliance
│  └─ Use: clean-arch-guardian
│
├─ Find security issues
│  └─ Use: security-guardian
│
└─ Review my code
   └─ Use: /review skill
```

---

## How agents work (behind the scenes)

Each agent has:
- **Specialized tools** (domain-modeler has Write, not Bash)
- **Checklist** (each agent verifies all critical steps)
- **Quality gates** (automatically runs /simplify, /security-review)
- **Focused context** (no distraction, one job)

**Result:** Better code, faster, fewer iterations.

---

## Before starting any task

### ✅ Clear request (proceed immediately):
```
"Create domain object User with fields: id (UUID), email (str), role (enum: admin|user)"
```

### ❌ Vague request (I'll ask for clarification):
```
"Build user management"
→ I ask: "Which endpoints? Auth required? Schema?"
```

### ⏳ Complex task (I'll use EnterPlanMode):
```
"Implement a feature that does X, Y, and Z with integration to A"
→ I: EnterPlanMode to show 2-3 options → You pick → I implement
```

---

## How I work — the flow

### For 1-line changes:
```
You: "Fix typo on line 42 of file X"
  ↓
Me: Read file (just that section) → Edit → Commit
  ↓
Result: Done in 30 seconds, 1 response
```

### For small features:
```
You: "Add endpoint GET /api/v1/settings that returns user language preference"
  ↓
Me: Read routes + models → Write route + tests → Commit
  ↓
Result: Done in 3 minutes, 1 response
```

### For large features or phases:
```
You: "Implement phase 9: analytics dashboard"
  ↓
Me: EnterPlanMode (explore + show options) → You approve
  ↓
Me: Spawn phase-implementer agent → Full end-to-end build
  ↓
Result: Done in 1-2 hours, quality gates included (/simplify + /security-review)
```

### For code review:
```
You: "I made some changes, can you review them?"
  ↓
Me: clean-arch-guardian (architecture) + security-guardian (vulnerabilities)
  ↓
Result: List of issues + fixes
```

---

## Response format I use

### Short tasks:
```
[1 sentence what I'm doing]

<tool calls>

[1-2 sentences: result + next step]
```

### Complex tasks:
```
[Brief overview]

<exploratory tool calls if needed>

[Findings + approach recommendation]

(OR)

[Final tool calls to implement]

[Quick validation]
```

**What I DON'T do:**
- "Here's a summary of what I just did" (you can see the diff)
- "Does this look right?" (I verify before declaring done)
- "Let me check one more thing" (I read what I need, then act)

---

## Commits — automatic

✅ I create commits automatically when code is complete.  
✅ Format: `type(scope): message` — e.g. `feat(dashboard): add user widget`  
✅ One commit per logical unit (feature, fix, docs)

---

## Settings & automation

File: `.claude/settings.json`

**What's configured:**
- ✅ Read/Glob/Grep allowed without prompt (zero overhead)
- ✅ Git read-only ops allowed (status, log, diff)
- ✅ Tests + pytest allowed without prompt
- ✅ Quality skills allowed (/simplify, /security-review, /claude-api)
- ⚠️ Destructive git ops require confirmation (reset, force push)
- ⚠️ Agent spawning requires confirmation (verify context)

**Result:** ~50% fewer permission prompts vs default.

---

## Memory — your context, always loaded

Files in: `C:\Users\fgomez\.claude\projects\C--proyectos-bridgeai\memory\`

**What I remember across sessions:**
- Stack decisions (Next.js 16, Auth0, FastAPI)
- Your preferences (no middleware.ts, use proxy.ts)
- Architecture rules (Clean Arch layer violations, tenant isolation)
- Technical patterns (how to build domains, services, repos)

**What I DON'T remember (read live each time):**
- Git history (use `git log`)
- Current code state (read files, don't assume)
- In-progress work (stored in git, not memory)

---

## Quality gates — automatic quality

After I write code:
1. `/simplify` — remove duplication, over-engineering, unnecessary abstractions
2. `/security-review` — find HIGH/MEDIUM vulns (I fix them, report LOW)
3. (For AI features) `/claude-api` — verify caching, models, error handling

**These run automatically on large tasks.** Small edits skip them unless you ask.

---

## Common scenarios & optimal responses

### Scenario: Build a new feature
```
You: "Create endpoint POST /api/v1/analytics with body {event_type, user_id}"
  ↓
Me: Invoke api-route-builder (includes domain + service + route + tests)
  ↓
Result: All 4 layers built, tested, quality gates passed
```

### Scenario: You want multiple features built in parallel
```
You: "Build feature A (endpoint), B (component), C (tests)"
  ↓
Me: Spawn three agents in parallel
  Agent 1: api-route-builder for feature A
  Agent 2: nextjs-frontend-builder for feature B
  Agent 3: test-specialist for feature C
  ↓
Result: All done in ~same time as one
```

### Scenario: Security review needed
```
You: "I pushed changes, please audit them for security"
  ↓
Me: security-guardian agent (runs full checklist: injection, SSRF, cross-tenant leaks, etc.)
  ↓
Result: CRITICAL/HIGH findings fixed automatically, MEDIUM/LOW reported
```

### Scenario: You want to review my code
```
You: "/review"
  ↓
Me: clean-arch-guardian (checks layers) + security-guardian (checks vulns)
  ↓
Result: Issues found + recommendations to fix
```

---

## Communication shortcuts

**You can say:**
```
"Use the domain-modeler"          → I invoke that agent
"Parallel this"                   → I run multiple things at once
"Quick check: does X work?"       → I read code, give 1-line yes/no
"Why did you Y?"                  → I explain the decision
"Try approach B instead"          → I pivot without question
"/schedule this every Monday"     → I set up a recurring agent
```

**You DON'T need to say:**
```
"Please"                          (assumed)
"Is this correct?"                (I verify before saying done)
"Here's the context..."           (I read code, don't rely on your summary)
"Can you..."                      (assumed I can, ask if I can't)
```

---

## Troubleshooting

### Q: "Why didn't you use [agent X] for this?"
**A:** Either it wasn't the right fit, or I should have. Tell me and I'll course-correct.

### Q: "Can I invoke an agent directly?"
**A:** Yes! Say "use domain-modeler" or "invoke phase-implementer" and I will.

### Q: "Why didn't you parallelize that?"
**A:** Either the tasks depend on each other, or I missed it. Tell me.

### Q: "This should use an agent, not direct edit."
**A:** You're right. Say "use [agent]" or describe the task and I'll suggest it.

---

## Token budget

**Your budget:** Roughly 200k tokens/session (auto-compresses at 80% full)

**How to stay under budget:**
1. Clear requirements (no "what should I do?" loop)
2. Parallel tool calls (1 call vs 3 calls = 60% savings)
3. Use agents for complex work (agent has focused context)
4. Avoid long iterative conversations (commit, move on)

---

## Next time you have a task

**Just tell me what you need.** I'll:
1. ✅ Ask for clarity if needed (1 question max)
2. ✅ Use EnterPlanMode if it's complex (show you options)
3. ✅ Use the right agent or tool (no waste)
4. ✅ Parallelize if possible (fast)
5. ✅ Run quality gates (clean code)
6. ✅ Commit when done (you can review)

**You never need to worry about:**
- Permission prompts (settings.json handles common ops)
- "Am I using the right agent?" (I choose based on your description)
- "Is this code good?" (quality gates verify)
- "What did you do?" (git log + diff tell the story)

---

**Happy coding! Use any agent anytime — just describe what you need.**
