import { redirect } from "next/navigation"
import { auth0 } from "@/lib/auth0"
import { DashboardView } from "@/components/features/DashboardView"

const API_URL = process.env.API_URL ?? "http://localhost:8000"

export default async function Home() {
  const session = await auth0.getSession()
  if (!session) redirect("/login")

  let provisionOk = false
  for (let attempt = 0; attempt < 3 && !provisionOk; attempt++) {
    try {
      const { token } = await auth0.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/auth/provision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_email: session.user.email ?? "",
          user_name: session.user.name ?? null,
        }),
      })
      if (res.ok) provisionOk = true
    } catch {
      // retry
    }
  }

  return <DashboardView />
}
