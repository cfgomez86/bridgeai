"use client"

import { useUser } from "@auth0/nextjs-auth0/client"
import { useEffect } from "react"
import { setTokenGetter } from "@/lib/api-client"

export function Auth0TokenSync() {
  const { user, isLoading } = useUser()

  useEffect(() => {
    if (isLoading) return
    if (!user) {
      setTokenGetter(null)
      return
    }
    setTokenGetter(async () => {
      const res = await fetch("/api/auth/token")
      const data = await res.json()
      return (data as { accessToken: string | null }).accessToken
    })
    return () => setTokenGetter(null)
  }, [user, isLoading])

  return null
}
