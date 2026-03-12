import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

// 로그아웃 Route Handler
export async function POST(request: Request) {
  const supabase = await createClient();
  await supabase.auth.signOut();
  return NextResponse.redirect(new URL("/auth/login", request.url));
}
