import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"

export default async function TenantLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: Promise<{ tenant: string }>
}) {
  const { userId, orgSlug } = await auth()

  // Require authentication for all tenant routes
  if (!userId) {
    redirect("/sign-in")
  }

  const { tenant } = await params

  // If the user has an active org and it doesn't match the URL tenant, redirect
  // to the correct tenant. If orgSlug is null the user has no org membership;
  // they can only reach their own personal workspace (same slug as userId is
  // not valid here), so redirect them to sign-in to select an org.
  if (orgSlug && orgSlug !== tenant) {
    redirect(`/app/${orgSlug}/workflow`)
  }

  if (!orgSlug) {
    // Authenticated but no org selected — send back to sign-in so Clerk can
    // prompt org selection (or the app can handle onboarding).
    redirect("/sign-in")
  }

  return <>{children}</>
}
