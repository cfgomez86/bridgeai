import { redirect } from "next/navigation"
import { auth0 } from "@/lib/auth0"
import { FeedbackReview } from "@/components/features/feedback/FeedbackReview"

export default async function FeedbackPage() {
  const session = await auth0.getSession()
  if (!session) redirect("/login")

  return <FeedbackReview />
}
