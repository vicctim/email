"use client";

import { useEffect, useState } from "react";
import { Plus, GitBranch, Trash2, Pencil } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import Modal from "@/components/ui/Modal";
import { rulesApi, sitesApi, accountsApi } from "@/lib/api";

interface Rule {
  id: number;
  name: string;
  active: boolean;
  sender_contains: string | null;
  sender_name_contains: string | null;
  subject_regex: string | null;
  delay_minutes: number;
  post_status: string;
  email_account_id: number;
  wordpress_site_id: number;
  email_account?: { name: string };
  wordpress_site?: { name: string };
}

interface SelectOption { id: number; name: string }

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [sites, setSites] = useState<SelectOption[]>([]);
  const [accounts, setAccounts] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [regexTest, setRegexTest] = useState("");

  const [form, setForm] = useState({
    name: "",
    email_account_id: 0,
    wordpress_site_id: 0,
    sender_contains: "",
    sender_name_contains: "",
    subject_regex: "",
    delay_minutes: 10,
    post_status: "publish",
    remove_signature: true,
    remove_footer: true,
    convert_bold_to_h3: true,
    extract_gallery: true,
  });

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [r, s, a] = await Promise.all([rulesApi.list(), sitesApi.list(), accountsApi.list()]);
      setRules(Array.isArray(r) ? r : []);
      setSites(Array.isArray(s) ? s : []);
      setAccounts(Array.isArray(a) ? a : []);
    } catch {
      setRules([]); setSites([]); setAccounts([]);
    } finally {
      setLoading(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({
      name: "", email_account_id: accounts[0]?.id || 0, wordpress_site_id: sites[0]?.id || 0,
      sender_contains: "", sender_name_contains: "", subject_regex: "",
      delay_minutes: 10, post_status: "publish",
      remove_signature: true, remove_footer: true, convert_bold_to_h3: true, extract_gallery: true,
    });
    setModalOpen(true);
  }

  function openEdit(rule: Rule) {
    setEditing(rule);
    setForm({
      name: rule.name,
      email_account_id: rule.email_account_id,
      wordpress_site_id: rule.wordpress_site_id,
      sender_contains: rule.sender_contains || "",
      sender_name_contains: rule.sender_name_contains || "",
      subject_regex: rule.subject_regex || "",
      delay_minutes: rule.delay_minutes,
      post_status: rule.post_status,
      remove_signature: true, remove_footer: true, convert_bold_to_h3: true, extract_gallery: true,
    });
    setModalOpen(true);
  }

  async function handleSubmit() {
    try {
      if (editing) {
        await rulesApi.update(editing.id, form);
      } else {
        await rulesApi.create(form);
      }
      setModalOpen(false);
      loadData();
    } catch (err) {
      console.error("Erro ao salvar regra:", err);
    }
  }

  async function handleToggle(id: number) {
    await rulesApi.toggle(id);
    loadData();
  }

  async function handleDelete(id: number) {
    if (!confirm("Remover esta regra?")) return;
    await rulesApi.delete(id);
    loadData();
  }

  return (
    <div>
      <PageHeader
        title="Regras de Matching"
        description="Configure quais emails serão capturados e para qual site serão publicados"
        actions={
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> Nova Regra
          </button>
        }
      />

      {loading ? (
        <div style={{ display: "grid", gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: 72, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      ) : rules.length === 0 ? (
        <div className="glass-card empty-state">
          <GitBranch size={40} />
          <p>Nenhuma regra configurada. Crie uma regra para começar a capturar emails.</p>
          <button className="btn btn-primary" onClick={openCreate} style={{ marginTop: 16 }}>
            <Plus size={16} /> Nova Regra
          </button>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Ativa</th>
                <th>Nome</th>
                <th>Remetente</th>
                <th>Assunto</th>
                <th>Site Destino</th>
                <th>Delay</th>
                <th style={{ width: 100 }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>
                    <button
                      className={`toggle ${rule.active ? "active" : ""}`}
                      onClick={() => handleToggle(rule.id)}
                    />
                  </td>
                  <td style={{ fontWeight: 500 }}>{rule.name}</td>
                  <td style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                    {rule.sender_contains || rule.sender_name_contains || "—"}
                  </td>
                  <td>
                    {rule.subject_regex ? (
                      <code style={{
                        fontSize: 12,
                        padding: "2px 8px",
                        background: "var(--bg-tertiary)",
                        borderRadius: "var(--radius-sm)",
                        color: "var(--brand-400)",
                      }}>
                        {rule.subject_regex}
                      </code>
                    ) : "—"}
                  </td>
                  <td>
                    <span className="badge badge-info">
                      {rule.wordpress_site?.name || `Site #${rule.wordpress_site_id}`}
                    </span>
                  </td>
                  <td style={{ fontSize: 13, color: "var(--text-muted)" }}>{rule.delay_minutes} min</td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => openEdit(rule)} title="Editar">
                        <Pencil size={14} />
                      </button>
                      <button className="btn btn-ghost btn-sm btn-icon" onClick={() => handleDelete(rule.id)} title="Remover" style={{ color: "var(--error-500)" }}>
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

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? "Editar Regra" : "Nova Regra"} width={620}>
        <div className="form-group">
          <label className="input-label">Nome da regra</label>
          <input className="input" placeholder="ExpoQueijo - Releases" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="input-label">Conta de Email</label>
            <select className="input" value={form.email_account_id} onChange={(e) => setForm({ ...form, email_account_id: Number(e.target.value) })}>
              <option value={0}>Selecione...</option>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="input-label">Site WordPress destino</label>
            <select className="input" value={form.wordpress_site_id} onChange={(e) => setForm({ ...form, wordpress_site_id: Number(e.target.value) })}>
              <option value={0}>Selecione...</option>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>

        <div style={{ background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)", padding: 16, marginBottom: 18 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>Filtros de Matching</p>
          <div className="form-group">
            <label className="input-label">Remetente contém</label>
            <input className="input" placeholder="comuniquese2.com.br" value={form.sender_contains} onChange={(e) => setForm({ ...form, sender_contains: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="input-label">Nome do remetente contém</label>
            <input className="input" placeholder="ExpoQueijo Brasil" value={form.sender_name_contains} onChange={(e) => setForm({ ...form, sender_name_contains: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="input-label">Regex do assunto (opcional)</label>
            <input className="input" placeholder="ExpoQueijo.*" value={form.subject_regex} onChange={(e) => setForm({ ...form, subject_regex: e.target.value })} />
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Expressão regular aplicada no campo Assunto do email
            </p>
            {form.subject_regex && (
              <div style={{ marginTop: 10 }}>
                <label className="input-label">Testar regex</label>
                <input
                  className="input"
                  placeholder="Cole um assunto de email para testar..."
                  value={regexTest}
                  onChange={(e) => setRegexTest(e.target.value)}
                  style={{ fontSize: 13 }}
                />
                {regexTest && (() => {
                  try {
                    const match = new RegExp(form.subject_regex, "i").test(regexTest);
                    return (
                      <div style={{
                        marginTop: 6,
                        padding: "6px 10px",
                        borderRadius: "var(--radius-sm)",
                        fontSize: 12,
                        fontWeight: 500,
                        background: match ? "rgba(34, 197, 94, 0.1)" : "rgba(239, 68, 68, 0.1)",
                        color: match ? "var(--success-500)" : "var(--error-500)",
                        border: `1px solid ${match ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)"}`,
                      }}>
                        {match ? "✅ Match! Este assunto será capturado." : "❌ Sem match. O assunto não será capturado."}
                      </div>
                    );
                  } catch {
                    return (
                      <div style={{ marginTop: 6, padding: "6px 10px", borderRadius: "var(--radius-sm)", fontSize: 12, background: "rgba(239, 68, 68, 0.1)", color: "var(--error-500)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                        ⚠️ Regex inválida
                      </div>
                    );
                  }
                })()}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="input-label">Delay (minutos)</label>
            <input className="input" type="number" min={0} value={form.delay_minutes} onChange={(e) => setForm({ ...form, delay_minutes: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label className="input-label">Status do post</label>
            <select className="input" value={form.post_status} onChange={(e) => setForm({ ...form, post_status: e.target.value })}>
              <option value="publish">Publicado</option>
              <option value="draft">Rascunho</option>
              <option value="pending">Pendente</option>
            </select>
          </div>
        </div>

        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={handleSubmit}>{editing ? "Salvar" : "Criar Regra"}</button>
        </div>
      </Modal>
    </div>
  );
}
