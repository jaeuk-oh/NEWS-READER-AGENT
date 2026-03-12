"use client";

import { useState } from "react";
import { toggleSubscription, deleteSubscription, type Subscription } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface Props {
  initialSubscriptions: Subscription[];
}

export function SubscriptionList({ initialSubscriptions }: Props) {
  const [subscriptions, setSubscriptions] = useState(initialSubscriptions);

  async function handleToggle(id: string, current: boolean) {
    try {
      const updated = await toggleSubscription(id, !current);
      setSubscriptions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, is_active: updated.is_active } : s))
      );
    } catch {
      alert("상태 변경에 실패했습니다.");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("구독을 삭제할까요?")) return;
    try {
      await deleteSubscription(id);
      setSubscriptions((prev) => prev.filter((s) => s.id !== id));
    } catch {
      alert("삭제에 실패했습니다.");
    }
  }

  if (subscriptions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        구독 중인 주제가 없습니다.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {subscriptions.map((sub) => (
        <li key={sub.id}>
          <Card>
            <CardContent className="flex items-center justify-between gap-4 py-4">
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{sub.topic}</p>
                <p className="text-sm text-muted-foreground">
                  {sub.schedule_time} · {sub.target_lang.toUpperCase()}
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Badge variant={sub.is_active ? "default" : "secondary"}>
                  {sub.is_active ? "활성" : "정지"}
                </Badge>
                <Switch
                  checked={sub.is_active}
                  onCheckedChange={() => handleToggle(sub.id, sub.is_active)}
                  aria-label={`${sub.topic} 구독 ${sub.is_active ? "비활성화" : "활성화"}`}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(sub.id)}
                  aria-label={`${sub.topic} 구독 삭제`}
                >
                  삭제
                </Button>
              </div>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}
