import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionsByEmail } from "@/lib/api";
import { SubscriptionList } from "@/components/subscription-list";
import { Button } from "@/components/ui/button";
import Link from "next/link";

// 서버 컴포넌트 — 서버에서 인증 확인 + 구독 목록 fetch (waterfall 없음)
export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/auth/login");

  const subscriptions = await getSubscriptionsByEmail(user.email!).catch(() => []);

  return (
    <main className="min-h-screen p-4 max-w-lg mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">내 구독</h1>
          <p className="text-sm text-muted-foreground">{user.email}</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-3 h-8 text-sm font-medium hover:bg-accent"
          >
            + 추가
          </Link>
          <LogoutButton />
        </div>
      </div>

      <SubscriptionList initialSubscriptions={subscriptions} />
    </main>
  );
}

// 로그아웃 버튼
function LogoutButton() {
  return (
    <form action="/auth/logout" method="POST">
      <Button variant="ghost" size="sm" type="submit">로그아웃</Button>
    </form>
  );
}
