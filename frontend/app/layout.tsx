import type { Metadata } from "next"
import "./globals.css"
import { Sidebar } from "@/components/features/Sidebar"

export const metadata: Metadata = {
  title: "BridgeAI",
  description: "Requirement to ticket automation",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 overflow-y-auto md:ml-60">{children}</main>
        </div>
      </body>
    </html>
  )
}
