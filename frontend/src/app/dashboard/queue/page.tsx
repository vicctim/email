"use client";

import { useEffect, useState } from "react";
import { ListOrdered, Eye, XCircle, RotateCcw, Loader2 } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import Modal from "@/components/ui/Modal";
import { queueApi } from "@/lib/api";
import { formatDateTime } from "@/lib/time";

interface QueueItem {
  id: number;
  email_subject: string;
  email_from: string;
  parsed_title: string | null;
  status: string;
  scheduled_at: string | null;
  published_at: string | null;
  post_url: string | null;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
  wordpress_site?: { name: string };
}

const statusMap: Record<string, { label: string; badge: string }> = {
  pending: { label: "Pendente", badge: "badge-neutral" },
  scheduled: { label: "Agendado", badge: "badge-info" },
  processing: { label: "Processando", badge: "badge-warning" },
  published: { label: "Publicado", badge: "badge-success" },
  failed: { label: "Falhou", badge: "badge-error" },
  cancelled: { label: "Cancelado", badge: "badge-neutral" },
};

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewTitle, setPreviewTitle] = useState("");
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => { loadQueue(); }, [filter]);

  async function loadQueue() {
    setLoading(true);
    try {
      const params: Record<string, string> | undefined = filter !== "all" ? { status: filter } : undefined;
      const data = await queueApi.list(params);
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function handlePreview(item: QueueItem) {
    setPreviewTitle(item.parsed_title || item.email_subject);
    try {
      const data = await queueApi.preview(item.id);
      setPreviewHtml(data.content_html || "<p>Sem conteúdo</p>");
    } catch {
      setPreviewHtml("<p>Erro ao carregar preview</p>");
    }
    setPreviewOpen(true);
  }

  async function handleCancel(id: number) {
    if (!confirm("Cancelar esta publicação?")) return;
    setActionLoading(id);
    try {
      await queueApi.cancel(id);
      loadQueue();
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRetry(item: QueueItem) {
    if (item.status === "published") {
      const confirmed = confirm("Republicar este item no WordPress? Use esta ação quando o post foi apagado diretamente no WordPress.");
      if (!confirmed) return;
    }

    setActionLoading(item.id);
    try {
      await queueApi.retry(item.id);
      loadQueue();
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Fila de Publicação"
        description="Acompanhe o status de cada email capturado"
        actions={
          <div style={{ display: "flex", gap: 6 }}>
            {["all", "pending", "scheduled", "processing", "published", "failed", "cancelled"].map((f) => (
              <button
                key={f}
                className={`btn btn-sm ${filter === f ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "Todos" : statusMap[f]?.label || f}
              </button>
            ))}
          </div>
        }
      />

      {loading ? (
        <div style={{ display: "grid", gap: 12 }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 64, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="glass-card empty-state">
          <ListOrdered size={40} />
          <p>Nenhum item na fila{filter !== "all" ? ` com status "${statusMap[filter]?.label}"` : ""}.</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Título / Assunto</th>
                <th>Remetente</th>
                <th>Site</th>
                <th>Status</th>
                <th>Agendado</th>
                <th>Tentativas</th>
                <th style={{ width: 120 }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td style={{ maxWidth: 280 }}>
                    <span className="truncate" style={{ display: "block", fontWeight: 500 }}>
                      {item.parsed_title || item.email_subject}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{item.email_from}</td>
                  <td>
                    <span className="badge badge-info">{item.wordpress_site?.name || "—"}</span>
                  </td>
                  <td>
                    <span className={`badge ${statusMap[item.status]?.badge || "badge-neutral"}`}>
                      {statusMap[item.status]?.label || item.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: "var(--text-muted)" }}>
                    {formatDateTime(item.scheduled_at)}
                  </td>
                  <td style={{ fontSize: 13 }}>
                    {item.attempts}/{item.max_attempts}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => handlePreview(item)} title="Preview">
                        <Eye size={14} />
                      </button>
                      {(item.status === "pending" || item.status === "scheduled") && (
                        <button
                          className="btn btn-ghost btn-sm btn-icon"
                          onClick={() => handleCancel(item.id)}
                          disabled={actionLoading === item.id}
                          title="Cancelar"
                          style={{ color: "var(--error-500)" }}
                        >
                          {actionLoading === item.id ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <XCircle size={14} />}
                        </button>
                      )}
                      {(item.status === "failed" || item.status === "cancelled" || item.status === "published") && (
                        <button
                          className="btn btn-ghost btn-sm btn-icon"
                          onClick={() => handleRetry(item)}
                          disabled={actionLoading === item.id}
                          title={item.status === "published" ? "Republicar" : "Tentar novamente"}
                          style={{ color: "var(--warning-500)" }}
                        >
                          {actionLoading === item.id ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <RotateCcw size={14} />}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview Modal */}
      <Modal open={previewOpen} onClose={() => setPreviewOpen(false)} title={previewTitle} width={700}>
        <div
          style={{
            background: "var(--bg-tertiary)",
            borderRadius: "var(--radius-md)",
            padding: 20,
            maxHeight: 400,
            overflowY: "auto",
            fontSize: 14,
            lineHeight: 1.7,
            color: "var(--text-secondary)",
          }}
          dangerouslySetInnerHTML={{ __html: previewHtml }}
        />
      </Modal>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
