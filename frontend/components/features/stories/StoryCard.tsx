"use client"

import { useState, useRef, useEffect } from "react"
import { Trash2, Plus, CheckCircle, Code, ListChecks, FileText, AlertTriangle, Lock, Loader2, GitPullRequest, ChevronDown } from "lucide-react"
import { updateStory, type StoryDetailResponse, type Subtask } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface StoryCardProps {
  story: StoryDetailResponse
  onSaved: (updated: StoryDetailResponse) => void
  onToast: (msg: string, tone: "ok" | "err") => void
}

type Cat = "frontend" | "backend" | "configuration"

// Variant C: click-to-edit (Notion-style), matches design file step34-full.jsx
const editableCSS = `
input[type=number]::-webkit-outer-spin-button,
input[type=number]::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

[data-edit-style="C"] .field {
  position: relative;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 4px 8px;
  cursor: text;
  transition: background 120ms, border-color 120ms;
}
[data-edit-style="C"] .field:hover { background: var(--surface-2); }
[data-edit-style="C"] .field:focus-within {
  background: var(--surface);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent) 10%, transparent);
}
[data-edit-style="C"] .field input,
[data-edit-style="C"] .field textarea {
  width: 100%; box-sizing: border-box;
  background: transparent; border: none; outline: none;
  font: inherit; color: inherit; padding: 0;
}
[data-edit-style="C"] .field textarea { resize: vertical; }

.crit-row {
  display: grid; grid-template-columns: 22px 1fr 24px; gap: 8px; align-items: start;
  padding: 4px 0;
}
.crit-num {
  width: 22px; height: 22px; border-radius: 6px;
  background: var(--surface-3); color: var(--fg-2);
  font-family: var(--font-mono); font-size: 10.5px; font-weight: 700;
  display: grid; place-items: center; flex-shrink: 0; margin-top: 2px;
  border: 1px solid var(--border);
}
.row-del {
  width: 24px; height: 24px; border-radius: 6px;
  border: 1px solid transparent; background: transparent;
  color: var(--muted-2); cursor: pointer;
  display: grid; place-items: center;
  opacity: 0; transition: opacity 120ms, background 120ms;
  margin-top: 2px;
}
.crit-row:hover .row-del { opacity: 1; }
.row-del:hover { background: var(--err-bg); color: var(--err-fg); border-color: transparent; }
.row-del:disabled { display: none; }

.add-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 999px;
  border: 1px dashed var(--border-strong);
  background: transparent; color: var(--muted);
  font-size: 11.5px; font-weight: 500; cursor: pointer;
  transition: all 120ms; margin-top: 8px; font-family: inherit;
}
.add-pill:hover {
  background: var(--accent-soft); color: var(--accent-strong);
  border-color: var(--accent); border-style: solid;
}
`

function AutoTextarea({ value, onChange, style, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto"
      ref.current.style.height = ref.current.scrollHeight + "px"
    }
  }, [value])
  return (
    <textarea
      ref={ref}
      value={value}
      onChange={onChange}
      {...props}
      style={{ ...style, overflow: "hidden", resize: "none" }}
    />
  )
}

function FieldGroup({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  const labelStyle: React.CSSProperties = {
    fontSize: "10.5px", fontWeight: 700, textTransform: "uppercase",
    letterSpacing: "0.08em", color: "var(--muted)",
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
        <span style={{ display: "inline-flex", color: "var(--muted)" }}>{icon}</span>
        <span style={labelStyle}>{label}</span>
      </div>
      {children}
    </div>
  )
}

export function StoryCard({ story, onSaved, onToast }: StoryCardProps) {
  const { t } = useLanguage()
  const s = t.workflow.step3
  const ts = t.stories
  const locked = !!story.is_locked

  const [title, setTitle] = useState(story.title)
  const [description, setDescription] = useState(story.story_description)
  const [ac, setAc] = useState([...story.acceptance_criteria])
  const [subtasks, setSubtasks] = useState<Record<Cat, Subtask[]>>({
    frontend: story.subtasks.frontend.map(st => ({ ...st })),
    backend: story.subtasks.backend.map(st => ({ ...st })),
    configuration: story.subtasks.configuration.map(st => ({ ...st })),
  })
  const [dod, setDod] = useState([...story.definition_of_done])
  const [riskNotes, setRiskNotes] = useState([...story.risk_notes])
  const [storyPoints, setStoryPoints] = useState(story.story_points)
  const [riskLevel, setRiskLevel] = useState(story.risk_level)
  const [isDirty, setIsDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [open, setOpen] = useState(true)

  function mark() { setIsDirty(true) }

  function updateAc(i: number, v: string) { const n = [...ac]; n[i] = v; setAc(n); mark() }
  function removeAc(i: number) { setAc(ac.filter((_, j) => j !== i)); mark() }
  function addAc() { setAc([...ac, ""]); mark() }

  function updateDod(i: number, v: string) { const n = [...dod]; n[i] = v; setDod(n); mark() }
  function removeDod(i: number) { setDod(dod.filter((_, j) => j !== i)); mark() }
  function addDod() { setDod([...dod, ""]); mark() }

  function updateRisk(i: number, v: string) { const n = [...riskNotes]; n[i] = v; setRiskNotes(n); mark() }
  function removeRisk(i: number) { setRiskNotes(riskNotes.filter((_, j) => j !== i)); mark() }
  function addRisk() { setRiskNotes([...riskNotes, ""]); mark() }

  function updateSubTitle(cat: Cat, i: number, v: string) {
    setSubtasks(p => { const u = [...p[cat]]; u[i] = { ...u[i], title: v }; return { ...p, [cat]: u } }); mark()
  }
  function updateSubDesc(cat: Cat, i: number, v: string) {
    setSubtasks(p => { const u = [...p[cat]]; u[i] = { ...u[i], description: v }; return { ...p, [cat]: u } }); mark()
  }
  function removeSub(cat: Cat, i: number) {
    setSubtasks(p => ({ ...p, [cat]: p[cat].filter((_, j) => j !== i) })); mark()
  }
  function addSub(cat: Cat) {
    setSubtasks(p => ({ ...p, [cat]: [...p[cat], { title: "", description: "" }] })); mark()
  }

  async function handleSave() {
    setSaving(true)
    try {
      const updated = await updateStory(story.story_id, {
        source_connection_id: story.source_connection_id,
        title, story_description: description,
        acceptance_criteria: ac, subtasks,
        definition_of_done: dod, risk_notes: riskNotes,
        story_points: storyPoints, risk_level: riskLevel,
      })
      onSaved(updated)
      setIsDirty(false)
      onToast(ts.edit_saved, "ok")
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      onToast(msg.toLowerCase().includes("locked") ? ts.locked_error : msg, "err")
    } finally {
      setSaving(false)
    }
  }

  function handleDiscard() {
    setTitle(story.title)
    setDescription(story.story_description)
    setAc([...story.acceptance_criteria])
    setSubtasks({
      frontend: story.subtasks.frontend.map(st => ({ ...st })),
      backend: story.subtasks.backend.map(st => ({ ...st })),
      configuration: story.subtasks.configuration.map(st => ({ ...st })),
    })
    setDod([...story.definition_of_done])
    setRiskNotes([...story.risk_notes])
    setStoryPoints(story.story_points)
    setRiskLevel(story.risk_level)
    setIsDirty(false)
  }

  const divider: React.CSSProperties = { height: "1px", background: "var(--border)", margin: "2px 0" }

  const riskSelectStyle: React.CSSProperties = {
    padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 700,
    fontFamily: "var(--font-mono)", letterSpacing: "0.02em",
    border: "1px solid transparent",
    background: riskLevel === "HIGH" ? "var(--err-bg)" : riskLevel === "MEDIUM" ? "var(--warn-bg)" : "var(--ok-bg)",
    color: riskLevel === "HIGH" ? "var(--err-fg)" : riskLevel === "MEDIUM" ? "var(--warn-fg)" : "var(--ok-fg)",
    cursor: locked ? "default" : "pointer", outline: "none",
  }

  const catLabels: Record<Cat, string> = {
    frontend: s.subtasks_frontend,
    backend: s.subtasks_backend,
    configuration: s.subtasks_configuration,
  }

  return (
    <>
      {/* Story editing card */}
      <div
        data-edit-style="C"
        style={{
          background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "12px",
          padding: "20px 22px", display: "flex", flexDirection: "column", gap: "14px",
          boxShadow: "0 6px 20px oklch(0.2 0.02 260 / 0.04)",
        }}
      >
        <style>{editableCSS}</style>

        {/* Card header — clickable to collapse */}
        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "none", border: "none", cursor: "pointer",
            padding: 0, textAlign: "left", color: "var(--fg)",
          }}
        >
          <GitPullRequest size={14} style={{ color: "var(--accent-strong)", flexShrink: 0 }} />
          <span style={{ fontSize: "13px", fontWeight: 600, fontFamily: "var(--font-display)", color: "var(--fg)", flex: 1 }}>
            {ts.story_ready}
          </span>
          {locked && (
            <span style={{
              display: "inline-flex", alignItems: "center", gap: "4px",
              padding: "1px 7px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
              background: "var(--surface-3)", color: "var(--muted)",
            }}>
              <Lock size={10} /> {ts.locked_badge}
            </span>
          )}
          <ChevronDown
            size={14}
            style={{
              flexShrink: 0, color: "var(--muted)",
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.15s",
            }}
          />
        </button>

        {open && <div style={divider} />}

        {/* Title row: story ID chip + editable title */}
        {open && <>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 600, color: "var(--muted)",
            padding: "2px 8px", borderRadius: "4px",
            background: "var(--surface-2)", border: "1px solid var(--border)", flexShrink: 0,
          }}>
            {story.story_id.slice(0, 10)}
          </span>
          <div className="field" style={{ flex: 1 }}>
            <input
              disabled={locked}
              value={title}
              onChange={e => { setTitle(e.target.value); mark() }}
              style={{ fontSize: "18px", fontWeight: 600, fontFamily: "var(--font-display)", color: "var(--fg)", letterSpacing: "-0.01em" }}
            />
          </div>
        </div>

        {/* Meta: story points + risk level */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 10,
            padding: "3px 10px", borderRadius: "6px",
            background: "var(--accent-soft)", color: "var(--accent-strong)",
            fontFamily: "var(--font-mono)", fontSize: "12px", fontWeight: 700,
          }}>
            <input
              type="number" min={1} max={100} disabled={locked}
              value={storyPoints}
              onChange={e => { setStoryPoints(Number(e.target.value)); mark() }}
              style={{
                width: "32px", background: "transparent", border: "none", outline: "none",
                color: "inherit", font: "inherit", textAlign: "right", padding: 0,
                cursor: locked ? "default" : "text",
              }}
            />
            <span>{storyPoints === 1 ? s.point : s.points}</span>
          </span>
          <select
            disabled={locked}
            value={riskLevel}
            onChange={e => { setRiskLevel(e.target.value); mark() }}
            style={riskSelectStyle}
          >
            <option value="LOW">LOW</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="HIGH">HIGH</option>
          </select>
        </div>

        <div style={divider} />

        {/* Description */}
        <FieldGroup label={s.description_label} icon={<FileText size={12} />}>
          <div className="field">
            <AutoTextarea
              disabled={locked}
              value={description}
              onChange={e => { setDescription(e.target.value); mark() }}
              style={{ fontSize: "12.5px", color: "var(--fg-2)", lineHeight: 1.6 }}
            />
          </div>
        </FieldGroup>

        <div style={divider} />

        {/* Acceptance Criteria */}
        <FieldGroup label={`${s.acceptance_criteria} (${ac.length})`} icon={<CheckCircle size={12} />}>
          {ac.map((item, i) => (
            <div key={i} className="crit-row">
              <span className="crit-num">{i + 1}</span>
              <div className="field">
                <AutoTextarea
                  disabled={locked}
                  value={item}
                  onChange={e => updateAc(i, e.target.value)}
                  rows={1}
                  style={{ fontSize: "12.5px", color: "var(--fg-2)", lineHeight: 1.5 }}
                />
              </div>
              <button type="button" className="row-del" disabled={locked} onClick={() => removeAc(i)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {!locked && (
            <button type="button" className="add-pill" onClick={addAc}>
              <Plus size={11} /> {ts.add_item}
            </button>
          )}
        </FieldGroup>

        <div style={divider} />

        {/* Subtasks by category */}
        {(["frontend", "backend", "configuration"] as Cat[]).map(cat => {
          const tasks = subtasks[cat]
          if (tasks.length === 0 && locked) return null
          return (
            <FieldGroup key={cat} label={catLabels[cat]} icon={<Code size={12} />}>
              {tasks.map((sub, i) => (
                <div key={i} className="crit-row" style={{ alignItems: "stretch" }}>
                  <span className="crit-num" style={{ marginTop: 2 }}>{i + 1}</span>
                  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <div className="field">
                      <input
                        disabled={locked}
                        placeholder={ts.subtask_title_placeholder}
                        value={sub.title}
                        onChange={e => updateSubTitle(cat, i, e.target.value)}
                        style={{ fontSize: "12.5px", fontWeight: 500, color: "var(--fg)" }}
                      />
                    </div>
                    <div className="field">
                      <AutoTextarea
                        disabled={locked}
                        placeholder={ts.subtask_desc_placeholder}
                        value={sub.description}
                        onChange={e => updateSubDesc(cat, i, e.target.value)}
                        style={{ fontSize: "11.5px", color: "var(--muted)", lineHeight: 1.5 }}
                      />
                    </div>
                  </div>
                  <button type="button" className="row-del" disabled={locked} onClick={() => removeSub(cat, i)}>
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              {!locked && (
                <button type="button" className="add-pill" onClick={() => addSub(cat)}>
                  <Plus size={11} /> {ts.add_subtask}
                </button>
              )}
            </FieldGroup>
          )
        })}

        <div style={divider} />

        {/* Definition of Done */}
        <FieldGroup label={s.definition_of_done} icon={<ListChecks size={12} />}>
          {dod.map((item, i) => (
            <div key={i} className="crit-row">
              <span style={{
                width: "16px", height: "16px", borderRadius: "4px",
                border: "1.5px solid var(--border-strong)",
                marginTop: "5px", flexShrink: 0,
              }} />
              <div className="field">
                <AutoTextarea
                  disabled={locked}
                  value={item}
                  onChange={e => updateDod(i, e.target.value)}
                  rows={1}
                  style={{ fontSize: "12.5px", color: "var(--fg-2)", lineHeight: 1.5 }}
                />
              </div>
              <button type="button" className="row-del" disabled={locked} onClick={() => removeDod(i)}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {!locked && (
            <button type="button" className="add-pill" onClick={addDod}>
              <Plus size={11} /> {ts.add_item}
            </button>
          )}
        </FieldGroup>

        {/* Risk Notes */}
        {(riskNotes.length > 0 || !locked) && (
          <>
            <div style={divider} />
            <FieldGroup label={s.risk_notes} icon={<AlertTriangle size={12} style={{ color: "var(--warn-fg)" }} />}>
              {riskNotes.map((note, i) => (
                <div key={i} className="crit-row">
                  <span style={{
                    width: "8px", height: "8px", borderRadius: "50%", background: "var(--warn-fg)",
                    marginTop: "8px", flexShrink: 0, marginLeft: "7px",
                  }} />
                  <div className="field">
                    <AutoTextarea
                      disabled={locked}
                      value={note}
                      onChange={e => updateRisk(i, e.target.value)}
                      rows={1}
                      style={{ fontSize: "12.5px", color: "var(--fg-2)", lineHeight: 1.5 }}
                    />
                  </div>
                  <button type="button" className="row-del" disabled={locked} onClick={() => removeRisk(i)}>
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              {!locked && (
                <button type="button" className="add-pill" onClick={addRisk}>
                  <Plus size={11} /> {ts.add_item}
                </button>
              )}
            </FieldGroup>
          </>
        )}

        {/* Sticky save bar — appears when there are pending changes */}
        {isDirty && !locked && (
          <div style={{
            position: "sticky", bottom: 8, marginTop: 4,
            padding: "8px 12px",
            background: "color-mix(in oklch, var(--surface) 70%, transparent)",
            backdropFilter: "blur(8px)",
            border: "1px solid var(--border)",
            color: "var(--fg)",
            borderRadius: "10px", display: "flex",
            alignItems: "center", justifyContent: "space-between", gap: 12,
            boxShadow: "0 4px 16px oklch(0.2 0.02 260 / 0.10)",
          }}>
            <span style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: 8 }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%", background: "var(--warn-fg)", display: "inline-block",
              }} />
              {ts.unsaved}
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                type="button"
                onClick={handleDiscard}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  color: "var(--fg-2)", padding: "5px 12px", borderRadius: "6px",
                  fontSize: "12px", cursor: "pointer",
                }}
              >
                {ts.discard}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                style={{
                  background: "var(--accent)", color: "var(--accent-fg)",
                  border: "none", padding: "5px 14px", borderRadius: "6px",
                  fontSize: "12px", fontWeight: 600,
                  cursor: saving ? "not-allowed" : "pointer",
                  fontFamily: "var(--font-display)",
                  display: "flex", alignItems: "center", gap: 6,
                }}
              >
                {saving && <Loader2 size={12} className="animate-spin" />}
                {saving ? t.connections.actions.saving : ts.save_changes}
              </button>
            </div>
          </div>
        )}
        </>}
      </div>
    </>
  )
}
