"use client";

import { useState } from "react";
import { createSubscription } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LANGUAGES = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "zh-CN", label: "中文" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
];

export function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("");
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [targetLang, setTargetLang] = useState("ko");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

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

  if (success) {
    return (
      <div className="rounded-lg border p-6 text-center space-y-2">
        <p className="text-lg font-medium">구독이 완료됐습니다!</p>
        <p className="text-sm text-muted-foreground">설정한 시각에 뉴스 브리핑을 보내드립니다.</p>
        <Button variant="outline" onClick={() => setSuccess(false)}>또 추가하기</Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <Label htmlFor="email">이메일</Label>
        <Input
          id="email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="topic">주제 / 키워드</Label>
        <Input
          id="topic"
          placeholder="예: AI, 반도체, 코스피"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          required
          maxLength={200}
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="schedule-time">발송 시각</Label>
        <Input
          id="schedule-time"
          type="time"
          value={scheduleTime}
          onChange={(e) => setScheduleTime(e.target.value)}
          required
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="target-lang">언어</Label>
        <Select value={targetLang} onValueChange={(v) => v && setTargetLang(v)}>
          <SelectTrigger id="target-lang">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LANGUAGES.map((lang) => (
              <SelectItem key={lang.value} value={lang.value}>
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">{error}</p>
      )}

      <Button type="submit" className="w-full" disabled={loading} aria-busy={loading}>
        {loading ? "구독 중..." : "구독하기"}
      </Button>
    </form>
  );
}
