// Render 백엔드 API 호출 함수 모음

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Subscription {
  id: string;
  email: string;
  topic: string;
  schedule_time: string;
  target_lang: string;
  is_active: boolean;
  unsubscribe_token: string;
}

export interface SubscriptionCreate {
  email: string;
  topic: string;
  schedule_time: string;
  target_lang: string;
}

// 구독 생성
export async function createSubscription(data: SubscriptionCreate): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "구독 생성에 실패했습니다.");
  }
  return res.json();
}

// 이메일로 구독 목록 조회
export async function getSubscriptionsByEmail(email: string): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/subscriptions?email=${encodeURIComponent(email)}`);
  if (!res.ok) throw new Error("구독 목록 조회에 실패했습니다.");
  return res.json();
}

// 구독 활성화/비활성화 토글
export async function toggleSubscription(id: string, isActive: boolean): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) throw new Error("구독 상태 변경에 실패했습니다.");
  return res.json();
}

// 구독 삭제
export async function deleteSubscription(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/subscriptions/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("구독 삭제에 실패했습니다.");
}

export interface InstantRequest {
  email: string;
  topic: string;
  target_lang: string;
}

// 일회성 즉시 발송
export async function createInstantBriefing(data: InstantRequest): Promise<{ message: string }> {
  const res = await fetch(`${API_URL}/subscriptions/instant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "요청에 실패했습니다.");
  }
  return res.json();
}
