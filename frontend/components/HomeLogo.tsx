"use client";
import { usePathname, useRouter } from "next/navigation";

export default function HomeLogo() {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname !== "/") return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 91,
        left: "max(20px, calc((100vw - 1040px) / 2 + 20px))",
        width: 210,
        padding: "20px 16px 14px",
        display: "flex",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <img
        src="/logo/global-in-logo.svg"
        alt="Global-In"
        style={{ width: "90%", height: "auto", cursor: "pointer" }}
        onClick={() => router.push("/")}
      />
    </div>
  );
}
