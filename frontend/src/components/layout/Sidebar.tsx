"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Globe,
  Mail,
  GitBranch,
  ListOrdered,
  ScrollText,
  Settings,
  LogOut,
  Zap,
} from "lucide-react";
import { logout } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/sites", label: "Sites WordPress", icon: Globe },
  { href: "/dashboard/accounts", label: "Contas de Email", icon: Mail },
  { href: "/dashboard/rules", label: "Regras", icon: GitBranch },
  { href: "/dashboard/queue", label: "Fila", icon: ListOrdered },
  { href: "/dashboard/logs", label: "Logs", icon: ScrollText },
  { href: "/dashboard/settings", label: "Configurações", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: 260,
      height: "100vh",
      background: "var(--bg-secondary)",
      borderRight: "1px solid var(--border-primary)",
      display: "flex",
      flexDirection: "column",
      zIndex: 40,
    }}>
      {/* Logo */}
      <div style={{
        padding: "24px 20px",
        borderBottom: "1px solid var(--border-primary)",
      }}>
        <Link href="/dashboard" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: "var(--radius-md)",
            background: "linear-gradient(135deg, var(--brand-600), var(--brand-400))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 12px rgba(51, 129, 255, 0.3)",
          }}>
            <Zap size={18} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>
              Email Extractor
            </h1>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Auto Publisher</span>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "12px 10px", overflowY: "auto" }}>
        {navItems.map((item) => {
          const isActive = pathname === item.href || 
            (item.href !== "/dashboard" && pathname?.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                marginBottom: 2,
                borderRadius: "var(--radius-md)",
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive ? 500 : 400,
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                background: isActive ? "rgba(51, 129, 255, 0.1)" : "transparent",
                borderLeft: isActive ? "2px solid var(--brand-500)" : "2px solid transparent",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "var(--bg-tertiary)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }
              }}
            >
              <Icon size={18} style={{ opacity: isActive ? 1 : 0.6 }} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: "14px 10px",
        borderTop: "1px solid var(--border-primary)",
      }}>
        <button
          onClick={logout}
          className="btn btn-ghost"
          style={{ width: "100%", justifyContent: "flex-start", fontSize: 13 }}
        >
          <LogOut size={16} />
          Sair
        </button>
      </div>
    </aside>
  );
}
