import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Global-In",
  description: "나에게 맞는 비자·체류 프로그램을 비교하고 준비하세요",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}