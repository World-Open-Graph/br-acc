import { useState } from "react";

interface Report {
  id: string;
  title: string;
  date: string;
  description: string;
  tags: string[];
  url: string;
  highlight?: string;
}

const REPORTS: Report[] = [
  {
    id: "patense",
    title: "Grupo Patense - Rede Societária e Financeira",
    date: "2026-03-01",
    description: "Pesquisa de 13 empresas interligadas com R$217M em financiamentos BNDES e R$2.15B em divida ativa.",
    tags: ["BNDES", "rede societaria", "divida ativa"],
    url: "/reports/patense.html",
    highlight: "R$2.15B em divida ativa",
  },
  {
    id: "superar",
    title: "SUPERAR LTDA — Empresa Sancionada",
    date: "2026-03-02",
    description: "Empresa com 7 sancoes no grafo, socio PJ — pesquisa de cadeia societaria e beneficiarios finais.",
    tags: ["sancoes", "CEIS", "cadeia societaria"],
    url: "/reports/report-01-superar-ltda.html",
    highlight: "7 sancoes",
  },
  {
    id: "manaus",
    title: "Transparencia Municipal — Manaus (AM)",
    date: "2026-03-02",
    description: "Emendas parlamentares, 4.664 processos judiciais e diarios oficiais de Manaus. Foco ambiental.",
    tags: ["emendas", "DataJud", "meio ambiente"],
    url: "/reports/report-02-manaus-transparencia.html",
    highlight: "4.664 processos",
  },
  {
    id: "rj-sp",
    title: "Recuperacao Judicial — Sao Paulo",
    date: "2026-03-02",
    description: "3.704 processos de recuperacao judicial no TJSP. Cruzamentos com contratos publicos e sancoes.",
    tags: ["recuperacao judicial", "TJSP", "DataJud"],
    url: "/reports/report-03-recuperacao-judicial-sp.html",
    highlight: "3.704 processos",
  },
];

const TAG_BG: Record<string, string> = {
  BNDES: "#f59e0b",
  "rede societaria": "#3b82f6",
  "divida ativa": "#ef4444",
};

export function ReportsShowcase() {
  const [hover, setHover] = useState<string | null>(null);

  if (REPORTS.length === 0) return null;

  return (
    <section style={{ padding: "2rem 1.5rem", maxWidth: 1000, margin: "0 auto" }}>
      <span style={{ display: "block", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "#94a3b8", marginBottom: "0.5rem" }}>
        Pesquisas Reais
      </span>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9", marginBottom: "0.25rem" }}>
        Relatorios Publicados
      </h2>
      <p style={{ fontSize: "0.8125rem", color: "#64748b", marginBottom: "1.5rem" }}>
        Gerados automaticamente a partir dos dados do grafo Neo4j. 100% dados publicos, verificaveis.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {REPORTS.map((r) => (
          <a
            key={r.id}
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              textDecoration: "none",
              display: "block",
              background: hover === r.id ? "rgba(30,58,95,0.5)" : "rgba(30,41,59,0.6)",
              border: hover === r.id ? "1px solid rgba(59,130,246,0.4)" : "1px solid rgba(71,85,105,0.3)",
              borderRadius: 10,
              padding: "1.25rem",
              transition: "all 0.2s",
            }}
            onMouseEnter={() => setHover(r.id)}
            onMouseLeave={() => setHover(null)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.625rem", color: "#64748b" }}>{r.date}</span>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, color: "#e2e8f0", margin: "0.125rem 0 0.375rem" }}>{r.title}</h3>
                <p style={{ fontSize: "0.8125rem", color: "#94a3b8", margin: 0, lineHeight: 1.5 }}>{r.description}</p>
              </div>
              {r.highlight && (
                <div style={{ textAlign: "right", flexShrink: 0, marginLeft: "1rem" }}>
                  <span style={{ fontSize: "1.125rem", fontWeight: 700, color: "#ef4444", display: "block" }}>{r.highlight}</span>
                  <span style={{ fontSize: "0.5625rem", color: "#64748b", textTransform: "uppercase" }}>destaque</span>
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: "0.25rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
              {r.tags.map((tag) => (
                <span key={tag} style={{ fontSize: "0.5625rem", padding: "0.0625rem 0.375rem", borderRadius: 999, background: `${TAG_BG[tag] || "#475569"}20`, color: TAG_BG[tag] || "#94a3b8", border: `1px solid ${TAG_BG[tag] || "#475569"}30` }}>
                  {tag}
                </span>
              ))}
              <span style={{ fontSize: "0.5625rem", padding: "0.0625rem 0.375rem", borderRadius: 999, background: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.2)", marginLeft: "auto" }}>
                Abrir relatorio &rarr;
              </span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
