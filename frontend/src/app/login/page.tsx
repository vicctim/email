"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Zap, Eye, EyeOff, Loader2 } from "lucide-react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password);
      router.push("/dashboard");
    } catch {
      setError("Credenciais inválidas. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 20,
      background: `
        radial-gradient(ellipse at 20% 50%, rgba(51, 129, 255, 0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(51, 129, 255, 0.05) 0%, transparent 50%),
        var(--bg-primary)
      `,
    }}>
      <div className="animate-fade-in" style={{ width: "100%", maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{
            width: 56,
            height: 56,
            borderRadius: "var(--radius-lg)",
            background: "linear-gradient(135deg, var(--brand-600), var(--brand-400))",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 16,
            boxShadow: "0 0 30px rgba(51, 129, 255, 0.3)",
          }}>
            <Zap size={26} color="white" />
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>Email Extractor</h1>
          <p style={{ fontSize: 14, color: "var(--text-muted)" }}>
            Acesse o painel de administração
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="glass-card" style={{ padding: 28 }}>
          {error && (
            <div style={{
              padding: "10px 14px",
              marginBottom: 18,
              borderRadius: "var(--radius-md)",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "var(--error-500)",
              fontSize: 13,
            }}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="input-label" htmlFor="login-username">Usuário</label>
            <input
              id="login-username"
              className="input"
              type="text"
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label className="input-label" htmlFor="login-password">Senha</label>
            <div style={{ position: "relative" }}>
              <input
                id="login-password"
                className="input"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                style={{ paddingRight: 44 }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: 8,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-muted)",
                  padding: 6,
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: "100%", marginTop: 8, height: 44 }}
          >
            {loading ? <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} /> : "Entrar"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: 20, fontSize: 12, color: "var(--text-muted)" }}>
          Email Content Extractor v1.0
        </p>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
