import { redirect } from "next/navigation"
import { auth0 } from "@/lib/auth0"
import { CoherenceReview } from "@/components/features/feedback/CoherenceReview"

export default async function CoherencePage() {
  const session = await auth0.getSession()
  if (!session) redirect("/login")

  return <CoherenceReview />
}
