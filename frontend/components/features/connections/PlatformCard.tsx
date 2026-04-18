"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { savePlatformConfig, deletePlatformConfig, getOAuthAuthorizeUrl, type PlatformResponse } from "@/lib/api-client"
import { Settings, Plug, Trash2, CheckCircle2, AlertCircle, Loader2, Copy, Check } from "lucide-react"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

const PLATFORM_ICONS: Record<string, string> = {
  github: "GH",
  gitlab: "GL",
  azure_devops: "AZ",
}

interface PlatformCardProps {
  platform: PlatformResponse
  onUpdated: () => void
}

export function PlatformCard({ platform, onUpdated }: PlatformCardProps) {
  const [editing, setEditing] = useState(false)
  const [clientId, setClientId] = useState(platform.client_id ?? "")
  const [clientSecret, setClientSecret] = useState("")
  const [saving, setSaving] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const redirectUri = `${BASE}/api/v1/connections/oauth/callback/${platform.platform}`

  function handleCopy() {
    navigator.clipboard.writeText(redirectUri)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function handleSave() {
    if (!clientId.trim() || !clientSecret.trim()) return
    setSaving(true)
    setError(null)
    try {
      await savePlatformConfig(platform.platform, clientId.trim(), clientSecret.trim())
      setEditing(false)
      setClientSecret("")
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setSaving(true)
    setError(null)
    try {
      await deletePlatformConfig(platform.platform)
      setEditing(false)
      setClientId("")
      setClientSecret("")
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete")
    } finally {
      setSaving(false)
    }
  }

  async function handleConnect() {
    setConnecting(true)
    setError(null)
    try {
      const { url } = await getOAuthAuthorizeUrl(platform.platform)
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start OAuth")
      setConnecting(false)
    }
  }

  return (
    <Card className="border-slate-200">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-slate-800 text-white text-xs font-bold">
              {PLATFORM_ICONS[platform.platform] ?? "?"}
            </span>
            <span>{platform.label}</span>
          </div>
          {platform.configured ? (
            <Badge className="bg-green-50 text-green-700 border-green-200 gap-1">
              <CheckCircle2 className="h-3 w-3" /> Configured
            </Badge>
          ) : (
            <Badge variant="outline" className="text-slate-400 gap-1">
              <AlertCircle className="h-3 w-3" /> Not set up
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <p className="text-xs text-red-600">{error}</p>
        )}

        {editing ? (
          <div className="space-y-2">
            <Input
              placeholder="Client ID"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
            />
            <Input
              type="password"
              placeholder="Client Secret"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
            />
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 space-y-1.5">
              <p className="text-xs font-medium text-amber-800">
                Register this Redirect URI in your OAuth App:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-white border border-amber-200 rounded px-2 py-1 text-xs text-slate-700 break-all">
                  {redirectUri}
                </code>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex-shrink-0 p-1.5 rounded border border-amber-200 bg-white hover:bg-amber-50 transition-colors"
                  title="Copy"
                >
                  {copied
                    ? <Check className="h-3.5 w-3.5 text-green-600" />
                    : <Copy className="h-3.5 w-3.5 text-amber-600" />
                  }
                </button>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleSave}
                disabled={saving || !clientId.trim() || !clientSecret.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setEditing(false); setError(null) }}>
                Cancel
              </Button>
              {platform.configured && (
                <Button size="sm" variant="outline" onClick={handleDelete} disabled={saving} className="ml-auto text-red-500 hover:text-red-700">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditing(true)}
              className="gap-1.5"
            >
              <Settings className="h-3.5 w-3.5" />
              {platform.configured ? "Edit" : "Configure"}
            </Button>
            {platform.configured && (
              <Button
                size="sm"
                onClick={handleConnect}
                disabled={connecting}
                className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {connecting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Plug className="h-3.5 w-3.5" />
                )}
                Connect
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
