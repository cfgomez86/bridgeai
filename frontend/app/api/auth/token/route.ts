import { getAccessToken } from "@auth0/nextjs-auth0"
import { NextResponse } from "next/server"

export async function GET() {
  try {
    const { accessToken } = await getAccessToken()
    return NextResponse.json({ accessToken: accessToken ?? null })
  } catch {
    return NextResponse.json({ accessToken: null })
  }
}
