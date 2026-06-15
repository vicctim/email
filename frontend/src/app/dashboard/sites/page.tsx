"use client";

import { useEffect, useState } from "react";
import { Plus, Globe, Trash2, Pencil, Wifi, Loader2 } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import Modal from "@/components/ui/Modal";
import { sitesApi } from "@/lib/api";

interface Site {
  id: number;
  name: string;
  base_url: string;
  username: string;
  is_active: boolean;
  last_status: string | null;
  last_checked_at: string | null;
  created_at: string;
  has_plugin_token: boolean;
}

export default function SitesPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Site | null>(null);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { ok: boolean; msg: string }>>({});

  const [form, setForm] = useState({
    name: "",
    base_url: "",
    username: "",
    app_password: "",
    plugin_token: "",
    default_status: "publish",
  });

  useEffect(() => {
    loadSites();
  }, []);

  async function loadSites() {
    try {
      const data = await sitesApi.list();
      setSites(Array.isArray(data) ? data : []);
    } catch {
      setSites([]);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({ name: "", base_url: "", username: "", app_password: "", plugin_token: "", default_status: "publish" });
    setModalOpen(true);
  }

  function openEdit(site: Site) {
    setEditing(site);
    setForm({
      name: site.name,
      base_url: site.base_url,
      username: site.username,
      app_password: "",
      plugin_token: "",
      default_status: "publish",
    });
    setModalOpen(true);
  }

  async function handleSubmit() {
    try {
      if (editing) {
        await sitesApi.update(editing.id, form);
      } else {
        await sitesApi.create(form);
      }
      setModalOpen(false);
      loadSites();
    } catch (err) {
      console.error("Erro ao salvar site:", err);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Remover este site?")) return;
    await sitesApi.delete(id);
    loadSites();
  }

  async function handleTest(id: number) {
    setTesting(id);
    try {
      const result = await sitesApi.test(id);
      setTestResult((prev) => ({ ...prev, [id]: { ok: true, msg: result.message || "Conexão OK" } }));
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Falha na conexão";
      setTestResult((prev) => ({ ...prev, [id]: { ok: false, msg } }));
    } finally {
      setTesting(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Sites WordPress"
        description="Gerencie os sites conectados para publicação automática"
        actions={
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> Novo Site
          </button>
        }
      />

      {loading ? (
        <div style={{ display: "grid", gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: 72, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : sites.length === 0 ? (
        <div className="glass-card empty-state">
          <Globe size={40} />
          <p>Nenhum site cadastrado. Adicione seu primeiro site WordPress.</p>
          <button className="btn btn-primary" onClick={openCreate} style={{ marginTop: 16 }}>
            <Plus size={16} /> Novo Site
          </button>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>URL</th>
                <th>Status</th>
                <th>Conexão</th>
                <th style={{ width: 140 }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id}>
                  <td style={{ fontWeight: 500 }}>{site.name}</td>
                  <td>
                    <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{site.base_url}</span>
                  </td>
                  <td>
                    <span className={`badge ${site.is_active ? "badge-success" : "badge-neutral"}`}>
                      {site.is_active ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td>
                    {testResult[site.id] ? (
                      <span className={`badge ${testResult[site.id].ok ? "badge-success" : "badge-error"}`}>
                        {testResult[site.id].msg}
                      </span>
                    ) : (
                      <span className={`badge ${site.has_plugin_token ? "badge-neutral" : "badge-warning"}`}>
                        {site.has_plugin_token ? site.last_status || "Não testado" : "Token pendente"}
                      </span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={() => handleTest(site.id)}
                        disabled={testing === site.id}
                        title="Testar conexão"
                      >
                        {testing === site.id ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Wifi size={14} />}
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(site)} title="Editar">
                        <Pencil size={14} />
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => handleDelete(site.id)} title="Remover" style={{ color: "var(--error-500)" }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal Form */}
      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Editar Site" : "Novo Site"}>
        <div className="form-group">
          <label className="input-label">Nome do site</label>
          <input className="input" placeholder="ExpoQueijo Brasil" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="input-label">URL base do WordPress</label>
          <input className="input" placeholder="https://expoqueijobrasil.com.br" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="input-label">Usuário WordPress</label>
          <input className="input" placeholder="admin" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="input-label">Application Password do WordPress</label>
          <input className="input" type="password" placeholder={editing ? "••••••• (deixe vazio para manter)" : "xxxx xxxx xxxx xxxx"} value={form.app_password} onChange={(e) => setForm({ ...form, app_password: e.target.value })} />
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Usado para criar posts e enviar imagens pela API nativa do WordPress
          </p>
        </div>
        <div className="form-group">
          <label className="input-label">Token do Plugin</label>
          <input
            className="input"
            type="password"
            placeholder={editing ? "••••••• (deixe vazio para manter)" : "Token em Configurações → Email Extractor"}
            value={form.plugin_token}
            onChange={(e) => setForm({ ...form, plugin_token: e.target.value })}
          />
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Token da instalação do plugin neste site, usado para testar conexão e listar categorias
          </p>
        </div>
        <div className="form-group">
          <label className="input-label">Status padrão do post</label>
          <select className="input" value={form.default_status} onChange={(e) => setForm({ ...form, default_status: e.target.value })}>
            <option value="publish">Publicado</option>
            <option value="draft">Rascunho</option>
            <option value="pending">Pendente</option>
          </select>
        </div>
        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={handleSubmit}>
            {editing ? "Salvar" : "Criar Site"}
          </button>
        </div>
      </Modal>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
