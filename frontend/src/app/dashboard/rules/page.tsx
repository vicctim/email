"use client";

import { useEffect, useState } from "react";
import { Plus, GitBranch, Trash2, Pencil, Play, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
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
  category_ids: number[];
  author_username: string | null;
  email_account_id: number;
  wordpress_site_id: number;
  email_account?: { name: string };
  wordpress_site?: { name: string };
  approval_required: boolean;
}

interface SelectOption { id: number; name: string }
interface CategoryOption { id: number; name: string; slug: string; count: number }
interface AuthorOption { id: number; name: string; username: string }

interface RuleForm extends Record<string, unknown> {
  name: string;
  email_account_id: number;
  wordpress_site_id: number;
  sender_contains: string;
  sender_name_contains: string;
  subject_regex: string;
  delay_minutes: number;
  post_status: string;
  category_ids: number[];
  author_username: string;
  remove_signature: boolean;
  remove_footer: boolean;
  convert_bold_to_h3: boolean;
  extract_gallery: boolean;
  approval_required: boolean;
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [sites, setSites] = useState<SelectOption[]>([]);
  const [accounts, setAccounts] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Rule | null>(null);
  const [regexTest, setRegexTest] = useState("");
  const [running, setRunning] = useState<number | null>(null);
  const [runResult, setRunResult] = useState<{ ruleId: number; ok: boolean; message: string } | null>(null);
  const [categoriesBySite, setCategoriesBySite] = useState<Record<number, CategoryOption[]>>({});
  const [authorsBySite, setAuthorsBySite] = useState<Record<number, AuthorOption[]>>({});
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [loadingAuthors, setLoadingAuthors] = useState(false);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [authorError, setAuthorError] = useState<string | null>(null);

  const [form, setForm] = useState<RuleForm>({
    name: "",
    email_account_id: 0,
    wordpress_site_id: 0,
    sender_contains: "",
    sender_name_contains: "",
    subject_regex: "",
    delay_minutes: 10,
    post_status: "publish",
    category_ids: [],
    author_username: "",
    remove_signature: true,
    remove_footer: true,
    convert_bold_to_h3: true,
    extract_gallery: true,
    approval_required: false,
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
    const siteId = sites[0]?.id || 0;
    setCategoryError(null);
    setAuthorError(null);
    setForm({
      name: "", email_account_id: accounts[0]?.id || 0, wordpress_site_id: siteId,
      sender_contains: "", sender_name_contains: "", subject_regex: "",
      delay_minutes: 10, post_status: "publish", category_ids: [], author_username: "",
      remove_signature: true, remove_footer: true, convert_bold_to_h3: true, extract_gallery: true,
      approval_required: false,
    });
    if (siteId) void loadSiteOptions(siteId);
    setModalOpen(true);
  }

  function openEdit(rule: Rule) {
    setEditing(rule);
    setCategoryError(null);
    setAuthorError(null);
    setForm({
      name: rule.name,
      email_account_id: rule.email_account_id,
      wordpress_site_id: rule.wordpress_site_id,
      sender_contains: rule.sender_contains || "",
      sender_name_contains: rule.sender_name_contains || "",
      subject_regex: rule.subject_regex || "",
      delay_minutes: rule.delay_minutes,
      post_status: rule.post_status,
      category_ids: Array.isArray(rule.category_ids) ? rule.category_ids : [],
      author_username: rule.author_username || "",
      remove_signature: true, remove_footer: true, convert_bold_to_h3: true, extract_gallery: true,
      approval_required: ("approval_required" in rule) ? (rule as Rule).approval_required : false,
    });
    if (rule.wordpress_site_id) void loadSiteOptions(rule.wordpress_site_id);
    setModalOpen(true);
  }

  async function loadSiteOptions(siteId: number) {
    await Promise.all([loadCategories(siteId), loadAuthors(siteId)]);
  }

  async function loadCategories(siteId: number) {
    if (!siteId || categoriesBySite[siteId]) return;
    setLoadingCategories(true);
    setCategoryError(null);
    try {
      const data = await sitesApi.categories(siteId);
      setCategoriesBySite((prev) => ({ ...prev, [siteId]: Array.isArray(data) ? data : [] }));
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Não foi possível carregar categorias";
      setCategoryError(msg);
      setCategoriesBySite((prev) => ({ ...prev, [siteId]: [] }));
    } finally {
      setLoadingCategories(false);
    }
  }

  async function loadAuthors(siteId: number) {
    if (!siteId || authorsBySite[siteId]) return;
    setLoadingAuthors(true);
    setAuthorError(null);
    try {
      const data = await sitesApi.authors(siteId);
      setAuthorsBySite((prev) => ({ ...prev, [siteId]: Array.isArray(data) ? data : [] }));
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Não foi possível carregar autores";
      setAuthorError(msg);
      setAuthorsBySite((prev) => ({ ...prev, [siteId]: [] }));
    } finally {
      setLoadingAuthors(false);
    }
  }

  function handleSiteChange(siteId: number) {
    setForm({ ...form, wordpress_site_id: siteId, category_ids: [], author_username: "" });
    setCategoryError(null);
    setAuthorError(null);
    if (siteId) void loadSiteOptions(siteId);
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

  async function handleRun(id: number) {
    setRunning(id);
    setRunResult(null);
    try {
      const result = await rulesApi.run(id);
      setRunResult({ ruleId: id, ok: true, message: result.message || `${result.processed} email(s) enfileirado(s)` });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao executar regra";
      setRunResult({ ruleId: id, ok: false, message: msg });
    } finally {
      setRunning(null);
      setTimeout(() => setRunResult(null), 5000);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Remover esta regra?")) return;
    await rulesApi.delete(id);
    loadData();
  }

  const selectedCategories = form.wordpress_site_id ? categoriesBySite[form.wordpress_site_id] || [] : [];
  const selectedAuthors = form.wordpress_site_id ? authorsBySite[form.wordpress_site_id] || [] : [];
  const selectedCategoryId = form.category_ids[0] || "";

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
                <th>Aprovação</th>
                <th style={{ width: 130 }}>Ações</th>
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
                    {rule.approval_required ? (
                      <span className="badge badge-warning">Manual</span>
                    ) : (
                      <span className="badge badge-neutral" style={{ opacity: 0.6 }}>Automática</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button
                        className="btn btn-ghost btn-sm btn-icon"
                        onClick={() => handleRun(rule.id)}
                        disabled={running === rule.id}
                        title="Executar regra agora"
                        style={{ color: "var(--brand-400)" }}
                      >
                        {running === rule.id
                          ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                          : <Play size={14} />}
                      </button>
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

      {/* Toast de resultado da execução */}
      {runResult && (
        <div style={{
          position: "fixed",
          bottom: 28,
          right: 28,
          zIndex: 2000,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 20px",
          borderRadius: "var(--radius-lg)",
          background: runResult.ok ? "rgba(34, 197, 94, 0.12)" : "rgba(239, 68, 68, 0.12)",
          border: `1px solid ${runResult.ok ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
          color: runResult.ok ? "var(--success-500)" : "var(--error-500)",
          fontSize: 13,
          fontWeight: 500,
          boxShadow: "var(--shadow-lg)",
          backdropFilter: "blur(8px)",
          animation: "fadeIn 0.2s ease",
          maxWidth: 380,
        }}>
          {runResult.ok
            ? <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
            : <AlertCircle size={16} style={{ flexShrink: 0 }} />}
          {runResult.message}
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
            <select className="input" value={form.wordpress_site_id} onChange={(e) => handleSiteChange(Number(e.target.value))}>
              <option value={0}>Selecione...</option>
              {sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div className="form-group">
            <label className="input-label">Categoria do post</label>
            <select
              className="input"
              value={selectedCategoryId}
              disabled={!form.wordpress_site_id || loadingCategories || !!categoryError}
              onChange={(e) => {
                const value = Number(e.target.value);
                setForm({ ...form, category_ids: value ? [value] : [] });
              }}
            >
              <option value="">
                {loadingCategories ? "Carregando categorias..." : "Sem categoria específica"}
              </option>
              {selectedCategories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            {categoryError ? (
              <p style={{ fontSize: 11, color: "var(--error-500)", marginTop: 4 }}>{categoryError}</p>
            ) : (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                A lista vem do WordPress selecionado
              </p>
            )}
          </div>

          <div className="form-group">
            <label className="input-label">Autor do post</label>
            <select
              className="input"
              value={form.author_username}
              disabled={!form.wordpress_site_id || loadingAuthors || !!authorError}
              onChange={(e) => setForm({ ...form, author_username: e.target.value })}
            >
              <option value="">
                {loadingAuthors ? "Carregando autores..." : "Autor padrão do WordPress"}
              </option>
              {selectedAuthors.map((author) => (
                <option key={author.id} value={author.username}>
                  {author.name} (@{author.username})
                </option>
              ))}
            </select>
            {authorError ? (
              <p style={{ fontSize: 11, color: "var(--error-500)", marginTop: 4 }}>{authorError}</p>
            ) : (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                Define o autor das publicações automáticas
              </p>
            )}
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

        <div className="form-group" style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, padding: "12px 16px", background: "var(--bg-tertiary)", borderRadius: "var(--radius-md)" }}>
          <input
            type="checkbox"
            id="approval_required"
            checked={form.approval_required}
            onChange={(e) => setForm({ ...form, approval_required: e.target.checked })}
            style={{ width: 18, height: 18, accentColor: "var(--brand-500)" }}
          />
          <label htmlFor="approval_required" style={{ fontSize: 14, fontWeight: 500, cursor: "pointer", margin: 0 }}>
            Exige aprovação manual
          </label>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            — Post vai como rascunho e precisa ser aprovado pelo cliente via WhatsApp
          </span>
        </div>

        <div className="form-actions">
          <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={handleSubmit}>{editing ? "Salvar" : "Criar Regra"}</button>
        </div>
      </Modal>
    </div>
  );
}
