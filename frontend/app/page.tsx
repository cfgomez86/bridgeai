import { auth, currentUser } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export default async function Home() {
  const { userId, orgSlug, orgId, getToken } = await auth()

  if (!userId) redirect("/sign-in")
  if (!orgSlug || !orgId) redirect("/select-org")

  try {
    const [token, user] = await Promise.all([getToken(), currentUser()])
    await fetch(`${API_URL}/api/v1/auth/provision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        tenant_name: orgSlug,
        tenant_slug: orgSlug,
        clerk_org_id: orgId,
        user_email: user?.emailAddresses[0]?.emailAddress ?? "",
        user_name: user?.fullName ?? null,
      }),
    })
  } catch {
    // Provisioning failed — workspace will show 403 until resolved
  }

  redirect(`/app/${orgSlug}/workflow`)
}
