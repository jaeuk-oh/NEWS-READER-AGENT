"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const INTEREST_OPTIONS = [
  "AI / 테크", "경제 / 비즈니스", "정치 / 사회", "스타트업",
  "글로벌 뉴스", "환경 / 에너지", "문화 / 라이프", "반도체 / 제조",
];

export default function CompleteSignupPage() {
  const router = useRouter();
  const supabase = createClient();

  const [interests, setInterests] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleComplete() {
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.updateUser({
      data: { interests },
    });
    setLoading(false);
    if (error) setError(error.message);
    else router.push("/dashboard");
  }

  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8">
        <h1 className="text-2xl font-bold font-serif mb-1">관심사 설정</h1>
        <p className="text-slate-500 text-sm mb-6">어떤 뉴스를 받고 싶으신가요? 1개 이상 선택해주세요.</p>

        <div className="flex flex-wrap gap-2 mb-6">
          {INTEREST_OPTIONS.map((interest) => (
            <button
              key={interest}
              type="button"
              onClick={() =>
                setInterests((prev) =>
                  prev.includes(interest)
                    ? prev.filter((i) => i !== interest)
                    : [...prev, interest]
                )
              }
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition border ${
                interests.includes(interest)
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-slate-600 border-slate-200 hover:border-indigo-400"
              }`}
            >
              {interest}
            </button>
          ))}
        </div>

        {error && <p role="alert" className="text-sm text-red-500 mb-4">{error}</p>}

        <button
          onClick={handleComplete}
          disabled={interests.length === 0 || loading}
          className="w-full py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition"
        >
          {loading ? "저장 중..." : "시작하기"}
        </button>
      </div>
    </main>
  );
}
