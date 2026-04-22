"use client"

import { useAuth } from "@clerk/nextjs"
import { useEffect } from "react"
import { setTokenGetter } from "@/lib/api-client"

export function ClerkTokenSync() {
  const { getToken, isSignedIn } = useAuth()

  useEffect(() => {
    if (!isSignedIn) {
      setTokenGetter(null)
      return
    }
    setTokenGetter(getToken)
    return () => setTokenGetter(null)
  }, [isSignedIn, getToken])

  return null
}
