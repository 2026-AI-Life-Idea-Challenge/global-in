"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function HomeLogo() {
  const pathname = usePathname();
  const router = useRouter();
  const [logoLeft, setLogoLeft] = useState(20);

  useEffect(() => {
    const update = () =>
      setLogoLeft(Math.max(20, (window.innerWidth - 1040) / 2 + 20));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  if (pathname !== "/") return null;

  return (
    <div
      style={{
        position: "absolute",
        top: 91,
        left: logoLeft,
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
