import type { Config } from "tailwindcss"
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        fg: "var(--fg)",
        "fg-2": "var(--fg-2)",
        muted: "var(--muted)",
        "muted-2": "var(--muted-2)",
        accent: {
          DEFAULT: "var(--accent)",
          strong: "var(--accent-strong)",
          soft: "var(--accent-soft)",
          fg: "var(--accent-fg)",
        },
        ok: { bg: "var(--ok-bg)", fg: "var(--ok-fg)" },
        warn: { bg: "var(--warn-bg)", fg: "var(--warn-fg)" },
        err: { bg: "var(--err-bg)", fg: "var(--err-fg)" },
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        lg: "var(--radius-lg)",
      },
    },
  },
}
export default config
