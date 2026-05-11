"use client";

import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color: "brand" | "success" | "warning" | "error";
  trend?: string;
}

const colorMap = {
  brand: { bg: "rgba(51, 129, 255, 0.1)", icon: "var(--brand-500)", border: "rgba(51, 129, 255, 0.2)" },
  success: { bg: "rgba(34, 197, 94, 0.1)", icon: "var(--success-500)", border: "rgba(34, 197, 94, 0.2)" },
  warning: { bg: "rgba(245, 158, 11, 0.1)", icon: "var(--warning-500)", border: "rgba(245, 158, 11, 0.2)" },
  error: { bg: "rgba(239, 68, 68, 0.1)", icon: "var(--error-500)", border: "rgba(239, 68, 68, 0.2)" },
};

export default function StatCard({ label, value, icon: Icon, color, trend }: StatCardProps) {
  const c = colorMap[color];

  return (
    <div className="glass-card" style={{ padding: "20px 22px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 6 }}>{label}</p>
          <p style={{ fontSize: 28, fontWeight: 700, lineHeight: 1 }}>{value}</p>
          {trend && (
            <p style={{ fontSize: 12, color: c.icon, marginTop: 8 }}>{trend}</p>
          )}
        </div>
        <div style={{
          width: 44,
          height: 44,
          borderRadius: "var(--radius-md)",
          background: c.bg,
          border: `1px solid ${c.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}>
          <Icon size={20} color={c.icon} />
        </div>
      </div>
    </div>
  );
}
