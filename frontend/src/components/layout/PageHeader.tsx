"use client";

import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div style={{
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      marginBottom: 28,
      gap: 16,
      flexWrap: "wrap",
    }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.3 }}>{title}</h1>
        {description && (
          <p style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 4 }}>
            {description}
          </p>
        )}
      </div>
      {actions && <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>{actions}</div>}
    </div>
  );
}
