import { getSession, getAccessToken } from "@auth0/nextjs-auth0"
import { redirect } from "next/navigation"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export default async function Home() {
  const session = await getSession()
  if (!session) redirect("/api/auth/login")

  try {
    const { accessToken } = await getAccessToken()
    await fetch(`${API_URL}/api/v1/auth/provision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        user_email: session.user.email ?? "",
        user_name: session.user.name ?? null,
      }),
    })
  } catch {
    // Provisioning failed — workspace will show 403 until resolved
  }

  redirect("/workflow")
}
