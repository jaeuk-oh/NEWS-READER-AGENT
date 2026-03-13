import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

// Supabase magic link 클릭 후 리다이렉트되는 콜백 Route Handler
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { data } = await supabase.auth.exchangeCodeForSession(code);

    // 신규 유저(관심사 미설정)면 프로필 설정 페이지로
    if (data.user && !data.user.user_metadata?.interests) {
      return NextResponse.redirect(`${origin}/auth/signup/complete`);
    }
  }

  return NextResponse.redirect(`${origin}/dashboard`);
}
