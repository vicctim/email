"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/api";
import Sidebar from "@/components/layout/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{
        flex: 1,
        marginLeft: 260,
        padding: "28px 32px",
        minHeight: "100vh",
        background: `
          radial-gradient(ellipse at 70% 10%, rgba(51, 129, 255, 0.04) 0%, transparent 50%),
          var(--bg-primary)
        `,
      }}>
        <div className="animate-fade-in" style={{ maxWidth: 1200 }}>
          {children}
        </div>
      </main>
    </div>
  );
}
