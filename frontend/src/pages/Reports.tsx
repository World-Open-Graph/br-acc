import { useState } from "react";
import styles from "./Reports.module.css";

interface Report {
  title: string;
  file: string;
  date: string;
  scenario: string;
  entities: string[];
  sources: string[];
}

const PUBLISHED_REPORTS: Report[] = [
  {
    title: "SUPERAR LTDA - Empresa Sancionada",
    file: "report-01-superar-ltda.md",
    date: "02/03/2026",
    scenario: "Empresa com 7 sanções no grafo, sócio PJ",
    entities: ["SUPERAR LTDA", "ALDIVAR BAGATOLI", "MASTER ELETRODOMESTICO LTDA"],
    sources: ["Neo4j", "BrasilAPI", "Portal da Transparência"],
  },
  {
    title: "Transparência Municipal - Manaus (AM)",
    file: "report-02-manaus-transparencia.md",
    date: "02/03/2026",
    scenario: "Emendas parlamentares + processos judiciais + diários oficiais",
    entities: ["Manaus (AM)", "VINICIUS GURGEL", "CABUCU BORGES"],
    sources: ["Portal da Transparência", "DataJud TJAM", "Querido Diário"],
  },
  {
    title: "Recuperação Judicial - São Paulo",
    file: "report-03-recuperacao-judicial-sp.md",
    date: "02/03/2026",
    scenario: "3.704 processos de recuperação judicial no TJSP",
    entities: ["TJSP", "Varas de Falências"],
    sources: ["DataJud CNJ", "Portal da Transparência"],
  },
];

export function Reports() {
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [reportContent, setReportContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genQuery, setGenQuery] = useState("");
  const [genResult, setGenResult] = useState<string>("");

  const loadReport = async (file: string) => {
    setLoading(true);
    try {
      const resp = await fetch(`/reports/${file}`);
      if (resp.ok) {
        setReportContent(await resp.text());
        setSelectedReport(file);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    if (!genQuery.trim()) return;
    setGenerating(true);
    setGenResult("");
    try {
      const resp = await fetch(`/api/v1/monitor/report/${encodeURIComponent(genQuery)}`);
      if (resp.ok) {
        const data = await resp.json();
        let md = `# Relatório: ${data.municipio}\n\n`;
        md += `> Gerado em: ${data.generated_at}\n\n`;
        for (const [section, content] of Object.entries(data.sections || {})) {
          md += `## ${section}\n\n`;
          md += "```json\n" + JSON.stringify(content, null, 2) + "\n```\n\n";
        }
        if (data.error) md += `\n**Erro:** ${data.error}`;
        setGenResult(md);
      }
    } catch (e) {
      setGenResult("Erro ao gerar relatório");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Relatórios de Investigação</h1>
      <p className={styles.subtitle}>
        Relatórios gerados com dados reais do grafo Neo4j, Portal da Transparência, DataJud e outras fontes públicas.
      </p>

      <div className={styles.generateSection}>
        <h2 className={styles.sectionTitle}>Gerar Novo Relatório</h2>
        <div className={styles.generateForm}>
          <input
            className={styles.input}
            type="text"
            placeholder="Nome do município (ex: Manaus, São Paulo, Curitiba...)"
            value={genQuery}
            onChange={(e) => setGenQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && generateReport()}
          />
          <button className={styles.button} onClick={generateReport} disabled={generating}>
            {generating ? "Gerando..." : "Gerar Relatório"}
          </button>
        </div>
        {genResult && (
          <div className={styles.generatedReport}>
            <pre className={styles.reportPre}>{genResult}</pre>
          </div>
        )}
      </div>

      <h2 className={styles.sectionTitle}>Relatórios Publicados</h2>
      <div className={styles.reportGrid}>
        {PUBLISHED_REPORTS.map((r) => (
          <div
            key={r.file}
            className={`${styles.reportCard} ${selectedReport === r.file ? styles.reportCardActive : ""}`}
            onClick={() => loadReport(r.file)}
          >
            <div className={styles.reportDate}>{r.date}</div>
            <h3 className={styles.reportTitle}>{r.title}</h3>
            <p className={styles.reportScenario}>{r.scenario}</p>
            <div className={styles.reportTags}>
              {r.sources.map((s) => (
                <span key={s} className={styles.tag}>{s}</span>
              ))}
            </div>
            <div className={styles.reportEntities}>
              {r.entities.slice(0, 3).map((e) => (
                <span key={e} className={styles.entity}>{e}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {loading && <p className={styles.loading}>Carregando relatório...</p>}

      {selectedReport && reportContent && (
        <div className={styles.reportViewer}>
          <div className={styles.viewerHeader}>
            <h2>{PUBLISHED_REPORTS.find((r) => r.file === selectedReport)?.title}</h2>
            <button className={styles.closeBtn} onClick={() => setSelectedReport(null)}>Fechar</button>
          </div>
          <pre className={styles.reportPre}>{reportContent}</pre>
        </div>
      )}

      <div className={styles.howItWorks}>
        <h2 className={styles.sectionTitle}>Como Funciona</h2>
        <div className={styles.stepsGrid}>
          <div className={styles.step}>
            <div className={styles.stepNumber}>1</div>
            <h3>Busca no Grafo</h3>
            <p>317.583 entidades e 34.507 conexões em Neo4j</p>
          </div>
          <div className={styles.step}>
            <div className={styles.stepNumber}>2</div>
            <h3>APIs Públicas</h3>
            <p>Portal Transparência, DataJud, Querido Diário, Brave Search</p>
          </div>
          <div className={styles.step}>
            <div className={styles.stepNumber}>3</div>
            <h3>AI Cross-Reference</h3>
            <p>Gemini 2.0 Flash analisa e cruza todas as fontes</p>
          </div>
          <div className={styles.step}>
            <div className={styles.stepNumber}>4</div>
            <h3>Relatório</h3>
            <p>Documento com dados, análise e passo a passo</p>
          </div>
        </div>
        <div className={styles.costInfo}>
          <strong>Custo desta análise:</strong> ~R$ 0,05 (tokens LLM) + R$ 0,00 (APIs gratuitas)
          <br />
          <strong>Comparação:</strong> Palantir Gotham custa ~US$10M/ano para análise equivalente.
        </div>
      </div>
    </div>
  );
}
