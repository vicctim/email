"use client";

import { useEffect, useState } from "react";
import { Plus, Mail, Trash2, Pencil, Wifi, Loader2 } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import Modal from "@/components/ui/Modal";
import { accountsApi } from "@/lib/api";

interface Account {
  id: number;
  name: string;
  imap_host: string;
  imap_port: number;
  username: string;
  folder: string;
  polling_interval_seconds: number;
  is_active: boolean;
  created_at: string;
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, { ok: boolean; msg: string }>>({});

  const [form, setForm] = useState({
    name: "",
    imap_host: "imap.gmail.com",
    imap_port: 993,
    username: "",
    password: "",
    folder: "INBOX",
    polling_interval_seconds: 60,
  });

  useEffect(() => { loadAccounts(); }, []);

  async function loadAccounts() {
    try {
      const data = await accountsApi.list();
      setAccounts(Array.isArray(data) ? data : []);
    } catch {
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({ name: "", imap_host: "imap.gmail.com", imap_port: 993, username: "", password: "", folder: "INBOX", polling_interval_seconds: 60 });
    setModalOpen(true);
  }

  function openEdit(acc: Account) {
    setEditing(acc);
    setForm({
      name: acc.name,
      imap_host: acc.imap_host,
      imap_port: acc.imap_port,
      username: acc.username,
      password: "",
      folder: acc.folder,
      polling_interval_seconds: acc.polling_interval_seconds,
    });
    setModalOpen(true);
  }

  async function handleSubmit() {
    try {
      if (editing) {
        await accountsApi.update(editing.id, form);
      } else {
        await accountsApi.create(form);
      }
      setModalOpen(false);
      loadAccounts();
    } catch (err) {
      console.error("Erro ao salvar conta:", err);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Remover esta conta de email?")) return;
    await accountsApi.delete(id);
    loadAccounts();
  }

  async function handleTest(id: number) {
    setTesting(id);
    try {
      const result = await accountsApi.test(id);
      setTestResult((prev) => ({ ...prev, [id]: { ok: true, msg: result.message || "IMAP OK" } }));
    } catch {
      setTestResult((prev) => ({ ...prev, [id]: { ok: false, msg: "Falha na conexão" } }));
    } finally {
      setTesting(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Contas de Email"
        description="Configure as contas IMAP monitoradas pelo sistema"
        actions={
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> Nova Conta
          </button>
        }
      />

      {loading ? (
        <div style={{ display: "grid", gap: 12 }}>
          {[1, 2].map((i) => (
            <div key={i} className="skeleton" style={{ height: 72, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : accounts.length === 0 ? (
        <div className="glass-card empty-state">
          <Mail size={40} />
          <p>Nenhuma conta de email configurada. Adicione sua conta Gmail para monitorar.</p>
          <button className="btn btn-primary" onClick={openCreate} style={{ marginTop: 16 }}>
            <Plus size={16} /> Nova Conta
          </button>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Email</th>
                <th>Servidor</th>
                <th>Pasta</th>
                <th>Status</th>
                <th style={{ width: 140 }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acc) => (
                <tr key={acc.id}>
                  <td style={{ fontWeight: 500 }}>{acc.name}</td>
                  <td style={{ fontSize: 13, color: "var(--text-secondary)" }}>{acc.username}</td>
                  <td style={{ fontSize: 13, color: "var(--text-muted)" }}>{acc.imap_host}:{acc.imap_port}</td>
                  <td><span className="badge badge-neutral">{acc.folder}</span></td>
                  <td>
                    {testResult[acc.id] ? (
                      <span className={`badge ${testResult[acc.id].ok ? "badge-success" : "badge-error"}`}>
                        {testResult[acc.id].msg}
                      </span>
                    ) : (
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div className={`status-dot ${acc.is_active ? "online" : "offline"}`} />
                        <span style={{ fontSize: 13 }}>{acc.is_active ? "Monitorando" : "Inativo"}</span>
                      </div>
                    )}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => handleTest(acc.id)} disabled={testing === acc.id} title="Testar IMAP">
                        {testing === acc.id ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Wifi size={14} />}
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(acc)} title="Editar">
                        <Pencil size={14} />
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => handleDelete(acc.id)} title="Remover" style={{ color: "var(--error-500)" }}>
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Editar Conta" : "Nova Conta de Email"}>
        <div className="form-group">
          <label className="input-label">Nome</label>
          <input className="input" placeholder="Gmail Principal" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="input-label">Servidor IMAP</label>
            <input className="input" placeholder="imap.gmail.com" value={form.imap_host} onChange={(e) => setForm({ ...form, imap_host: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="input-label">Porta</label>
            <input className="input" type="number" value={form.imap_port} onChange={(e) => setForm({ ...form, imap_port: Number(e.target.value) })} />
          </div>
        </div>
        <div className="form-group">
          <label className="input-label">Email (login IMAP)</label>
          <input className="input" placeholder="seu-email@gmail.com" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="input-label">App Password</label>
          <input className="input" type="password" placeholder={editing ? "••••••• (deixe vazio para manter)" : "xxxx xxxx xxxx xxxx"} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Gmail: ative 2FA e gere em myaccount.google.com/apppasswords
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="input-label">Pasta</label>
            <input className="input" value={form.folder} onChange={(e) => setForm({ ...form, folder: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="input-label">Polling (segundos)</label>
            <input className="input" type="number" value={form.polling_interval_seconds} onChange={(e) => setForm({ ...form, polling_interval_seconds: Number(e.target.value) })} />
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={handleSubmit}>{editing ? "Salvar" : "Criar Conta"}</button>
        </div>
      </Modal>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
