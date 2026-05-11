import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Email Extractor — Painel Admin",
  description: "Ferramenta de extração automática de conteúdo de email para WordPress",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
