"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { createSubscription } from "@/lib/api";
import type { User } from "@supabase/supabase-js";
import Link from "next/link";

const LANGUAGES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh-CN", label: "中文" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
];

interface Props {
  variant?: "default" | "dark";
}

export function SubscribeForm({ variant = "default" }: Props) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [topic, setTopic] = useState("");
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [targetLang, setTargetLang] = useState("ko");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const isDark = variant === "dark";

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => setUser(data.user ?? null));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!user?.email) return;
    setError("");
    setLoading(true);
    try {
      await createSubscription({ email: user.email, topic, schedule_time: scheduleTime, target_lang: targetLang });
      setSuccess(true);
      setTopic(""); setScheduleTime("09:00"); setTargetLang("ko");
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  // 로딩 중
  if (user === undefined) {
    return <div className={`h-48 rounded-2xl animate-pulse ${isDark ? "bg-indigo-800/50" : "bg-slate-100"}`} />;
  }

  // 비로그인
  if (!user) {
    return (
      <div className={`rounded-2xl p-8 text-center space-y-4 ${isDark ? "bg-indigo-800/50 border border-indigo-700" : "border border-slate-200"}`}>
        <p className={`font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>
          구독하려면 로그인이 필요합니다.
        </p>
        <div className="flex justify-center gap-3">
          <Link
            href="/auth/login"
            className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition ${
              isDark ? "bg-white/10 text-white hover:bg-white/20" : "border border-slate-200 hover:bg-slate-50"
            }`}
          >
            로그인
          </Link>
          <Link
            href="/auth/signup"
            className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-500 text-white hover:bg-indigo-400 transition"
          >
            회원가입
          </Link>
        </div>
      </div>
    );
  }

  // 구독 완료
  if (success) {
    return (
      <div className={`rounded-2xl border p-8 text-center space-y-3 ${isDark ? "border-indigo-700 bg-indigo-800/50" : ""}`}>
        <p className={`text-lg font-bold ${isDark ? "text-white" : ""}`}>구독이 완료됐습니다!</p>
        <p className={`text-sm ${isDark ? "text-indigo-200" : "text-muted-foreground"}`}>
          설정한 시각에 뉴스 브리핑을 보내드립니다.
        </p>
        <button
          onClick={() => setSuccess(false)}
          className={`mt-2 text-sm font-semibold underline underline-offset-4 ${isDark ? "text-indigo-300 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}
        >
          또 추가하기
        </button>
      </div>
    );
  }

  const inputClass = isDark
    ? "w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm"
    : "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm";

  const labelClass = `block text-sm font-semibold mb-1 text-left ${isDark ? "text-indigo-100" : "text-slate-700"}`;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-left">
      {/* 로그인된 이메일 표시 */}
      <div className={`px-4 py-2.5 rounded-xl text-sm ${isDark ? "bg-white/10 text-indigo-200" : "bg-slate-50 text-slate-500 border border-slate-200"}`}>
        {user.email}
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="topic" className={labelClass}>주제 / 키워드</label>
          <input
            id="topic"
            placeholder="예: AI, 반도체, 코스피"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
            maxLength={200}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="schedule-time" className={labelClass}>발송 시각</label>
          <input
            id="schedule-time"
            type="time"
            value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)}
            required
            className={inputClass}
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="target-lang" className={labelClass}>언어</label>
          <select
            id="target-lang"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className={inputClass}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>{lang.label}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <p role="alert" className={`text-sm ${isDark ? "text-red-300" : "text-red-500"}`}>{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        aria-busy={loading}
        className={`w-full py-4 rounded-2xl font-bold text-sm transition ${
          isDark
            ? "bg-indigo-500 hover:bg-indigo-400 text-white disabled:opacity-60"
            : "bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60"
        }`}
      >
        {loading ? "구독 중..." : "시작하기"}
      </button>
    </form>
  );
}
