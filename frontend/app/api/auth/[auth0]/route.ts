import { handleAuth } from "@auth0/nextjs-auth0"

const auth0Handler = handleAuth()

export async function GET(
  request: Request,
  context: { params: Promise<{ auth0: string | string[] }> },
) {
  const params = await context.params
  return auth0Handler(request, { params })
}
