import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionsByEmail } from "@/lib/api";
import { SubscriptionList } from "@/components/subscription-list";
import { SubscribeForm } from "@/components/subscribe-form";

// 서버 컴포넌트 — 서버에서 인증 확인 + 구독 목록 fetch (waterfall 없음)
export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/auth/login");

  const subscriptions = await getSubscriptionsByEmail(user.email!).catch(() => []);

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold font-serif text-indigo-700">NEWS READER</h1>
            <p className="text-xs text-slate-400">{user.email}</p>
          </div>
          <form action="/auth/logout" method="POST">
            <button type="submit" className="text-sm text-slate-500 hover:text-slate-800 transition">
              로그아웃
            </button>
          </form>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-6 py-8 space-y-10">
        {/* 구독 신청 */}
        <section>
          <h2 className="text-base font-semibold text-slate-800 mb-4">새 구독 추가</h2>
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <SubscribeForm />
          </div>
        </section>

        {/* 내 구독 목록 */}
        <section>
          <h2 className="text-base font-semibold text-slate-800 mb-4">
            내 구독
            <span className="ml-2 text-xs font-normal text-slate-400">{subscriptions.length}개</span>
          </h2>
          <SubscriptionList initialSubscriptions={subscriptions} />
        </section>
      </div>
    </main>
  );
}
