"use client"

import { useState, useEffect } from "react"
import { ThumbsUp, ThumbsDown, Loader2 } from "lucide-react"
import { getStoryFeedback, submitStoryFeedback, type FeedbackResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface StoryFeedbackProps {
  storyId: string
  onToast?: (msg: string, tone: "ok" | "err") => void
}

export function StoryFeedback({ storyId, onToast }: StoryFeedbackProps) {
  const [rating, setRating] = useState<"thumbs_up" | "thumbs_down" | null>(null)
  const [comment, setComment] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [initial, setInitial] = useState<FeedbackResponse | null>(null)
  const { t } = useLanguage()
  const s = t.stories.feedback

  useEffect(() => {
    getStoryFeedback(storyId)
      .then(fb => {
        if (fb) {
          setInitial(fb)
          setRating(fb.rating as "thumbs_up" | "thumbs_down")
          setComment(fb.comment || "")
          setSubmitted(true)
        }
      })
      .catch(() => {/* ignore */})
  }, [storyId])

  async function handleSubmit() {
    if (!rating) return
    setLoading(true)
    try {
      const result = await submitStoryFeedback(storyId, rating, comment || undefined)
      setInitial(result)
      setSubmitted(true)
      onToast?.(s.submitted_ok, "ok")
    } catch (err) {
      onToast?.(err instanceof Error ? err.message : s.submit_error, "err")
    } finally {
      setLoading(false)
    }
  }

  const btnBase: React.CSSProperties = {
    display: "flex", alignItems: "center", gap: "5px",
    padding: "5px 10px", borderRadius: "var(--radius)",
    border: "1px solid var(--border)", background: "var(--surface-2)",
    fontSize: "12px", cursor: "pointer", transition: "background 0.1s",
  }

  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: "var(--radius)",
      background: "var(--surface)", padding: "12px", marginTop: "8px",
    }}>
      <div style={{ fontSize: "10.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: "10px" }}>
        {s.title}
      </div>

      <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
        <button
          type="button"
          onClick={() => setRating("thumbs_up")}
          style={{
            ...btnBase,
            background: rating === "thumbs_up" ? "var(--ok-bg)" : "var(--surface-2)",
            color: rating === "thumbs_up" ? "var(--ok-fg)" : "var(--fg-2)",
            borderColor: rating === "thumbs_up" ? "var(--ok-fg)" : "var(--border)",
          }}
        >
          <ThumbsUp size={13} /> {s.thumbs_up}
        </button>
        <button
          type="button"
          onClick={() => setRating("thumbs_down")}
          style={{
            ...btnBase,
            background: rating === "thumbs_down" ? "var(--err-bg)" : "var(--surface-2)",
            color: rating === "thumbs_down" ? "var(--err-fg)" : "var(--fg-2)",
            borderColor: rating === "thumbs_down" ? "var(--err-fg)" : "var(--border)",
          }}
        >
          <ThumbsDown size={13} /> {s.thumbs_down}
        </button>
      </div>

      {rating && (
        <>
          <textarea
            placeholder={s.comment_placeholder}
            value={comment}
            onChange={e => setComment(e.target.value)}
            style={{
              width: "100%", boxSizing: "border-box", minHeight: "60px",
              padding: "7px 10px", borderRadius: "var(--radius)",
              border: "1px solid var(--border)", background: "var(--surface-2)",
              color: "var(--fg)", fontSize: "12.5px", resize: "vertical",
              fontFamily: "inherit", outline: "none", marginBottom: "8px",
            }}
          />
          <button
            type="button"
            disabled={loading}
            onClick={handleSubmit}
            style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "5px 12px", borderRadius: "var(--radius)",
              border: "none",
              background: loading ? "var(--surface-3)" : "var(--accent)",
              color: loading ? "var(--muted)" : "var(--accent-fg)",
              fontSize: "12px", fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading && <Loader2 size={12} className="animate-spin" />}
            {loading ? s.submitting : submitted ? s.update_btn : s.submit_btn}
          </button>
        </>
      )}
    </div>
  )
}
