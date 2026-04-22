import { SignIn } from "@clerk/nextjs"
import { BrandHeader } from "@/components/features/BrandHeader"

export default function SignInPage() {
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
      <SignIn fallbackRedirectUrl="/" />
    </div>
  )
}
