"use client";

import { useEffect, useState } from "react";
import { Save, Loader2, Download, Plug, Package } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import { settingsApi, pluginApi } from "@/lib/api";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [pluginVersion, setPluginVersion] = useState<string | null>(null);
  const [form, setForm] = useState({
    default_publish_delay: 10,
    polling_interval_seconds: 60,
    whatsapp_notify_number: "",
    evolution_instance: "emailext",
  });

  useEffect(() => {
    async function load() {
      try {
        const [data, pluginInfo] = await Promise.all([
          settingsApi.get(),
          pluginApi.info().catch(() => null),
        ]);
        setForm((prev) => ({ ...prev, ...data }));
        if (pluginInfo?.version) {
          setPluginVersion(pluginInfo.version);
        }
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

  async function handleDownloadPlugin() {
    setDownloading(true);
    try {
      await pluginApi.download();
    } catch (err) {
      console.error("Erro ao baixar plugin:", err);
    } finally {
      setDownloading(false);
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

      {/* ── Configurações gerais ── */}
      <div className="glass-card" style={{ padding: 24, maxWidth: 600 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18 }}>Publicação</h3>
        <div className="form-group">
          <label className="input-label">Delay padrão (minutos)</label>
          <input
            className="input"
            type="number"
            min={0}
            value={form.default_publish_delay}
            onChange={(e) => setForm({ ...form, default_publish_delay: Number(e.target.value) })}
          />
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Tempo de espera entre captura do email e publicação
          </p>
        </div>
        <div className="form-group">
          <label className="input-label">Intervalo de polling IMAP (segundos)</label>
          <input
            className="input"
            type="number"
            min={10}
            value={form.polling_interval_seconds}
            onChange={(e) => setForm({ ...form, polling_interval_seconds: Number(e.target.value) })}
          />
        </div>

        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 18, marginTop: 28 }}>WhatsApp (Evolution API)</h3>
        <div className="form-group">
          <label className="input-label">Número para notificações</label>
          <input
            className="input"
            placeholder="5534999999999"
            value={form.whatsapp_notify_number}
            onChange={(e) => setForm({ ...form, whatsapp_notify_number: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label className="input-label">Nome da instância</label>
          <input
            className="input"
            value={form.evolution_instance}
            onChange={(e) => setForm({ ...form, evolution_instance: e.target.value })}
          />
        </div>
      </div>

      {/* ── Plugin WordPress ── */}
      <div className="glass-card" style={{ padding: 24, maxWidth: 600, marginTop: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <Plug size={18} style={{ color: "var(--accent)" }} />
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Plugin WordPress</h3>
          {pluginVersion && (
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 10px",
              borderRadius: "var(--radius-full, 999px)",
              background: "rgba(99, 102, 241, 0.12)",
              color: "var(--brand-400)",
              border: "1px solid rgba(99, 102, 241, 0.2)",
            }}>
              v{pluginVersion}
            </span>
          )}
        </div>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>
          Baixe e instale o plugin <strong>Email Extractor Bridge</strong> no seu WordPress para que
          ele receba os posts automaticamente via API.
        </p>

        <button
          id="btn-download-plugin"
          className="btn btn-primary"
          onClick={handleDownloadPlugin}
          disabled={downloading}
          style={{ marginBottom: 24 }}
        >
          {downloading
            ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
            : <Download size={16} />}
          {downloading ? "Preparando..." : "Baixar email-extractor.zip"}
        </button>

        <div style={{
          background: "var(--surface-2, rgba(255,255,255,0.04))",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md, 8px)",
          padding: "16px 18px",
        }}>
          <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, color: "var(--text-secondary)" }}>
            Como instalar:
          </p>
          <ol style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.8, paddingLeft: 18, margin: 0 }}>
            <li>Acesse o painel do WordPress → <strong>Plugins → Adicionar novo</strong></li>
            <li>
              Clique em <strong>"Fazer upload do plugin"</strong> e selecione o arquivo{" "}
              <code style={{ background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 4 }}>
                email-extractor.zip
              </code>
            </li>
            <li>Clique em <strong>"Instalar agora"</strong> e depois em <strong>"Ativar"</strong></li>
            <li>
              Vá em <strong>Configurações → Email Extractor</strong> no WordPress e copie o{" "}
              <strong>Token de Autenticação</strong>
            </li>
            <li>Cadastre ou edite o site em <strong>Sites WordPress</strong> e cole o token no campo <strong>Token do Plugin</strong></li>
          </ol>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
