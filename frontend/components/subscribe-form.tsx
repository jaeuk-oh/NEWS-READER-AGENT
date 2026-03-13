"use client";

import { useState } from "react";
import { createSubscription, createInstantBriefing } from "@/lib/api";

const LANGUAGES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh-CN", label: "中文" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
];

type Tab = "cron" | "instant";

interface Props {
  variant?: "default" | "dark";
}

export function SubscribeForm({ variant = "default" }: Props) {
  const [tab, setTab] = useState<Tab>("cron");

  const isDark = variant === "dark";

  return (
    <div className="space-y-5">
      {/* 탭 */}
      <div className={`flex rounded-xl p-1 text-sm font-semibold ${isDark ? "bg-indigo-800/60" : "bg-slate-100"}`}>
        {([
          { key: "cron", label: "정기 구독" },
          { key: "instant", label: "지금 받기" },
        ] as { key: Tab; label: string }[]).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`flex-1 py-2 rounded-lg transition ${
              tab === key
                ? isDark
                  ? "bg-indigo-600 text-white shadow"
                  : "bg-white text-indigo-700 shadow"
                : isDark
                ? "text-indigo-300 hover:text-white"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "cron" ? (
        <CronForm variant={variant} />
      ) : (
        <InstantForm variant={variant} />
      )}
    </div>
  );
}

/* ─── 정기 구독 폼 ─── */
function CronForm({ variant }: { variant: "default" | "dark" }) {
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("");
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [targetLang, setTargetLang] = useState("ko");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const isDark = variant === "dark";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await createSubscription({ email, topic, schedule_time: scheduleTime, target_lang: targetLang });
      setSuccess(true);
      setEmail(""); setTopic(""); setScheduleTime("09:00"); setTargetLang("ko");
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  if (success) return <SuccessMessage onReset={() => setSuccess(false)} isDark={isDark} />;

  const inputClass = getInputClass(isDark);
  const labelClass = getLabelClass(isDark);

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-left">
      <div>
        <label htmlFor="cron-email" className={labelClass}>이메일</label>
        <input
          id="cron-email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className={inputClass}
        />
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="cron-topic" className={labelClass}>주제 / 키워드</label>
          <input
            id="cron-topic"
            placeholder="예: AI, 반도체, 코스피"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
            maxLength={200}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="cron-time" className={labelClass}>발송 시각</label>
          <input
            id="cron-time"
            type="time"
            value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)}
            required
            className={inputClass}
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="cron-lang" className={labelClass}>언어</label>
          <select
            id="cron-lang"
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className={inputClass}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value} className="bg-white text-slate-900">{lang.label}</option>
            ))}
          </select>
        </div>
      </div>
      {error && <p role="alert" className={`text-sm ${isDark ? "text-red-300" : "text-red-500"}`}>{error}</p>}
      <SubmitButton loading={loading} label="구독 등록" isDark={isDark} />
    </form>
  );
}

/* ─── 일회성 즉시 발송 폼 ─── */
function InstantForm({ variant }: { variant: "default" | "dark" }) {
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("");
  const [targetLang, setTargetLang] = useState("ko");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const isDark = variant === "dark";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await createInstantBriefing({ email, topic, target_lang: targetLang });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className={`rounded-2xl border p-8 text-center space-y-3 ${isDark ? "border-indigo-700 bg-indigo-800/50" : ""}`}>
        <p className={`text-lg font-bold ${isDark ? "text-white" : ""}`}>요청 접수 완료!</p>
        <p className={`text-sm ${isDark ? "text-indigo-200" : "text-slate-500"}`}>
          AI 에이전트가 뉴스를 수집 중입니다.<br />
          완료되면 <span className={`font-semibold ${isDark ? "text-white" : "text-slate-800"}`}>{email}</span>으로 발송됩니다.
        </p>
        <button
          onClick={() => { setSuccess(false); setEmail(""); setTopic(""); }}
          className={`mt-2 text-sm font-semibold underline underline-offset-4 ${isDark ? "text-indigo-300 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}
        >
          다시 요청하기
        </button>
      </div>
    );
  }

  const inputClass = getInputClass(isDark);
  const labelClass = getLabelClass(isDark);

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-left">
      <div>
        <label htmlFor="instant-email" className={labelClass}>이메일</label>
        <input
          id="instant-email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="instant-topic" className={labelClass}>주제 / 키워드</label>
        <input
          id="instant-topic"
          placeholder="예: AI, 반도체, 코스피"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          required
          maxLength={200}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="instant-lang" className={labelClass}>언어</label>
        <select
          id="instant-lang"
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
          className={inputClass}
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.value} value={lang.value} className="bg-white text-slate-900">{lang.label}</option>
          ))}
        </select>
      </div>
      <p className={`text-xs ${isDark ? "text-indigo-300" : "text-slate-400"}`}>
        에이전트 파이프라인 실행 후 수 분 내 발송됩니다.
      </p>
      {error && <p role="alert" className={`text-sm ${isDark ? "text-red-300" : "text-red-500"}`}>{error}</p>}
      <SubmitButton loading={loading} label="지금 받기" isDark={isDark} />
    </form>
  );
}

/* ─── 공통 컴포넌트 ─── */
function SuccessMessage({ onReset, isDark }: { onReset: () => void; isDark: boolean }) {
  return (
    <div className={`rounded-2xl border p-8 text-center space-y-3 ${isDark ? "border-indigo-700 bg-indigo-800/50" : ""}`}>
      <p className={`text-lg font-bold ${isDark ? "text-white" : ""}`}>구독이 완료됐습니다!</p>
      <p className={`text-sm ${isDark ? "text-indigo-200" : "text-slate-500"}`}>
        설정한 시각에 뉴스 브리핑을 보내드립니다.
      </p>
      <button
        onClick={onReset}
        className={`mt-2 text-sm font-semibold underline underline-offset-4 ${isDark ? "text-indigo-300 hover:text-white" : "text-slate-600 hover:text-slate-900"}`}
      >
        또 추가하기
      </button>
    </div>
  );
}

function SubmitButton({ loading, label, isDark }: { loading: boolean; label: string; isDark: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading}
      aria-busy={loading}
      className={`w-full py-4 rounded-2xl font-bold text-sm transition active:scale-[0.98] ${
        isDark
          ? "bg-indigo-500 hover:bg-indigo-400 text-white disabled:opacity-60"
          : "bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60 shadow-lg shadow-indigo-200"
      }`}
    >
      {loading ? "처리 중..." : label}
    </button>
  );
}

function getInputClass(isDark: boolean) {
  return isDark
    ? "w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder:text-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm"
    : "w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm";
}

function getLabelClass(isDark: boolean) {
  return `block text-sm font-semibold mb-1 ${isDark ? "text-indigo-100" : "text-slate-700"}`;
}
