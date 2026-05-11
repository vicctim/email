"use client";

import { useEffect, useState } from "react";
import { Settings, Save, Loader2, Eye, EyeOff, Copy } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import { settingsApi } from "@/lib/api";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({
    default_publish_delay: 10,
    polling_interval_seconds: 60,
    whatsapp_notify_number: "",
    evolution_instance: "emailext",
    api_secret_key: "",
  });

  useEffect(() => {
    async function load() {
      try {
        const data = await settingsApi.get();
        setForm((prev) => ({ ...prev, ...data }));
      } catch { /* defaults */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await settingsApi.update(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Erro ao salvar:", err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return (
    <div>
      <PageHeader title="Configurações" />
      <div className="skeleton" style={{ height: 300, borderRadius: "var(--radius-lg)" }} />
    </div>
  );

  return (
    <div>
      <PageHeader title="Configurações" description="Ajustes globais do sistema" actions={
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <Save size={16} />}
          {saved ? "Salvo ✓" : "Salvar"}
        </button>
      } />

      <div className="glass-card" style={{ padding: 24, maxWidth: 600 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18 }}>Publicação</h3>
        <div className="form-group">
          <label className="input-label">Delay padrão (minutos)</label>
          <input className="input" type="number" min={0} value={form.default_publish_delay} onChange={(e) => setForm({ ...form, default_publish_delay: Number(e.target.value) })} />
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>Tempo de espera entre captura do email e publicação</p>
        </div>
        <div className="form-group">
          <label className="input-label">Intervalo de polling IMAP (segundos)</label>
          <input className="input" type="number" min={10} value={form.polling_interval_seconds} onChange={(e) => setForm({ ...form, polling_interval_seconds: Number(e.target.value) })} />
        </div>

        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18, marginTop: 28 }}>WhatsApp (Evolution API)</h3>
        <div className="form-group">
          <label className="input-label">Número para notificações</label>
          <input className="input" placeholder="5534999999999" value={form.whatsapp_notify_number} onChange={(e) => setForm({ ...form, whatsapp_notify_number: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="input-label">Nome da instância</label>
          <input className="input" value={form.evolution_instance} onChange={(e) => setForm({ ...form, evolution_instance: e.target.value })} />
        </div>

        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18, marginTop: 28 }}>Segurança</h3>
        <div className="form-group">
          <label className="input-label">Chave Secreta da API</label>
          <div style={{ display: "flex", gap: 6 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <input
                className="input"
                type={showSecret ? "text" : "password"}
                value={form.api_secret_key}
                onChange={(e) => setForm({ ...form, api_secret_key: e.target.value })}
                placeholder="Gerada automaticamente"
                style={{ paddingRight: 40, fontFamily: "monospace", fontSize: 13 }}
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}
              >
                {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                navigator.clipboard.writeText(form.api_secret_key);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              style={{ flexShrink: 0 }}
            >
              <Copy size={14} />
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>Usada para autenticação entre o backend e os plugins WordPress</p>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
