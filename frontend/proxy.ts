import { withMiddlewareAuthRequired } from "@auth0/nextjs-auth0/edge"

export default withMiddlewareAuthRequired()

export const config = {
  matcher: [
    "/",
    "/workflow/:path*",
    "/indexing/:path*",
    "/connections/:path*",
    "/settings/:path*",
  ],
}
