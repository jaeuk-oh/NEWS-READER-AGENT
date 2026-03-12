import { SubscribeForm } from "@/components/subscribe-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>News Reader Agent</CardTitle>
            <CardDescription>
              원하는 주제의 뉴스 브리핑을 매일 이메일로 받아보세요.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SubscribeForm />
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground">
          <Link href="/auth/login" className="hover:underline">
            로그인
          </Link>
          {" "}해서 내 구독을 관리하세요.
        </p>
      </div>
    </main>
  );
}
