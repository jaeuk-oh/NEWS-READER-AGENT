import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

// Supabase 이메일 인증 후 리다이렉트되는 콜백 Route Handler
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/dashboard`);
}
