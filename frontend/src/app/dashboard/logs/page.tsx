"use client";

import { useEffect, useState } from "react";
import { ScrollText, ChevronDown, ChevronUp } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import { logsApi } from "@/lib/api";
import { formatDateTime } from "@/lib/time";

interface LogEntry {
  id: number;
  level: string;
  event: string;
  message: string;
  content_preview: string | null;
  error_detail: string | null;
  created_at: string;
}

const levelBadge: Record<string, string> = {
  info: "badge-info",
  warning: "badge-warning",
  error: "badge-error",
};

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => { loadLogs(); }, [filter]);

  async function loadLogs() {
    setLoading(true);
    try {
      const params: Record<string, string> | undefined = filter !== "all" ? { level: filter } : undefined;
      const data = await logsApi.list(params);
      setLogs(Array.isArray(data) ? data : []);
    } catch { setLogs([]); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <PageHeader
        title="Logs"
        description="Histórico de eventos do sistema"
        actions={
          <div style={{ display: "flex", gap: 6 }}>
            {["all", "info", "warning", "error"].map((f) => (
              <button key={f} className={`btn btn-sm ${filter === f ? "btn-primary" : "btn-secondary"}`} onClick={() => setFilter(f)}>
                {f === "all" ? "Todos" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        }
      />

      {loading ? (
        <div style={{ display: "grid", gap: 8 }}>
          {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 48, borderRadius: "var(--radius-md)" }} />)}
        </div>
      ) : logs.length === 0 ? (
        <div className="glass-card empty-state">
          <ScrollText size={40} />
          <p>Nenhum log registrado.</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {logs.map((log) => (
            <div key={log.id} className="glass-card" style={{ padding: 0, overflow: "hidden" }}>
              <button onClick={() => setExpanded(expanded === log.id ? null : log.id)} style={{ width: "100%", display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: "none", border: "none", cursor: "pointer", color: "var(--text-primary)", textAlign: "left", fontSize: 14 }}>
                <span className={`badge ${levelBadge[log.level] || "badge-neutral"}`} style={{ minWidth: 60, justifyContent: "center" }}>{log.level}</span>
                <span style={{ fontWeight: 500, flex: 1 }}>{log.event}</span>
                <span style={{ fontSize: 12, color: "var(--text-muted)", flexShrink: 0 }}>
                  {formatDateTime(log.created_at)}
                </span>
                {expanded === log.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {expanded === log.id && (
                <div style={{ padding: "0 16px 16px", borderTop: "1px solid var(--border-primary)", paddingTop: 14 }}>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>{log.message}</p>
                  {log.error_detail && (
                    <pre style={{ marginTop: 10, padding: 12, background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.15)", borderRadius: "var(--radius-sm)", fontSize: 12, color: "var(--error-500)", overflow: "auto", maxHeight: 200, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{log.error_detail}</pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
