"use client";

import { useEffect, useState } from "react";
import { Send, Clock, AlertTriangle, CheckCircle2, Globe, ArrowUpRight } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import PageHeader from "@/components/layout/PageHeader";
import StatCard from "@/components/ui/StatCard";
import { dashboardApi } from "@/lib/api";

interface DashboardStats {
  published_today: number;
  pending: number;
  failed: number;
  total_published: number;
  active_sites: number;
  active_rules: number;
}

interface RecentPost {
  id: number;
  title: string;
  site_name: string;
  site_url: string;
  post_url: string;
  published_at: string;
  status: string;
}

const weekDays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

function generateEmptyWeek(): { day: string; posts: number }[] {
  const data = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    data.push({ day: weekDays[d.getDay()], posts: 0 });
  }
  return data;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<RecentPost[]>([]);
  const [weeklyData, setWeeklyData] = useState<{ day: string; posts: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, r] = await Promise.all([dashboardApi.stats(), dashboardApi.recent()]);
        setStats(s);
        setRecent(r);
        if (s.weekly_chart) {
          setWeeklyData(s.weekly_chart);
        } else {
          setWeeklyData(generateEmptyWeek());
        }
      } catch {
        setStats({
          published_today: 0,
          pending: 0,
          failed: 0,
          total_published: 0,
          active_sites: 0,
          active_rules: 0,
        });
        setRecent([]);
        setWeeklyData(generateEmptyWeek());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div>
        <PageHeader title="Dashboard" description="Visão geral do sistema" />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: "var(--radius-lg)" }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Dashboard" description="Visão geral do sistema de publicação automática" />

      {/* Stats Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: 16,
        marginBottom: 32,
      }}>
        <StatCard
          label="Publicados Hoje"
          value={stats?.published_today ?? 0}
          icon={CheckCircle2}
          color="success"
        />
        <StatCard
          label="Pendentes na Fila"
          value={stats?.pending ?? 0}
          icon={Clock}
          color="warning"
        />
        <StatCard
          label="Falhas"
          value={stats?.failed ?? 0}
          icon={AlertTriangle}
          color="error"
        />
        <StatCard
          label="Total Publicados"
          value={stats?.total_published ?? 0}
          icon={Send}
          color="brand"
        />
      </div>

      {/* Info Cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: 16,
        marginBottom: 32,
      }}>
        <div className="glass-card" style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 12 }}>
          <Globe size={18} color="var(--brand-400)" />
          <div>
            <p style={{ fontSize: 20, fontWeight: 700 }}>{stats?.active_sites ?? 0}</p>
            <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Sites Ativos</p>
          </div>
        </div>
        <div className="glass-card" style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 12 }}>
          <div className="status-dot online" />
          <div>
            <p style={{ fontSize: 20, fontWeight: 700 }}>{stats?.active_rules ?? 0}</p>
            <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Regras Ativas</p>
          </div>
        </div>
      </div>

      {/* Weekly Chart */}
      <div className="glass-card" style={{ padding: "20px 22px", marginBottom: 32 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--text-secondary)" }}>
          Publicações — Últimos 7 dias
        </h3>
        <div style={{ width: "100%", height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weeklyData} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51, 65, 85, 0.3)" vertical={false} />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border-primary)",
                  borderRadius: "var(--radius-md)",
                  fontSize: 13,
                  color: "var(--text-primary)",
                }}
                cursor={{ fill: "rgba(51, 129, 255, 0.06)" }}
              />
              <Bar dataKey="posts" fill="var(--brand-500)" radius={[4, 4, 0, 0]} name="Posts" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Posts */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 14 }}>Últimas Publicações</h2>
        {recent.length === 0 ? (
          <div className="glass-card empty-state">
            <Send size={36} />
            <p>Nenhuma publicação ainda. Configure sites e regras para começar.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Título</th>
                  <th>Site</th>
                  <th>Status</th>
                  <th>Data</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recent.map((post) => (
                  <tr key={post.id}>
                    <td style={{ maxWidth: 300 }}>
                      <span className="truncate" style={{ display: "block" }}>{post.title}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{post.site_name}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${post.status === "published" ? "success" : post.status === "failed" ? "error" : "warning"}`}>
                        {post.status === "published" ? "Publicado" : post.status === "failed" ? "Erro" : "Pendente"}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
                        {new Date(post.published_at).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </td>
                    <td>
                      {post.post_url && (
                        <a
                          href={post.post_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-ghost btn-sm btn-icon"
                          title="Ver post"
                        >
                          <ArrowUpRight size={14} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
