import { redirect } from "next/navigation"
import { auth0 } from "@/lib/auth0"
import { DashboardView } from "@/components/features/DashboardView"

const API_URL = process.env.API_URL ?? "http://localhost:8000"

export default async function Home() {
  const session = await auth0.getSession()
  if (!session) redirect("/login")

  try {
    const { token } = await auth0.getAccessToken()
    await fetch(`${API_URL}/api/v1/auth/provision`, {
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
  } catch {
    // Provisioning failed — workspace will show 403 until resolved
  }

  return <DashboardView />
}
