import type { Metadata } from "next";
import { Noto_Serif_KR } from "next/font/google";
import "./globals.css";

const notoSerifKR = Noto_Serif_KR({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-serif",
  preload: false,
  display: "swap",
});

export const metadata: Metadata = {
  title: "News Reader Agent",
  description: "AI가 큐레이션하는 나만의 뉴스 브리핑",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/pretendard@latest/dist/web/static/pretendard.css"
        />
      </head>
      <body className={`${notoSerifKR.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
