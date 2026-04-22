import { SignUp } from "@clerk/nextjs"
import { BrandHeader } from "@/components/features/BrandHeader"

export default function SignUpPage() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--bg)",
      gap: "24px",
    }}>
      <BrandHeader />
      <SignUp fallbackRedirectUrl="/select-org" />
    </div>
  )
}
