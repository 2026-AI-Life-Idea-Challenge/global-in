import type { Metadata } from "next";
import "./globals.css";
import HomeLogo from "@/components/HomeLogo";

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
      <head>
        <link rel="icon" href="/logo/favicon.ico" sizes="any" />
        <link rel="icon" href="/logo/favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/logo/apple-touch-icon.png" />
      </head>
      <body><HomeLogo />{children}</body>
    </html>
  );
}