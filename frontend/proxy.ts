import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"

const isProtected = createRouteMatcher([
  "/",
  "/app(.*)",
  "/select-org(.*)",
  "/workflow(.*)",
  "/indexing(.*)",
  "/connections(.*)",
  "/settings(.*)",
])

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req)) await auth.protect()
})

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
}
