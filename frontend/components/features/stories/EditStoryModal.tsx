"use client"

import { useState } from "react"
import { X, Loader2, Plus, Trash2 } from "lucide-react"
import { updateStory, type StoryDetailResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface EditStoryModalProps {
  story: StoryDetailResponse
  isOpen: boolean
  onClose: () => void
  onSaved: (updated: StoryDetailResponse) => void
}

export function EditStoryModal({ story, isOpen, onClose, onSaved }: EditStoryModalProps) {
  const { t } = useLanguage()
  const s = t.stories

  const [title, setTitle] = useState(story.title)
  const [description, setDescription] = useState(story.story_description)
  const [ac, setAc] = useState<string[]>([...story.acceptance_criteria])
  const [subtasks, setSubtasks] = useState<typeof story.subtasks>({
    frontend: story.subtasks.frontend.map(st => ({ ...st })),
    backend: story.subtasks.backend.map(st => ({ ...st })),
    configuration: story.subtasks.configuration.map(st => ({ ...st })),
  })
  const [dod, setDod] = useState<string[]>([...story.definition_of_done])
  const [riskNotes, setRiskNotes] = useState<string[]>([...story.risk_notes])
  const [storyPoints, setStoryPoints] = useState(story.story_points)
  const [riskLevel, setRiskLevel] = useState(story.risk_level)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onClose()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const updated = await updateStory(story.story_id, {
        source_connection_id: story.source_connection_id,
        title,
        story_description: description,
        acceptance_criteria: ac,
        subtasks,
        definition_of_done: dod,
        risk_notes: riskNotes,
        story_points: storyPoints,
        risk_level: riskLevel,
      })
      onSaved(updated)
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.toLowerCase().includes("locked")) {
        setError(s.locked_error)
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  const labelStyle: React.CSSProperties = {
    fontSize: "12px", fontWeight: 600, color: "var(--fg-2)",
    marginBottom: "4px", display: "block", textTransform: "uppercase", letterSpacing: "0.06em",
  }
  const inputStyle: React.CSSProperties = {
    width: "100%", boxSizing: "border-box", padding: "7px 10px",
    borderRadius: "var(--radius)", border: "1px solid var(--border)",
    background: "var(--surface-2)", color: "var(--fg)", fontSize: "13px",
    outline: "none",
  }
  const textareaStyle: React.CSSProperties = {
    ...inputStyle, minHeight: "70px", resize: "vertical", fontFamily: "inherit",
  }
  const rowStyle: React.CSSProperties = {
    display: "flex", gap: "6px", alignItems: "flex-start", marginBottom: "6px",
  }
  const iconBtnStyle: React.CSSProperties = {
    flexShrink: 0, padding: "4px", border: "none", background: "transparent",
    color: "var(--muted)", cursor: "pointer", borderRadius: "var(--radius)",
  }

  function renderStringList(
    label: string,
    items: string[],
    setItems: (v: string[]) => void,
  ) {
    return (
      <div>
        <label style={labelStyle}>{label}</label>
        {items.map((item, i) => (
          <div key={i} style={rowStyle}>
            <input
              style={{ ...inputStyle, flex: 1 }}
              value={item}
              onChange={e => {
                const next = [...items]; next[i] = e.target.value; setItems(next)
              }}
            />
            <button type="button" style={iconBtnStyle} onClick={() => {
              const next = items.filter((_, idx) => idx !== i); setItems(next)
            }}>
              <Trash2 size={13} />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => setItems([...items, ""])}
          style={{
            display: "flex", alignItems: "center", gap: "4px",
            padding: "4px 8px", border: "1px dashed var(--border)",
            borderRadius: "var(--radius)", background: "transparent",
            color: "var(--muted)", fontSize: "12px", cursor: "pointer",
          }}
        >
          <Plus size={11} /> {s.add_item}
        </button>
      </div>
    )
  }

  function renderSubtaskCategory(
    cat: "frontend" | "backend" | "configuration",
    label: string,
  ) {
    const tasks = subtasks[cat]
    return (
      <div>
        <label style={labelStyle}>{label}</label>
        {tasks.map((task, i) => (
          <div key={i} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "8px", marginBottom: "6px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "11px", color: "var(--muted)", fontWeight: 600 }}>{s.subtask} {i + 1}</span>
              <button type="button" style={iconBtnStyle} onClick={() => {
                setSubtasks(prev => ({ ...prev, [cat]: prev[cat].filter((_, idx) => idx !== i) }))
              }}>
                <Trash2 size={12} />
              </button>
            </div>
            <input
              style={{ ...inputStyle, marginBottom: "4px" }}
              placeholder={s.subtask_title_placeholder}
              value={task.title}
              onChange={e => {
                setSubtasks(prev => {
                  const updated = [...prev[cat]]
                  updated[i] = { ...updated[i], title: e.target.value }
                  return { ...prev, [cat]: updated }
                })
              }}
            />
            <textarea
              style={textareaStyle}
              placeholder={s.subtask_desc_placeholder}
              value={task.description}
              onChange={e => {
                setSubtasks(prev => {
                  const updated = [...prev[cat]]
                  updated[i] = { ...updated[i], description: e.target.value }
                  return { ...prev, [cat]: updated }
                })
              }}
            />
          </div>
        ))}
        <button
          type="button"
          onClick={() => setSubtasks(prev => ({
            ...prev,
            [cat]: [...prev[cat], { title: "", description: "" }],
          }))}
          style={{
            display: "flex", alignItems: "center", gap: "4px",
            padding: "4px 8px", border: "1px dashed var(--border)",
            borderRadius: "var(--radius)", background: "transparent",
            color: "var(--muted)", fontSize: "12px", cursor: "pointer",
          }}
        >
          <Plus size={11} /> {s.add_subtask}
        </button>
      </div>
    )
  }

  return (
    <div
      onClick={handleBackdropClick}
      style={{
        position: "fixed", inset: 0, zIndex: 50,
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        background: "rgba(0,0,0,0.45)", overflowY: "auto", padding: "32px 16px",
      }}
    >
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        width: "100%", maxWidth: "600px",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 18px", borderBottom: "1px solid var(--border)",
        }}>
          <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", margin: 0 }}>
            {s.edit_title}
          </h2>
          <button type="button" onClick={onClose} style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: "28px", height: "28px", borderRadius: "var(--radius)",
            border: "none", background: "transparent", color: "var(--muted)", cursor: "pointer",
          }}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "18px", display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Title */}
          <div>
            <label style={labelStyle}>{s.field_title}</label>
            <input style={inputStyle} value={title} onChange={e => setTitle(e.target.value)} required />
          </div>

          {/* Description */}
          <div>
            <label style={labelStyle}>{s.field_description}</label>
            <textarea style={textareaStyle} value={description} onChange={e => setDescription(e.target.value)} required />
          </div>

          {/* Acceptance Criteria */}
          {renderStringList(s.field_ac, ac, setAc)}

          {/* Subtasks */}
          {renderSubtaskCategory("frontend", s.subtasks_frontend)}
          {renderSubtaskCategory("backend", s.subtasks_backend)}
          {renderSubtaskCategory("configuration", s.subtasks_configuration)}

          {/* Definition of Done */}
          {renderStringList(s.field_dod, dod, setDod)}

          {/* Risk Notes */}
          {renderStringList(s.field_risk_notes, riskNotes, setRiskNotes)}

          {/* Story Points + Risk Level */}
          <div style={{ display: "flex", gap: "12px" }}>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>{s.field_story_points}</label>
              <input
                type="number" min={1} max={100} style={inputStyle}
                value={storyPoints}
                onChange={e => setStoryPoints(Number(e.target.value))}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={labelStyle}>{s.field_risk_level}</label>
              <select
                style={{ ...inputStyle, appearance: "auto" }}
                value={riskLevel}
                onChange={e => setRiskLevel(e.target.value)}
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
              </select>
            </div>
          </div>

          {error && (
            <div style={{
              padding: "8px 10px", borderRadius: "var(--radius)",
              background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px",
            }}>
              {error}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
            <button type="button" onClick={onClose} disabled={loading} style={{
              padding: "6px 14px", borderRadius: "var(--radius)",
              border: "1px solid var(--border)", background: "var(--surface-2)",
              color: "var(--fg-2)", fontSize: "12.5px",
              cursor: loading ? "not-allowed" : "pointer",
            }}>
              {t.connections.actions.cancel}
            </button>
            <button type="submit" disabled={loading} style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "6px 14px", borderRadius: "var(--radius)",
              border: "none",
              background: loading ? "var(--surface-3)" : "var(--accent)",
              color: loading ? "var(--muted)" : "var(--accent-fg)",
              fontSize: "12.5px", fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
            }}>
              {loading && <Loader2 size={13} className="animate-spin" />}
              {loading ? t.connections.actions.saving : t.connections.actions.save}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
