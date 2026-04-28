"use client"

import { useState } from "react"
import { Trash2, Plus, CheckCircle, Code, ListChecks, FileText, AlertTriangle, Lock, Loader2 } from "lucide-react"
import { updateStory, type StoryDetailResponse, type Subtask } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface StoryCardProps {
  story: StoryDetailResponse
  onSaved: (updated: StoryDetailResponse) => void
  onToast: (msg: string, tone: "ok" | "err") => void
}

type Cat = "frontend" | "backend" | "configuration"

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

  function mark() { setIsDirty(true) }

  // AC
  function updateAc(i: number, v: string) { const n=[...ac]; n[i]=v; setAc(n); mark() }
  function removeAc(i: number) { setAc(ac.filter((_,j)=>j!==i)); mark() }
  function addAc() { setAc([...ac,""]); mark() }

  // DoD
  function updateDod(i: number, v: string) { const n=[...dod]; n[i]=v; setDod(n); mark() }
  function removeDod(i: number) { setDod(dod.filter((_,j)=>j!==i)); mark() }
  function addDod() { setDod([...dod,""]); mark() }

  // Risk notes
  function updateRisk(i: number, v: string) { const n=[...riskNotes]; n[i]=v; setRiskNotes(n); mark() }
  function removeRisk(i: number) { setRiskNotes(riskNotes.filter((_,j)=>j!==i)); mark() }
  function addRisk() { setRiskNotes([...riskNotes,""]); mark() }

  // Subtasks
  function updateSubTitle(cat: Cat, i: number, v: string) {
    setSubtasks(p => { const u=[...p[cat]]; u[i]={...u[i],title:v}; return {...p,[cat]:u} }); mark()
  }
  function updateSubDesc(cat: Cat, i: number, v: string) {
    setSubtasks(p => { const u=[...p[cat]]; u[i]={...u[i],description:v}; return {...p,[cat]:u} }); mark()
  }
  function removeSub(cat: Cat, i: number) {
    setSubtasks(p => ({...p,[cat]:p[cat].filter((_,j)=>j!==i)})); mark()
  }
  function addSub(cat: Cat) {
    setSubtasks(p => ({...p,[cat]:[...p[cat],{title:"",description:""}]})); mark()
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

  const sectionLabel: React.CSSProperties = {
    fontSize: "10.5px", fontWeight: 600, textTransform: "uppercase",
    letterSpacing: "0.07em", color: "var(--muted)",
  }
  const divider: React.CSSProperties = { height: "1px", background: "var(--border)", margin: "2px 0" }
  const numBadge: React.CSSProperties = {
    flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
    width: "18px", height: "18px", borderRadius: "3px",
    background: "var(--surface-3)", color: "var(--fg-2)",
    fontSize: "10px", fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: "3px",
  }

  const catLabels: Record<Cat, string> = {
    frontend: s.subtasks_frontend,
    backend: s.subtasks_backend,
    configuration: s.subtasks_configuration,
  }

  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)",
      padding: "20px 22px", display: "flex", flexDirection: "column", gap: "16px",
    }}>

      {/* Title */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
        <input
          className="editable-field"
          disabled={locked}
          style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", fontFamily: "var(--font-display)", flex: 1 }}
          value={title}
          onChange={e => { setTitle(e.target.value); mark() }}
        />
        {locked && (
          <span style={{
            display: "inline-flex", alignItems: "center", gap: "4px",
            padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 600,
            background: "var(--surface-3)", color: "var(--muted)", flexShrink: 0,
          }}>
            <Lock size={10} /> {ts.locked_badge}
          </span>
        )}
      </div>

      {/* Story points + risk level */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{
          display: "inline-flex", alignItems: "center", gap: "4px",
          padding: "1px 8px", borderRadius: "4px", fontSize: "11px",
          background: "var(--accent-soft)", color: "var(--accent-strong)",
          fontFamily: "var(--font-mono)", fontWeight: 600,
        }}>
          <input
            type="number" min={1} max={100} disabled={locked}
            style={{
              width: "32px", background: "transparent", border: "none", outline: "none",
              color: "inherit", fontFamily: "inherit", fontSize: "inherit",
              fontWeight: "inherit", padding: 0, textAlign: "right",
              cursor: locked ? "default" : "text",
            }}
            value={storyPoints}
            onChange={e => { setStoryPoints(Number(e.target.value)); mark() }}
          />
          <span>{storyPoints === 1 ? s.point : s.points}</span>
        </span>
        <select
          disabled={locked}
          value={riskLevel}
          onChange={e => { setRiskLevel(e.target.value); mark() }}
          style={{
            padding: "2px 6px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
            border: "1px solid transparent", background: "var(--surface-3)",
            cursor: locked ? "default" : "pointer", color: "var(--fg-2)",
            fontFamily: "var(--font-mono)",
          }}
        >
          <option value="LOW">LOW</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="HIGH">HIGH</option>
        </select>
      </div>

      <div style={divider} />

      {/* Description */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
          <FileText size={12} style={{ color: "var(--muted)" }} />
          <span style={sectionLabel}>{s.description_label}</span>
        </div>
        <textarea
          className="editable-field"
          disabled={locked}
          rows={3}
          style={{ fontSize: "12.5px", lineHeight: 1.65, color: "var(--fg-2)", resize: "vertical" }}
          value={description}
          onChange={e => { setDescription(e.target.value); mark() }}
        />
      </div>

      <div style={divider} />

      {/* Acceptance Criteria */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <CheckCircle size={12} style={{ color: "var(--muted)" }} />
          <span style={sectionLabel}>{s.acceptance_criteria}</span>
        </div>
        <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
          {ac.map((item, i) => (
            <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px" }}>
              <button type="button" className="delete-btn" disabled={locked} onClick={() => removeAc(i)} style={{ marginTop: "3px" }}>
                <Trash2 size={12} />
              </button>
              <span style={numBadge}>{i + 1}</span>
              <input
                className="editable-field"
                disabled={locked}
                style={{ flex: 1, fontSize: "12.5px", color: "var(--fg-2)" }}
                value={item}
                onChange={e => updateAc(i, e.target.value)}
              />
            </li>
          ))}
        </ol>
        {!locked && (
          <button type="button" className="add-item-btn" style={{ marginTop: "8px" }} onClick={addAc}>
            <Plus size={11} /> {ts.add_item}
          </button>
        )}
      </div>

      <div style={divider} />

      {/* Subtasks by category */}
      {(["frontend", "backend", "configuration"] as Cat[]).map(cat => {
        const tasks = subtasks[cat]
        if (tasks.length === 0 && locked) return null
        return (
          <div key={cat}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
              <Code size={12} style={{ color: "var(--muted)" }} />
              <span style={sectionLabel}>{catLabels[cat]}</span>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "8px" }}>
              {tasks.map((sub, i) => (
                <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px" }}>
                  <button type="button" className="delete-btn" disabled={locked} onClick={() => removeSub(cat, i)} style={{ marginTop: "3px" }}>
                    <Trash2 size={12} />
                  </button>
                  <span style={numBadge}>{i + 1}</span>
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "3px" }}>
                    <input
                      className="editable-field"
                      disabled={locked}
                      placeholder={ts.subtask_title_placeholder}
                      style={{ fontSize: "12.5px", fontWeight: 500, color: "var(--fg)" }}
                      value={sub.title}
                      onChange={e => updateSubTitle(cat, i, e.target.value)}
                    />
                    <textarea
                      className="editable-field"
                      disabled={locked}
                      rows={2}
                      placeholder={ts.subtask_desc_placeholder}
                      style={{ fontSize: "12px", color: "var(--muted)", resize: "vertical", lineHeight: 1.5 }}
                      value={sub.description}
                      onChange={e => updateSubDesc(cat, i, e.target.value)}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {!locked && (
              <button type="button" className="add-item-btn" style={{ marginTop: "8px" }} onClick={() => addSub(cat)}>
                <Plus size={11} /> {ts.add_subtask}
              </button>
            )}
          </div>
        )
      })}

      <div style={divider} />

      {/* Definition of Done */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <ListChecks size={12} style={{ color: "var(--muted)" }} />
          <span style={sectionLabel}>{s.definition_of_done}</span>
        </div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
          {dod.map((item, i) => (
            <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px" }}>
              <button type="button" className="delete-btn" disabled={locked} onClick={() => removeDod(i)} style={{ marginTop: "3px" }}>
                <Trash2 size={12} />
              </button>
              <span style={{ flexShrink: 0, marginTop: "4px", width: "14px", height: "14px", borderRadius: "3px", border: "1px solid var(--border)" }} />
              <input
                className="editable-field"
                disabled={locked}
                style={{ flex: 1, fontSize: "12.5px", color: "var(--fg-2)" }}
                value={item}
                onChange={e => updateDod(i, e.target.value)}
              />
            </li>
          ))}
        </ul>
        {!locked && (
          <button type="button" className="add-item-btn" style={{ marginTop: "8px" }} onClick={addDod}>
            <Plus size={11} /> {ts.add_item}
          </button>
        )}
      </div>

      {/* Risk Notes */}
      {(riskNotes.length > 0 || !locked) && (
        <>
          <div style={divider} />
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
              <AlertTriangle size={12} style={{ color: "var(--warn-fg)" }} />
              <span style={sectionLabel}>{s.risk_notes}</span>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
              {riskNotes.map((note, i) => (
                <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "6px" }}>
                  <button type="button" className="delete-btn" disabled={locked} onClick={() => removeRisk(i)} style={{ marginTop: "3px" }}>
                    <Trash2 size={12} />
                  </button>
                  <span style={{ flexShrink: 0, marginTop: "8px", width: "6px", height: "6px", borderRadius: "50%", background: "var(--warn-fg)" }} />
                  <input
                    className="editable-field"
                    disabled={locked}
                    style={{ flex: 1, fontSize: "12.5px", color: "var(--fg-2)" }}
                    value={note}
                    onChange={e => updateRisk(i, e.target.value)}
                  />
                </li>
              ))}
            </ul>
            {!locked && (
              <button type="button" className="add-item-btn" style={{ marginTop: "8px" }} onClick={addRisk}>
                <Plus size={11} /> {ts.add_item}
              </button>
            )}
          </div>
        </>
      )}

      {/* Save button — only when there are pending changes */}
      {isDirty && !locked && (
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
            padding: "9px 16px", borderRadius: "var(--radius)", border: "none",
            background: saving ? "var(--surface-3)" : "var(--accent)",
            color: saving ? "var(--muted)" : "var(--accent-fg)",
            fontSize: "13px", fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
            fontFamily: "var(--font-display)", marginTop: "4px",
          }}
        >
          {saving && <Loader2 size={13} className="animate-spin" />}
          {saving ? t.connections.actions.saving : ts.save_changes}
        </button>
      )}
    </div>
  )
}
